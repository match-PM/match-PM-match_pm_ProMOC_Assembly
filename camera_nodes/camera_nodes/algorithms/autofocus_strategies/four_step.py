"""Four-step staged autofocus strategy."""

from __future__ import annotations

from enum import Enum, auto

import numpy as np

from ..autofocus import AutofocusConfig, AutofocusResult, MSPRAutofocus, Phase


class _FourStepStage(Enum):
    """Named scan stages for the staged coarse-to-fine sweep."""

    COARSE_SWEEP = auto()
    FINE_SWEEP = auto()
    ULTRA_FINE_SWEEP = auto()


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
        self.stage = _FourStepStage.COARSE_SWEEP
        self.drop_counter = 0
        self.parabolic_peak_mm: float | None = None
        self.parabolic_fit_points: list[tuple[float, float]] = []
        self.current_stage_best_score: float | None = None
        self.ultra_start_index: int | None = None

    def start(self) -> float:
        self._reset_runtime_state()
        self._phase = Phase.COARSE_SCAN

        # Step 1: Create the initial coarse scan across the full range.
        total_range = self.config.end_mm - self.config.start_mm
        n_steps = max(1, int(round(total_range / self.step_coarse)) + 1)
        self.scan_points = list(np.linspace(
            self.config.start_mm,
            self.config.end_mm,
            n_steps
        ))
        self.scan_points = self._clamp_positions(self.scan_points)
        self.scan_index = 0
        self.stage = _FourStepStage.COARSE_SWEEP
        self.current_stage_best_score = None
        self.ultra_start_index = None

        return self.scan_points[0] if self.scan_points else float(self.config.start_mm)

    def process_image(self, position_mm: float, image: np.ndarray) -> AutofocusResult:
        # Step 1: Score the current frame and update the global best measurement.
        score = self._calculate_score(image)
        current_measurement, _ = self._store_measurement(
            position_mm,
            score,
            fallback_to_previous=True
        )
        current_score = current_measurement.score

        # Step 2: Track when the ultra-fine stage starts moving away from the peak.
        if self.stage == _FourStepStage.ULTRA_FINE_SWEEP:
            if self.current_stage_best_score is None or current_score > self.current_stage_best_score:
                self.current_stage_best_score = current_score
                self.drop_counter = 0
            else:
                self.drop_counter += 1

        next_pos = position_mm
        finished = False

        if self.stage == _FourStepStage.COARSE_SWEEP:
            # Step 3a: Sweep the full range to locate the rough focus hill.
            self.scan_index += 1
            if self.scan_index < len(self.scan_points):
                next_pos = self.scan_points[self.scan_index]
            else:
                self.stage = _FourStepStage.FINE_SWEEP
                self._phase = Phase.REFINEMENT
                self._setup_next_scan(self.step_fine, self.range_fine)
                self.current_stage_best_score = None
                if self.scan_points:
                    next_pos = self.scan_points[0]
                else:
                    finished = True

        elif self.stage == _FourStepStage.FINE_SWEEP:
            # Step 3b: Rescan a narrower window around the current best point.
            self.scan_index += 1
            if self.scan_index < len(self.scan_points):
                next_pos = self.scan_points[self.scan_index]
            else:
                self.stage = _FourStepStage.ULTRA_FINE_SWEEP
                self._setup_next_scan(self.step_ultra, self.range_ultra)
                self.current_stage_best_score = None
                self.ultra_start_index = len(self._measurements)
                if self.scan_points:
                    next_pos = self.scan_points[0]
                else:
                    finished = True

        elif self.stage == _FourStepStage.ULTRA_FINE_SWEEP:
            # Step 3c: Run the ultra-fine pass and stop on repeated score drops.
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

        # Step 1: Center the next scan window around the best point so far.
        center = self._best_measurement.position_mm
        start = center - (window_width / 2)
        end = center + (window_width / 2)

        start = max(self.config.start_mm, start)
        end = min(self.config.end_mm, end)

        # Step 2: Rebuild the stage-specific forward scan grid.
        total_range = end - start
        n_steps = max(1, int(round(total_range / step_size)) + 1)
        self.scan_points = list(np.linspace(start, end, n_steps))
        self.scan_points = self._clamp_positions(self.scan_points)
        self.scan_index = 0
        self.drop_counter = 0

    def _get_progress(self) -> float:
        if self.stage == _FourStepStage.COARSE_SWEEP:
            return 0.3
        if self.stage == _FourStepStage.FINE_SWEEP:
            return 0.6
        if self.stage == _FourStepStage.ULTRA_FINE_SWEEP:
            return 0.9
        return 1.0

    def _apply_parabolic_refinement(self) -> None:
        """Apply local parabolic refinement to final-stage samples."""
        if not self.scan_points or not self._measurements:
            return

        # Step 1: Keep only the measurements from the ultra-fine stage.
        start_idx = self.ultra_start_index or 0
        final_coords = [
            (m.position_mm, m.score)
            for m in self._measurements[start_idx:]
        ]

        if len(final_coords) < 3:
            return

        # Step 2: Select the local 3-point neighborhood around the best sample.
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

        # Step 3: Keep the fitted peak as a candidate only.  The runner will
        # physically measure it and accept or reject it against the measured best
        # point, so the algorithm must not overwrite the verified best sample.
        return
