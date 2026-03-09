"""Fibonacci-search autofocus refinement strategy."""

from __future__ import annotations

from ..autofocus import AutofocusConfig, AutofocusResult, MSPRAutofocus, Phase


class FibonacciAutofocus(MSPRAutofocus):
    """
    Fibonacci Search Autofocus.
    
    Similar to Golden Section but uses Fibonacci numbers for interval reduction.
    Slightly more efficient than Golden Section for discrete search problems.
    
    Properties:
    - O(log(n)) measurements where n = range/min_step
    - Requires unimodal focus curve (single peak)
    - Robust against noise
    
    Algorithm:
    1. Coarse scan to find approximate peak region
    2. Use Fibonacci sequence to determine probe points
    3. Iteratively shrink interval until min_step reached
    """
    
    def __init__(self, config: AutofocusConfig):
        """Initialize Fibonacci autofocus."""
        super().__init__(config)
        self._fib_cache: list[int] = []
        self._fib_index = 0
        self._a = 0.0  # Left bound
        self._b = 0.0  # Right bound
        self._c = 0.0  # Inner left probe
        self._d = 0.0  # Inner right probe
        self._fc: float | None = None  # Score at c
        self._fd: float | None = None  # Score at d
        self._state = "INIT"  # INIT, PROBE_C, PROBE_D, SHRINK_LEFT, SHRINK_RIGHT

    def start(self) -> float:
        # Reset strategy-local state for re-entrant runs.
        self._fib_cache = []
        self._fib_index = 0
        self._a = 0.0
        self._b = 0.0
        self._c = 0.0
        self._d = 0.0
        self._fc = None
        self._fd = None
        self._state = "INIT"
        return super().start()

    def _generate_fibonacci(self, max_val: int) -> list[int]:
        """Generate Fibonacci sequence up to max_val."""
        fib = [1, 1]
        while fib[-1] < max_val:
            fib.append(fib[-1] + fib[-2])
        return fib
    
    def _prepare_refinement(self):
        """Prepare Fibonacci search refinement."""
        if not self._best_measurement:
            return
        
        center = self._best_measurement.position_mm
        
        # First refinement: set up initial bracket
        if self._refinement_level == 0:
            # Initial bracket: +/- 2 * step_mm around peak.
            bracket_half = self.config.step_mm * 2.0
            self._a = max(self.config.start_mm, center - bracket_half)
            self._b = min(self.config.end_mm, center + bracket_half)
            
            # Calculate how many steps fit
            n_steps = int((self._b - self._a) / self.config.min_step_mm)
            n_steps = max(5, n_steps)  # Minimum 5 steps
            
            # Generate Fibonacci sequence
            self._fib_cache = self._generate_fibonacci(n_steps)
            self._fib_index = len(self._fib_cache) - 1
            
            # Initial probe points using Fibonacci ratios
            self._c = self._a + (self._b - self._a) * self._fib_cache[-3] / self._fib_cache[-1]
            self._d = self._a + (self._b - self._a) * self._fib_cache[-2] / self._fib_cache[-1]
            
            self._fc = None
            self._fd = None
            self._state = "PROBE_C"
            
            # Start by measuring c
            self._refinement_positions = [self._c]
        
        else:
            # Continue Fibonacci contraction
            self._fib_index -= 1
            
            if self._fib_index < 2:
                # Fibonacci exhausted - use simple midpoint
                mid = (self._a + self._b) / 2
                self._refinement_positions = [mid]
            else:
                ratio = self._fib_cache[self._fib_index - 1] / self._fib_cache[self._fib_index]
                
                if self._state == "SHRINK_LEFT":
                    # Shrink from left (a moves right, c becomes new d)
                    self._a = self._c
                    self._fd = self._fc
                    self._c = self._a + (self._b - self._a) * ratio
                    self._refinement_positions = [self._c]
                    self._state = "PROBE_C"
                else:
                    # Shrink from right (b moves left, d becomes new c)
                    self._b = self._d
                    self._fc = self._fd
                    self._d = self._a + (self._b - self._a) * (1 - ratio)
                    self._refinement_positions = [self._d]
                    self._state = "PROBE_D"
        
        # Update step size
        self._current_step_mm = self._b - self._a
        self._current_range_mm = (self._b - self._a) / 2
        
        self._refinement_index = 0
        self._refinement_level += 1
    
    def _handle_refinement(self) -> AutofocusResult:
        """Handle Fibonacci refinement phase."""
        current_score = self._measurements[-1].score
        
        # Store score based on which probe we measured
        if self._state == "PROBE_C":
            self._fc = current_score
        elif self._state == "PROBE_D":
            self._fd = current_score
        
        # Need to measure the other probe point?
        if self._fc is None:
            self._refinement_positions = [self._c]
            self._refinement_index = 0
            self._state = "PROBE_C"
            return AutofocusResult(
                finished=False,
                next_position_mm=self._c,
                best_position_mm=self._best_measurement.position_mm,
                best_score=self._best_measurement.score,
                current_score=current_score,
                phase=Phase.REFINEMENT,
                progress=0.5 + 0.1 * self._refinement_level,
                current_level=self._refinement_level,
                current_step_mm=self._current_step_mm,
                current_range_mm=self._current_range_mm
            )
        
        if self._fd is None:
            self._refinement_positions = [self._d]
            self._refinement_index = 0
            self._state = "PROBE_D"
            return AutofocusResult(
                finished=False,
                next_position_mm=self._d,
                best_position_mm=self._best_measurement.position_mm,
                best_score=self._best_measurement.score,
                current_score=current_score,
                phase=Phase.REFINEMENT,
                progress=0.5 + 0.1 * self._refinement_level,
                current_level=self._refinement_level,
                current_step_mm=self._current_step_mm,
                current_range_mm=self._current_range_mm
            )
        
        # Both probes measured - decide which side to keep
        if self._fc > self._fd:
            # Peak is in [a, d], shrink from right
            self._state = "SHRINK_RIGHT"
        else:
            # Peak is in [c, b], shrink from left
            self._state = "SHRINK_LEFT"
        
        # Check termination
        interval_size = self._b - self._a
        if interval_size <= self.config.min_step_mm * 2:
            # Converged - return global best observed measurement.
            self._phase = Phase.FINISHED
            return AutofocusResult(
                finished=True,
                best_position_mm=self._best_measurement.position_mm,
                best_score=self._best_measurement.score,
                current_score=current_score,
                phase=Phase.FINISHED,
                progress=1.0,
                current_level=self._refinement_level,
                current_step_mm=interval_size,
                current_range_mm=interval_size / 2
            )
        
        # Continue to next refinement level
        self._prepare_refinement()
        
        return AutofocusResult(
            finished=False,
            next_position_mm=self._refinement_positions[0],
            best_position_mm=self._best_measurement.position_mm,
            best_score=self._best_measurement.score,
            current_score=current_score,
            phase=Phase.REFINEMENT,
            progress=0.5 + 0.1 * self._refinement_level,
            current_level=self._refinement_level,
            current_step_mm=self._current_step_mm,
            current_range_mm=self._current_range_mm
        )
