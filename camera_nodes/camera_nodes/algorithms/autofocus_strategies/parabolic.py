"""Parabolic autofocus strategy variants."""

from __future__ import annotations

import numpy as np

from ..autofocus import AutofocusConfig, AutofocusResult, MSPRAutofocus, Phase


class ParabolicAutofocus(MSPRAutofocus):
    """MSPR variant with local parabola fitting around coarse peak."""

    def __init__(self, config: AutofocusConfig):
        """Initialize parabolic autofocus."""
        super().__init__(config)
        self._interpolated_peak: float | None = None

    def start(self) -> float:
        self._interpolated_peak = None
        return super().start()

    def _fit_local_parabola(self) -> tuple[float, float] | None:
        """
        Fit parabola through best coarse point and its immediate neighbors.
        """
        if len(self._measurements) < 3:
            return None
        
        # Find index of best measurement in coarse scan
        scores = [m.score for m in self._measurements]
        best_idx = np.argmax(scores)
        
        # Safety: Need neighbors on both sides
        if best_idx == 0 or best_idx == len(self._measurements) - 1:
            return None
        
        # Select ONLY the 3 points around the peak (best + neighbors)
        subset = self._measurements[best_idx - 1 : best_idx + 2]
        
        x = np.array([m.position_mm for m in subset])
        y = np.array([m.score for m in subset])
        
        try:
            # Fit parabola: y = ax^2 + bx + c
            coeffs = np.polyfit(x, y, 2)
            a, b, c = coeffs
            
            # Parabola must open downward (a < 0) for maximum
            if a >= 0:
                return None
            
            # Vertex (maximum) at x = -b/(2a)
            peak_x = -b / (2 * a)
            peak_y = a * peak_x**2 + b * peak_x + c
            
            # Sanity check: Peak must be close to best measured point
            # (max 1 step away - otherwise the fit is unreliable)
            current_best_pos = self._measurements[best_idx].position_mm
            if abs(peak_x - current_best_pos) > self.config.step_mm:
                return None
            
            return (float(peak_x), float(peak_y))
        
        except (np.linalg.LinAlgError, ValueError):
            return None
    
    def _handle_coarse_scan(self) -> AutofocusResult:
        """
        Override coarse scan to use local parabolic fitting.
        """
        self._coarse_index += 1
        
        # Continue coarse scan?
        if self._coarse_index < len(self._coarse_positions):
            return AutofocusResult(
                finished=False,
                next_position_mm=self._coarse_positions[self._coarse_index],
                best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
                best_score=self._best_measurement.score if self._best_measurement else 0.0,
                current_score=self._measurements[-1].score,
                phase=Phase.COARSE_SCAN,
                progress=self._coarse_index / len(self._coarse_positions),
                current_level=0,
                current_step_mm=self.config.step_mm,
                current_range_mm=(self.config.end_mm - self.config.start_mm) / 2
            )
        
        # Coarse scan complete -> try local parabolic fit
        if not self._best_measurement:
             return AutofocusResult(finished=True, phase=Phase.FINISHED, best_position_mm=self.config.start_mm, best_score=0.0)
        
        # Attempt local parabolic fit (best + neighbors only)
        local_fit = self._fit_local_parabola()
        
        if local_fit:
            predicted_peak_pos, predicted_peak_score = local_fit
            self._set_best_measurement(predicted_peak_pos, predicted_peak_score)
            self._interpolated_peak = predicted_peak_pos
            self._current_range_mm = self.config.step_mm * 2.0
        
        self._prepare_refinement()
        
        result = AutofocusResult(
            finished=False,
            next_position_mm=self._refinement_positions[0],
            best_position_mm=self._best_measurement.position_mm,
            best_score=self._best_measurement.score,
            current_score=self._measurements[-1].score,
            phase=Phase.COARSE_SCAN,
            progress=0.5,
            current_level=self._refinement_level,
            current_step_mm=self._current_step_mm,
            current_range_mm=self._current_range_mm
        )
        self._phase = Phase.REFINEMENT
        return result


class IterativeParabolicAutofocus(ParabolicAutofocus):
    """Iterative parabola fitting to refine the predicted peak position."""

    def __init__(self, config: AutofocusConfig):
        super().__init__(config)
        self.iteration_count = 0
        self.max_iterations = 2  # Usually 2 iterations are enough.

    def start(self) -> float:
        self.iteration_count = 0
        return super().start()

    def _handle_refinement(self) -> AutofocusResult:
        # Measure the point we just moved to (predicted peak)
        current_measurement = self._measurements[-1]
        
        # Check if this new point is better
        if current_measurement.score > self._best_measurement.score:
            self._best_measurement = current_measurement
        
        self.iteration_count += 1
        
        # Check convergence
        if self.iteration_count >= self.max_iterations or (self._current_range_mm is not None and self._current_range_mm < self.config.min_step_mm):
             return AutofocusResult(finished=True, best_position_mm=self._best_measurement.position_mm, 
                                    best_score=self._best_measurement.score, phase=Phase.FINISHED, progress=1.0)

        # Re-fit with the new sample included.
        local_fit = self._fit_local_parabola()
        
        next_pos = self._best_measurement.position_mm
        
        if local_fit:
            pred_x, _ = local_fit
            next_pos = pred_x
            # Shrink range for safety check.
            self._current_range_mm = abs(pred_x - self._best_measurement.position_mm) * 2
        else:
            # Fit failed, try small step
            next_pos = self._best_measurement.position_mm + self.config.min_step_mm
            
        return AutofocusResult(
            finished=False,
            next_position_mm=next_pos,
            phase=Phase.REFINEMENT,
            progress=0.8 + (0.2 * self.iteration_count/self.max_iterations),
            best_score=self._best_measurement.score,
            best_position_mm=self._best_measurement.position_mm,
            current_score=current_measurement.score
        )
