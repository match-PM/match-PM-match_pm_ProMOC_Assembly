"""Exhaustive (brute-force) autofocus reference strategy."""

from __future__ import annotations

import numpy as np

from ..autofocus import AutofocusConfig, AutofocusResult, MSPRAutofocus, Phase


class ExhaustiveAutofocus(MSPRAutofocus):
    """
    Exhaustive (Brute-Force) Autofocus - Maximum Precision Reference.
    
    Scans EVERY position from start to end with minimum step size.
    No early termination, no shortcuts - guaranteed to find the global maximum.
    
    Use this as a ground truth reference for comparing other algorithms.
    
    WARNING: This is SLOW! Only use for:
    - Benchmarking other algorithms
    - Validating focus positions
    - Small search ranges
    
    Example:
        For a 10mm range with 0.01mm step: 1000 measurements!
        At 0.3s per measurement = ~5 minutes
    """
    
    def __init__(self, config: AutofocusConfig):
        """Initialize exhaustive autofocus with minimum step size."""
        super().__init__(config)
        # Override: use min_step_mm for the entire scan
        self._scan_step = config.min_step_mm
    
    def start(self) -> float:
        """
        Start exhaustive scan with minimum step size.
        
        Returns:
            Initial position to move to
        """
        self._reset_runtime_state()

        # Step 1: Generate the full scan grid at minimum resolution.
        self._coarse_positions = list(np.arange(
            self.config.start_mm,
            self.config.end_mm + self._scan_step / 2,
            self._scan_step
        ))
        
        # Step 2: Clamp positions into the configured travel range.
        self._coarse_positions = [
            max(self.config.start_mm, min(self.config.end_mm, pos))
            for pos in self._coarse_positions
        ]
        
        # Step 3: Remove duplicates caused by floating-point rounding.
        seen = set()
        unique = []
        for pos in self._coarse_positions:
            rounded = round(pos, 6)  # Avoid floating point issues
            if rounded not in seen:
                seen.add(rounded)
                unique.append(pos)
        self._coarse_positions = unique
        
        self._coarse_index = 0
        self._phase = Phase.COARSE_SCAN
        
        return self._coarse_positions[0]
    
    def _handle_coarse_scan(self) -> AutofocusResult:
        """
        Handle exhaustive scan - NO early termination.
        
        Simply measure every single position.
        """
        # Step 1: Advance to the next scan position.
        self._coarse_index += 1
        
        total = len(self._coarse_positions)
        progress = self._coarse_index / total
        
        # Step 2: Keep scanning until the last planned point is measured.
        if self._coarse_index < total:
            return AutofocusResult(
                finished=False,
                next_position_mm=self._coarse_positions[self._coarse_index],
                best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
                best_score=self._best_measurement.score if self._best_measurement else 0.0,
                current_score=self._measurements[-1].score,
                phase=Phase.COARSE_SCAN,
                progress=progress,
                current_level=0,
                current_step_mm=self._scan_step,
                current_range_mm=(self.config.end_mm - self.config.start_mm) / 2
            )
        
        # Step 3: Finish immediately because exhaustive search needs no refinement.
        self._phase = Phase.FINISHED
        return AutofocusResult(
            finished=True,
            best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
            best_score=self._best_measurement.score if self._best_measurement else 0.0,
            current_score=self._measurements[-1].score,
            phase=Phase.FINISHED,
            progress=1.0,
            current_level=0,
            current_step_mm=self._scan_step,
            current_range_mm=0.0
        )
