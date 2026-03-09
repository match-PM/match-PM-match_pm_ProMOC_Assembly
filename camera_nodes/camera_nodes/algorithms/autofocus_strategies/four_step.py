"""Four-step staged autofocus strategy."""

from __future__ import annotations

import numpy as np

from ..autofocus import AutofocusConfig, AutofocusResult, MSPRAutofocus, Phase


class FourStepAutofocus(MSPRAutofocus):
    """
    4-step autofocus for 10um precision without backlash.

    Progression:
    1. Coarse (0.4 mm) -> Scans full range. Finds the "Hill".
    2. Fine   (0.1 mm) -> Scans +/- 0.6 mm. Finds the "Peak".
    3. Ultra  (0.01 mm) -> Scans +/- 0.15 mm. Finds the "Summit".
    4. Parabolic refinement on the final samples.

    Feature: Unidirectional Scan
    Before each stage, the axis moves back to a start position and then
    scans strictly forward. This eliminates mechanical play.
    """

    def __init__(self, config: AutofocusConfig):
        super().__init__(config)

        self.step_coarse = 0.4
        self.step_fine = 0.1
        self.step_ultra = 0.01

        self.range_fine = 1.2
        self.range_ultra = 0.3

        self.scan_points: list[float] = []
        self.scan_index = 0
        self.stage = "COARSE"
        self.drop_counter = 0
        self.parabolic_peak_mm: float | None = None
        self.parabolic_fit_points: list[tuple[float, float]] = []
        self.current_stage_best_score: float | None = None
        self.ultra_start_index: int | None = None

    def start(self) -> float:
        self._reset_runtime_state()
        self._phase = Phase.COARSE_SCAN

        total_range = self.config.end_mm - self.config.start_mm
        n_steps = max(1, int(round(total_range / self.step_coarse)) + 1)
        self.scan_points = list(np.linspace(
            self.config.start_mm,
            self.config.end_mm,
            n_steps
        ))
        self.scan_points = self._clamp_positions(self.scan_points)
        self.scan_index = 0
        self.stage = "COARSE"
        self.current_stage_best_score = None
        self.ultra_start_index = None

        return self.scan_points[0] if self.scan_points else float(self.config.start_mm)

    def process_image(self, position_mm: float, image: np.ndarray) -> AutofocusResult:
        score = self._calculate_score(image)
        current_measurement, _ = self._store_measurement(
            position_mm,
            score,
            fallback_to_previous=True
        )
        current_score = current_measurement.score

        if self.stage == "ULTRA":
            if self.current_stage_best_score is None or current_score > self.current_stage_best_score:
                self.current_stage_best_score = current_score
                self.drop_counter = 0
            else:
                self.drop_counter += 1

        next_pos = position_mm
        finished = False

        if self.stage == "COARSE":
            self.scan_index += 1
            if self.scan_index < len(self.scan_points):
                next_pos = self.scan_points[self.scan_index]
            else:
                self.stage = "FINE"
                self._phase = Phase.REFINEMENT
                self._setup_next_scan(self.step_fine, self.range_fine)
                self.current_stage_best_score = None
                if self.scan_points:
                    next_pos = self.scan_points[0]
                else:
                    finished = True

        elif self.stage == "FINE":
            self.scan_index += 1
            if self.scan_index < len(self.scan_points):
                next_pos = self.scan_points[self.scan_index]
            else:
                self.stage = "ULTRA"
                self._setup_next_scan(self.step_ultra, self.range_ultra)
                self.current_stage_best_score = None
                self.ultra_start_index = len(self._measurements)
                if self.scan_points:
                    next_pos = self.scan_points[0]
                else:
                    finished = True

        elif self.stage == "ULTRA":
            if self.drop_counter >= 5:
                self._apply_parabolic_refinement()
                finished = True
            else:
                self.scan_index += 1
                if self.scan_index < len(self.scan_points):
                    next_pos = self.scan_points[self.scan_index]
                else:
                    self._apply_parabolic_refinement()
                    finished = True

        return AutofocusResult(
            finished=finished,
            next_position_mm=next_pos,
            best_position_mm=self._best_measurement.position_mm if self._best_measurement else 0.0,
            best_score=self._best_measurement.score if self._best_measurement else 0.0,
            phase=Phase.FINISHED if finished else self._phase,
            progress=self._get_progress(),
            current_score=current_score
        )

    def _setup_next_scan(self, step_size: float, window_width: float) -> None:
        if self._best_measurement is None:
            self.scan_points = []
            self.scan_index = 0
            return

        center = self._best_measurement.position_mm
        start = center - (window_width / 2)
        end = center + (window_width / 2)

        start = max(self.config.start_mm, start)
        end = min(self.config.end_mm, end)

        total_range = end - start
        n_steps = max(1, int(round(total_range / step_size)) + 1)
        self.scan_points = list(np.linspace(start, end, n_steps))
        self.scan_points = self._clamp_positions(self.scan_points)
        self.scan_index = 0
        self.drop_counter = 0

    def _get_progress(self) -> float:
        if self.stage == "COARSE":
            return 0.3
        if self.stage == "FINE":
            return 0.6
        if self.stage == "ULTRA":
            return 0.9
        return 1.0

    def _apply_parabolic_refinement(self) -> None:
        """Apply local parabolic refinement to final-stage samples."""
        if not self.scan_points or not self._measurements:
            return

        start_idx = self.ultra_start_index or 0
        final_coords = [
            (m.position_mm, m.score)
            for m in self._measurements[start_idx:]
        ]

        if len(final_coords) < 3:
            return

        # Use local 3-point neighborhood around the best position
        final_coords.sort(key=lambda x: x[0])
        self.parabolic_fit_points = final_coords

        best_idx = int(np.argmax([c[1] for c in final_coords]))
        if best_idx == 0 or best_idx == len(final_coords) - 1:
            return

        local_coords = final_coords[best_idx - 1:best_idx + 2]
        x_vals = [c[0] for c in local_coords]
        scores = [c[1] for c in local_coords]
        subpixel_pos = self._calculate_subpixel_peak(x_vals, scores)
        self.parabolic_peak_mm = subpixel_pos

        if self._best_measurement and abs(subpixel_pos - self._best_measurement.position_mm) > 1e-6:
            self._best_measurement.position_mm = subpixel_pos
