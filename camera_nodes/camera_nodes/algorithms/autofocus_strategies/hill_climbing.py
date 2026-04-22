"""Hill-climbing autofocus strategy."""

from __future__ import annotations

from enum import Enum, auto

import numpy as np

from ..autofocus import AutofocusConfig, AutofocusResult, MSPRAutofocus, Phase


class _HillClimbState(Enum):
    """Internal control flow for the hill-climbing strategy."""

    SEARCHING_FORWARD = auto()
    REFINING_AROUND_PEAK = auto()
    FINAL_CONFIRMATION_SCAN = auto()


class HillClimbingAutofocus(MSPRAutofocus):
    """Adaptive hill-climbing with recursive step-size refinement."""

    def __init__(self, config: AutofocusConfig):
        super().__init__(config)
        
        # Override start parameters
        self.current_pos = config.start_mm
        self.step = config.step_mm * 2.0  # Start with a larger stride.
        self._initial_step = self.step
        self.direction = 1  # 1 = forward, -1 = backward
        self.min_step = config.min_step_mm

        # Drop detection settings
        self.drop_threshold = 0.80
        self.refine_drop_threshold = 0.80
        self._refine_start_pos = 0.0

        # Early stop when no improvement at min step
        self._no_improve_count = 0
        self._max_no_improve = 8
        self._max_measurements = 45

        # Blind zone: force forward motion to avoid early aborts
        total_range = config.end_mm - config.start_mm
        self.blind_zone_end = config.start_mm + (total_range * 0.3)
        
        # State
        self.phase_state = _HillClimbState.SEARCHING_FORWARD
        self.final_scan_points: list[float] = []
        self.final_scan_index: int = 0

    def _dynamic_threshold(self, base: float) -> float:
        """Increase threshold as step size gets finer to stop earlier."""
        if self._initial_step <= 0:
            return base
        ratio = 1.0 - min(1.0, max(0.0, self.step / self._initial_step))
        # Increase up to +0.15 as we get finer
        return min(0.98, base + (0.15 * ratio))

    def start(self) -> float:
        self._reset_runtime_state()
        self.current_pos = self.config.start_mm
        self.step = self.config.step_mm * 2.0
        self._initial_step = self.step
        self.direction = 1
        self._refine_start_pos = 0.0
        self._no_improve_count = 0
        self.phase_state = _HillClimbState.SEARCHING_FORWARD
        self.final_scan_points = []
        self.final_scan_index = 0
        self._phase = Phase.COARSE_SCAN  # Reuse enum for compatibility.
        return self.current_pos

    def process_image(self, position_mm: float, image: np.ndarray) -> AutofocusResult:
        # Step 1: Score the current image and update the best-known point.
        score = self._calculate_score(image)
        current_measurement, improved = self._store_measurement(
            position_mm,
            score,
            fallback_to_previous=True
        )
        current_score = current_measurement.score

        if len(self._measurements) >= self._max_measurements:
            return AutofocusResult(
                finished=True,
                next_position_mm=position_mm,
                best_position_mm=self._best_measurement.position_mm if self._best_measurement else 0.0,
                best_score=self._best_measurement.score if self._best_measurement else 0.0,
                phase=Phase.FINISHED,
                progress=1.0,
                current_score=current_score
            )

        # Step 2: Track how long we have gone without improving the best score.
        if improved:
            self._no_improve_count = 0
        else:
            self._no_improve_count += 1

        # Step 3: Choose the next move from the current state-machine phase.
        next_pos = position_mm
        finished = False

        if self.phase_state == _HillClimbState.SEARCHING_FORWARD:
            # Step 3a: Move forward until the score drops enough to justify refinement.
            dyn_drop = self._dynamic_threshold(self.drop_threshold)
            if position_mm < self.blind_zone_end:
                next_pos = position_mm + (self.step * self.direction)
            else:
                if self._best_measurement is not None and current_score < (self._best_measurement.score * dyn_drop):
                    self._start_refinement_cycle()
                    next_pos = self._calculate_refine_start()
                else:
                    # Keep going with forward momentum.
                    next_pos = position_mm + (self.step * self.direction)
        
        elif self.phase_state == _HillClimbState.REFINING_AROUND_PEAK:
            # Step 3b: Shrink the step size around the best point found so far.
            dyn_refine_drop = self._dynamic_threshold(self.refine_drop_threshold)
            if self.step <= self.min_step and self._no_improve_count >= self._max_no_improve:
                finished = True
                return AutofocusResult(
                    finished=True,
                    next_position_mm=position_mm,
                    best_position_mm=self._best_measurement.position_mm if self._best_measurement else 0.0,
                    best_score=self._best_measurement.score if self._best_measurement else 0.0,
                    phase=Phase.FINISHED,
                    progress=1.0,
                    current_score=current_score
                )
            if self._best_measurement is not None and current_score < (self._best_measurement.score * dyn_refine_drop):
                if self.step <= self.min_step:
                    if self._setup_final_scan():
                        self.phase_state = _HillClimbState.FINAL_CONFIRMATION_SCAN
                        next_pos = self.final_scan_points[0]
                    else:
                        finished = True
                else:
                    self.step = max(self.step * 0.5, self.min_step)
                    next_pos = self._best_measurement.position_mm - (self.step * 3)
            else:
                # Continue in the same direction.
                next_pos = position_mm + self.step
                if self._best_measurement is not None:
                    dist = abs(next_pos - self._best_measurement.position_mm)
                    if dist > (self.step * 10):
                        if self.step <= self.min_step:
                            if self._setup_final_scan():
                                self.phase_state = _HillClimbState.FINAL_CONFIRMATION_SCAN
                                next_pos = self.final_scan_points[0]
                            else:
                                finished = True
                        else:
                            self._start_refinement_cycle()
                            next_pos = self._calculate_refine_start()

        elif self.phase_state == _HillClimbState.FINAL_CONFIRMATION_SCAN:
            # Step 3c: Finish with a dense confirmation scan around the peak.
            if self._no_improve_count >= self._max_no_improve:
                finished = True
            else:
                self.final_scan_index += 1
                if self.final_scan_index < len(self.final_scan_points):
                    next_pos = self.final_scan_points[self.final_scan_index]
                else:
                    finished = True

        # Step 4: Clamp or restart refinement when the proposed move leaves the range.
        if next_pos > self.config.end_mm or next_pos < self.config.start_mm:
            if self.step <= self.min_step:
                if self._setup_final_scan():
                    self.phase_state = _HillClimbState.FINAL_CONFIRMATION_SCAN
                    next_pos = self.final_scan_points[0]
                else:
                    finished = True
            else:
                self._start_refinement_cycle()
                next_pos = self._calculate_refine_start()

        next_pos = max(self.config.start_mm, min(self.config.end_mm, next_pos))

        return AutofocusResult(
            finished=finished,
            next_position_mm=next_pos,
            best_position_mm=self._best_measurement.position_mm if self._best_measurement else 0.0,
            best_score=self._best_measurement.score if self._best_measurement else 0.0,
            phase=Phase.FINISHED if finished else (
                Phase.COARSE_SCAN
                if self.phase_state == _HillClimbState.SEARCHING_FORWARD
                else Phase.REFINEMENT
            ),
            progress=0.5,
            current_score=current_score
        )

    def _start_refinement_cycle(self) -> None:
        """Prepares the next finer pass."""
        # Step 1: Enter refinement mode and reduce the stride.
        self.phase_state = _HillClimbState.REFINING_AROUND_PEAK
        self.step = max(self.step * 0.6, self.min_step)

    def _calculate_refine_start(self) -> float:
        """Calculates a start position slightly before the peak."""
        if self._best_measurement is None:
            return self.current_pos
        # Step 2: Restart slightly before the current best to rescan through the peak.
        self._refine_start_pos = self._best_measurement.position_mm - (self.step * 4.0)
        return self._refine_start_pos

    def _setup_final_scan(self) -> bool:
        """Prepare a final fine scan around the best position."""
        if self._best_measurement is None:
            return False

        # Step 1: Build a narrow confirmation window around the best point.
        window = max(self.min_step * 10.0, 0.05)
        start = self._best_measurement.position_mm - (window / 2.0)
        end = self._best_measurement.position_mm + (window / 2.0)

        start = max(self.config.start_mm, start)
        end = min(self.config.end_mm, end)

        # Step 2: Sample that window at minimum step size.
        self.final_scan_points = list(np.arange(start, end + (self.min_step / 2.0), self.min_step))
        self.final_scan_points = self._clamp_positions(self.final_scan_points)
        self.final_scan_index = 0
        return bool(self.final_scan_points)
