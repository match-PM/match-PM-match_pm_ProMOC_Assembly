"""
Hybrid Autofocus Algorithm with Hysteresis Compensation.

This module implements a hybrid autofocus algorithm featuring:
1. Coarse Search: A linear scan with large steps.
2. Fine Search: Refinement around the detected maximum.
3. Hysteresis Compensation: Through unidirectional movement.

Focus Metric:
=============
Tenengrad is used consistently for image evaluation, as it is robust for
single images and computation time is not critical in this application.

IMPORTANT - The Hysteresis Problem:
===================================
Linear stages exhibit mechanical hysteresis (due to backlash, friction, etc.).
Moving back and forth results in different physical positions for the same
target command.

    Forward:  0 → 10mm  →  Focus at 5.0mm
    Backward: 10 → 0mm  →  Focus at 4.8mm  ← Hysteresis!

Solution - Unidirectional Movement:
===================================
    ┌─────────────────────────────────────────────────────────────┐
    │  ScanDirection.FORWARD                                       │
    │                                                             │
    │  Start at Z_MIN, move only upwards.                         │
    │  0mm ──────────────────────────────────────────────▶ 10mm   │
    │       Coarse Scan (large steps)                             │
    │       Fine Scan (small steps, same direction)               │
    │                                                             │
    │  For Fine Search: Return to start, then move forward again. │
    │  5mm ◀────────── 0mm ──────────────────────▶ 5mm           │
    │      (fast)           (slow, with measurements)            │
    └─────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────┐
    │  ScanDirection.BACKWARD                                      │
    │                                                             │
    │  Start at Z_MAX, move only downwards.                       │
    │  10mm ◀────────────────────────────────────────────── 0mm   │
    │        Coarse Scan (large steps)                            │
    │        Fine Scan (small steps, same direction)              │
    └─────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────┐
    │  ScanDirection.BIDIRECTIONAL (Hysteresis Measurement)        │
    │                                                             │
    │  Performs both scans and compares the results:              │
    │  1. Forward:  0mm → 10mm  →  Focus_fwd                     │
    │  2. Backward: 10mm → 0mm  →  Focus_bwd                     │
    │  3. Hysteresis = |Fokus_fwd - Fokus_bwd|                    │
    │                                                             │
    │  If hysteresis < tolerance, it can be ignored.              │
    │  Otherwise, it must be compensated for.                     │
    └─────────────────────────────────────────────────────────────┘

Usage:
======
    from promoc_core.algorithms.autofocus import HybridAutofocus, AutofocusConfig
    
    # Unidirectional (recommended):
    config = AutofocusConfig(
        z_min_mm=0.0,
        z_max_mm=10.0,
        scan_direction=ScanDirection.FORWARD
    )
    
    # Measure hysteresis:
    config = AutofocusConfig(
        scan_direction=ScanDirection.BIDIRECTIONAL
    )
    result = autofocus.process_image(...)
    if result.finished:
        print(f"Hysteresis: {result.hysteresis_mm:.3f}mm")

Classes:
    ScanDirection: Scan direction (FORWARD, BACKWARD, BIDIRECTIONAL).
    AutofocusConfig: Configuration parameters.
    AutofocusResult: Result of the image processing step.
    HybridAutofocus: The main algorithm class.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Tuple, Callable
import math
import numpy as np

from .focus_metrics import tenengrad


class ScanDirection(Enum):
    """
    Scan direction for the autofocus process.

    FORWARD: From z_min to z_max (eliminates hysteresis).
    BACKWARD: From z_max to z_min (eliminates hysteresis).
    BIDIRECTIONAL: Both directions (measures hysteresis).
    """
    FORWARD = auto()      # 0 → max
    BACKWARD = auto()     # max → 0
    BIDIRECTIONAL = auto()  # Both directions (for hysteresis measurement)


class FocusPhase(Enum):
    """
    The current phase of the autofocus algorithm.

    Phase sequence (unidirectional):
    ================================
        IDLE → COARSE_SEARCH → FINE_REPOSITION → FINE_SEARCH → FINISHED

    Phase sequence (bidirectional):
    ===============================
        IDLE → COARSE_FORWARD → COARSE_BACKWARD → COMPARE → FINISHED
    """
    IDLE = auto()

    # Unidirectional phases
    COARSE_SEARCH = auto()      # Coarse search in the specified scan direction.
    FINE_REPOSITION = auto()    # Moving back to the start of the fine search range.
    FINE_SEARCH = auto()        # Fine search (same direction as coarse).

    # Bidirectional phases (for hysteresis measurement)
    COARSE_FORWARD = auto()     # Forward scan.
    COARSE_BACKWARD = auto()    # Backward scan.
    COMPARE_RESULTS = auto()    # Compare results.

    FINISHED = auto()


@dataclass
class AutofocusConfig:
    """
    Configuration for the hybrid autofocus algorithm.

    Attributes:
        z_min_mm: Minimum Z position in mm.
        z_max_mm: Maximum Z position in mm.
        coarse_step_mm: Step size for the coarse search.
        fine_step_mm: Step size for the fine search.
        fine_range_mm: Range around the maximum for the fine search (±fine_range).
        metric: Focus metric (fixed to 'tenengrad').
        min_focus_score: Minimum score for a valid focus.
        scan_direction: Scan direction (FORWARD, BACKWARD, BIDIRECTIONAL).
        hysteresis_threshold_mm: Threshold at which hysteresis is considered significant.

    Hysteresis Compensation:
    ========================
    - FORWARD/BACKWARD: No hysteresis (unidirectional motion).
    - BIDIRECTIONAL: Measures hysteresis and returns it in the result.
    """
    z_min_mm: float = 0.0
    z_max_mm: float = 10.0
    coarse_step_mm: float = 0.5
    fine_step_mm: float = 0.05
    fine_range_mm: float = 1.5
    # Optional: Multi-level refinement (iterative range reduction).
    # If enable_multilevel=True, after the initial coarse scan, the range
    # around the current maximum is iteratively narrowed. Approximately
    # refinement_samples are taken per level; the step size is determined
    # based on the level's range until min_step_mm is reached.
    enable_multilevel: bool = True
    refinement_samples: int = 51
    min_step_mm: float = 0.01
    refinement_shrink_factor: float = 0.35

    # Early Stopping: Stop the fine search early if the focus score decreases
    # for a consecutive number of measurements. This saves time when the
    # maximum has been passed.
    early_stopping_enabled: bool = True
    early_stopping_count: int = 3  # Stop after N consecutive decreasing scores
    early_stopping_threshold: float = 0.95  # Stop if score drops below 95% of best

    # Focus Metric: Tenengrad has proven robust for single-image analysis.
    # We keep the parameter for backward compatibility (e.g., in config files)
    # but only allow 'tenengrad'.
    metric: str = 'tenengrad'
    min_focus_score: float = 100.0
    scan_direction: ScanDirection = ScanDirection.FORWARD
    hysteresis_threshold_mm: float = 0.1  # Warn if hysteresis > 0.1mm

    def validate(self) -> None:
        """Validates the configuration parameters."""
        if self.z_min_mm >= self.z_max_mm:
            raise ValueError(
                f"z_min ({self.z_min_mm}) must be less than z_max ({self.z_max_mm})")
        if self.coarse_step_mm <= 0:
            raise ValueError(
                f"coarse_step must be positive, but is {self.coarse_step_mm}")
        if self.fine_step_mm <= 0:
            raise ValueError(
                f"fine_step must be positive, but is {self.fine_step_mm}")
        if self.fine_range_mm <= 0:
            raise ValueError(
                f"fine_range must be positive, but is {self.fine_range_mm}")
        if self.fine_step_mm >= self.coarse_step_mm:
            raise ValueError(
                f"fine_step ({self.fine_step_mm}) should be less than coarse_step ({self.coarse_step_mm})")

        if self.refinement_samples < 5:
            raise ValueError(
                f"refinement_samples must be >= 5, but is {self.refinement_samples}")
        if self.min_step_mm <= 0:
            raise ValueError(
                f"min_step_mm must be positive, but is {self.min_step_mm}")
        if not (0.0 < self.refinement_shrink_factor < 1.0):
            raise ValueError(
                f"refinement_shrink_factor must be between 0 and 1, but is {self.refinement_shrink_factor}")

        if self.metric != 'tenengrad':
            raise ValueError(
                f"Only 'tenengrad' is supported (requested: {self.metric!r})")


@dataclass
class AutofocusResult:
    """
    Result of an image processing step in the autofocus process.

    Attributes:
        finished: True if the autofocus process is complete.
        best_z_mm: The best Z position found (valid if finished=True).
        next_z_mm: The next Z position to move to (valid if finished=False).
        phase: The current phase of the algorithm.
        current_score: The focus score of the current image.
        best_score: The best focus score found so far.
        progress: Estimated progress from 0.0 to 1.0.
        message: A human-readable status message.

        # Hysteresis information (only for BIDIRECTIONAL scan):
        hysteresis_mm: Measured hysteresis in mm (None if not measured).
        forward_focus_mm: Focus position from the forward scan.
        backward_focus_mm: Focus position from the backward scan.
        hysteresis_significant: True if hysteresis exceeds the threshold.

        # Movement hints:
        requires_repositioning: True if the axis needs to be repositioned.
        reposition_z_mm: The target position for repositioning.
    """
    finished: bool = False
    best_z_mm: Optional[float] = None
    next_z_mm: Optional[float] = None
    phase: FocusPhase = FocusPhase.IDLE
    current_score: float = 0.0
    best_score: float = 0.0
    progress: float = 0.0
    message: str = ""

    # Hysteresis measurement (BIDIRECTIONAL)
    hysteresis_mm: Optional[float] = None
    forward_focus_mm: Optional[float] = None
    backward_focus_mm: Optional[float] = None
    hysteresis_significant: bool = False

    # Repositioning (for unidirectional fine search)
    requires_repositioning: bool = False
    reposition_z_mm: Optional[float] = None

    # Multi-Level Refinement (optional): current level parameters
    refinement_step_mm: Optional[float] = None
    refinement_range_mm: Optional[float] = None


@dataclass
class _FocusMeasurement:
    """Internal class for a single focus measurement."""
    z_mm: float
    score: float


class HybridAutofocus:
    """
    Hybrid autofocus with hysteresis compensation.

    The algorithm operates in several phases:

    Unidirectional (FORWARD/BACKWARD):
    ==================================
    1. Coarse Search: Linear scan in the specified direction.
    2. Fine Reposition: Move back to the start of the fine search range.
    3. Fine Search: Fine-grained search in the same direction.

    Bidirectional (Hysteresis Measurement):
    =======================================
    1. Coarse Forward: Scan from min to max.
    2. Coarse Backward: Scan from max to min.
    3. Compare: Compare results and calculate hysteresis.

    Why unidirectional?
    ===================
    Linear stages have mechanical hysteresis. Moving consistently in one
    direction eliminates this effect.

    Flow (FORWARD):
    ===============
        ┌─────────────────────────────────────────────────────────┐
        │  Coarse Search: 0mm → 10mm                              │
        │  ════════════════════════════════▶                      │
        │           ↑ Maximum found at 5mm                        │
        │                                                         │
        │  Fine Reposition: 5mm → 3.5mm (no measurements)        │
        │  ◀══════════════                                        │
        │                                                         │
        │  Fine Search: 3.5mm → 6.5mm                            │
        │  ════════════════════════════════▶                      │
        │           ↑ Precise maximum at 4.95mm                   │
        └─────────────────────────────────────────────────────────┘

    Usage:
        # Unidirectional (recommended):
        config = AutofocusConfig(
            scan_direction=ScanDirection.FORWARD
        )
        af = HybridAutofocus(config)

        # Measure hysteresis:
        config = AutofocusConfig(
            scan_direction=ScanDirection.BIDIRECTIONAL
        )
        af = HybridAutofocus(config)
        config = AutofocusConfig(z_min_mm=0, z_max_mm=10)
        af = HybridAutofocus(config)

        # Start search
        first_z = af.start()
        move_to_z(first_z)

        # Main loop
        while True:
            image = capture_image()
            result = af.process_image(current_z, image)

            if result.finished:
                print(f"Focus found at Z={result.best_z_mm:.3f}mm")
                break

            move_to_z(result.next_z_mm)
    """

    def __init__(self, config: AutofocusConfig):
        """
        Initializes the autofocus algorithm.

        Args:
            config: Autofocus configuration parameters.
        """
        config.validate()
        self.config = config
        self._reset_state()

    def _reset_state(self) -> None:
        """Resets the internal state for a new search."""
        self._phase = FocusPhase.IDLE
        self._measurements: List[_FocusMeasurement] = []

        # Scan direction
        self._scan_forward = (self.config.scan_direction !=
                              ScanDirection.BACKWARD)

        # Coarse Search State
        self._coarse_positions: List[float] = []
        self._coarse_index: int = 0

        # Fine Search State (unidirectional)
        self._fine_positions: List[float] = []
        self._fine_index: int = 0
        self._fine_start_z: float = 0.0  # Start position for Fine Search
        self._fine_end_z: float = 0.0    # End position for Fine Search

        # Multi-Level Refinement State
        self._refine_current_step_mm: float = self.config.fine_step_mm
        self._refine_current_range_mm: float = self.config.fine_range_mm

        # Early Stopping State
        self._consecutive_decreasing: int = 0  # Count of consecutive decreasing scores
        self._fine_best_score: float = 0.0  # Best score in current fine search level

        # Bidirectional: results from both directions
        self._forward_measurements: List[_FocusMeasurement] = []
        self._backward_measurements: List[_FocusMeasurement] = []
        self._forward_best_z: float = 0.0
        self._backward_best_z: float = 0.0

        # Best result tracking
        self._best_z: float = 0.0
        self._best_score: float = 0.0

    def start(self) -> float:
        """
        Starts a new autofocus search.

        Generates positions based on the scan direction:
        - FORWARD:  z_min → z_max
        - BACKWARD: z_max → z_min
        - BIDIRECTIONAL: Starts with Forward scan.

        Returns:
            The first Z position to move to.
        """
        self._reset_state()

        # Generate positions based on direction
        if self.config.scan_direction == ScanDirection.BIDIRECTIONAL:
            # Bidirectional: Start with Forward
            self._coarse_positions = self._generate_positions(forward=True)
            self._phase = FocusPhase.COARSE_FORWARD
        else:
            # Unidirectional
            forward = (self.config.scan_direction == ScanDirection.FORWARD)
            self._coarse_positions = self._generate_positions(forward=forward)
            self._phase = FocusPhase.COARSE_SEARCH

        self._coarse_index = 0
        return self._coarse_positions[0]

    def _generate_positions(self, forward: bool) -> List[float]:
        """
        Generates positions for the scan.

        Args:
            forward: True for min→max, False for max→min.

        Returns:
            A list of Z positions.
        """
        z_range = self.config.z_max_mm - self.config.z_min_mm
        num_steps = int(z_range / self.config.coarse_step_mm) + 1

        positions = [
            self.config.z_min_mm + i * self.config.coarse_step_mm
            for i in range(num_steps)
        ]

        # Don't overshoot the maximum position
        if positions[-1] > self.config.z_max_mm:
            positions[-1] = self.config.z_max_mm

        # For a backward scan, reverse the list
        if not forward:
            positions = positions[::-1]

        return positions

    def process_image(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Processes an image and determines the next action.

        This method is called for each captured image. It calculates the
        focus score and returns the next position to move to.

        Args:
            current_z_mm: Current Z position in mm.
            image: The image captured at the current position.

        Returns:
            AutofocusResult with the next action or the final result.
        """
        if self._phase == FocusPhase.IDLE:
            return AutofocusResult(
                finished=False,
                next_z_mm=self.start(),
                phase=FocusPhase.COARSE_SEARCH,
                message="Starting autofocus"
            )

        # Unidirectional phases
        if self._phase == FocusPhase.COARSE_SEARCH:
            return self._process_coarse_unidirectional(current_z_mm, image)

        if self._phase == FocusPhase.FINE_REPOSITION:
            return self._process_fine_reposition(current_z_mm)

        if self._phase == FocusPhase.FINE_SEARCH:
            return self._process_fine_unidirectional(current_z_mm, image)

        # Bidirectional phases
        if self._phase == FocusPhase.COARSE_FORWARD:
            return self._process_coarse_forward(current_z_mm, image)

        if self._phase == FocusPhase.COARSE_BACKWARD:
            return self._process_coarse_backward(current_z_mm, image)

        if self._phase == FocusPhase.COMPARE_RESULTS:
            return self._compare_bidirectional_results()

        # Already finished
        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message="Autofocus complete"
        )

    def _compute_focus_score(self, image: np.ndarray) -> float:
        """Calculates the focus score for an image (using Tenengrad)."""
        # Tenengrad is robust for single images and yields higher values for sharper images.
        return tenengrad(image)

    # ══════════════════════════════════════════════════════════════════════════
    # UNIDIRECTIONAL SEARCH (FORWARD/BACKWARD)
    # ══════════════════════════════════════════════════════════════════════════

    def _process_coarse_unidirectional(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Processes an image during the unidirectional coarse search.

        Moves in one direction only (no hysteresis).
        """
        # Calculate focus score
        score = self._compute_focus_score(image)

        # Store measurement
        self._measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        # Track the best result
        if score > self._best_score:
            self._best_score = score
            self._best_z = current_z_mm

        # Calculate progress
        progress = (self._coarse_index + 1) / len(self._coarse_positions) * 0.5

        # Move to the next position
        self._coarse_index += 1

        if self._coarse_index < len(self._coarse_positions):
            next_z = self._coarse_positions[self._coarse_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.COARSE_SEARCH,
                current_score=score,
                best_score=self._best_score,
                progress=progress,
                message=f"Coarse search: {self._coarse_index}/{len(self._coarse_positions)}"
            )

        # Coarse search finished → prepare for fine search
        return self._prepare_fine_search_unidirectional()

    def _prepare_fine_search_unidirectional(self) -> AutofocusResult:
        """
        Prepares the unidirectional fine search.

        Calculates the fine search range around the coarse maximum and generates
        positions in the correct scan direction.
        """
        if not self._measurements:
            return AutofocusResult(
                finished=True,
                best_z_mm=self.config.z_min_mm,
                phase=FocusPhase.FINISHED,
                message="No measurements were collected"
            )

        # Calculate fine search range
        best_z = self._best_z
        forward = (self.config.scan_direction == ScanDirection.FORWARD)

        # Multi-Level: The initial fine level is based on config.fine_range_mm / fine_step_mm,
        # then it is iteratively narrowed. Single-level (default) behaves as before.
        self._refine_current_step_mm = self.config.fine_step_mm
        self._refine_current_range_mm = self.config.fine_range_mm

        fine_start, fine_end = self._compute_refinement_window(best_z)
        self._fine_positions = self._generate_refinement_positions(
            fine_start, fine_end, self._refine_current_step_mm, forward=forward)

        # For backward scan, reverse the list
        if not forward:
            self._fine_positions = self._fine_positions[::-1]

        self._fine_index = 0

        # Starting position for the fine search
        reposition_target = self._fine_positions[0]

        # Do we need to reposition first?
        # For FORWARD: if we are past the fine start.
        # For BACKWARD: if we are before the fine start.
        current_z = self._coarse_positions[-1]  # Last coarse position

        if forward:
            need_reposition = current_z > reposition_target
        else:
            need_reposition = current_z < reposition_target

        if need_reposition:
            # Reposition first (without measurement!)
            self._phase = FocusPhase.FINE_REPOSITION
            self._fine_start_z = reposition_target

            return AutofocusResult(
                finished=False,
                next_z_mm=reposition_target,
                phase=FocusPhase.FINE_REPOSITION,
                best_score=self._best_score,
                progress=0.5,
                message=f"Repositioning to {reposition_target:.2f}mm for fine search",
                requires_repositioning=True,
                reposition_z_mm=reposition_target
            )
        else:
            # Start fine search directly
            self._phase = FocusPhase.FINE_SEARCH
            return AutofocusResult(
                finished=False,
                next_z_mm=self._fine_positions[0],
                phase=FocusPhase.FINE_SEARCH,
                best_score=self._best_score,
                progress=0.5,
                message="Starting fine search"
            )

    def _compute_refinement_window(self, best_z: float) -> Tuple[float, float]:
        """Calculates the [start, end] window for the current refinement level around `best_z`.

        The window is clamped to the global limits (`z_min_mm`, `z_max_mm`).
        """
        start = max(self.config.z_min_mm, best_z -
                    self._refine_current_range_mm)
        end = min(self.config.z_max_mm, best_z + self._refine_current_range_mm)
        if end < start:
            end = start
        return start, end

    def _generate_refinement_positions(
        self,
        start: float,
        end: float,
        step_mm: float,
        *,
        forward: bool,
    ) -> List[float]:
        """Generates an inclusive list of positions from start to end with a given step.

        Note:
            The list includes `start` and, if possible, `end`.
        """
        if step_mm <= 0:
            raise ValueError(f"step_mm must be positive, got {step_mm}")

        width = end - start
        if width <= 0:
            return [start]

        num_steps = int(width / step_mm) + 1
        positions = [start + i * step_mm for i in range(num_steps)]
        if positions[-1] > end:
            positions[-1] = end
        if not forward:
            positions = positions[::-1]
        return positions

    def _process_fine_reposition(self, current_z_mm: float) -> AutofocusResult:
        """
        Handles the repositioning step before a fine search.

        IMPORTANT: No measurements are taken here, only movement.
        """
        # Repositioning complete → start fine search
        self._phase = FocusPhase.FINE_SEARCH
        self._fine_index = 0

        # Reset early stopping state for the new fine search level
        self._consecutive_decreasing = 0
        self._fine_best_score = 0.0

        return AutofocusResult(
            finished=False,
            next_z_mm=self._fine_positions[0],
            phase=FocusPhase.FINE_SEARCH,
            best_score=self._best_score,
            progress=0.55,
            message="Repositioning complete, starting fine search"
        )

    def _process_fine_unidirectional(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Processes an image during the unidirectional fine search.

        Moves in one direction only through the fine search range.
        Supports early stopping when focus score decreases consistently.
        """
        # Calculate focus score
        score = self._compute_focus_score(image)

        # Store measurement
        self._measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        # Track best result (global)
        if score > self._best_score:
            self._best_score = score
            self._best_z = current_z_mm

        # Track best in current fine search level for early stopping
        if score > self._fine_best_score:
            self._fine_best_score = score
            self._consecutive_decreasing = 0
        else:
            self._consecutive_decreasing += 1

        # Early stopping check: if score drops significantly below best
        should_early_stop = False
        if self.config.early_stopping_enabled and self._fine_best_score > 0:
            # Check if we've seen enough consecutive decreasing scores
            if self._consecutive_decreasing >= self.config.early_stopping_count:
                # Also verify the score has dropped below threshold
                relative_score = score / self._fine_best_score
                if relative_score < self.config.early_stopping_threshold:
                    should_early_stop = True

        # Progress: 50% (coarse) + 50% (fine)
        progress = 0.5 + (self._fine_index + 1) / \
            len(self._fine_positions) * 0.5

        # Move to next position
        self._fine_index += 1

        # Continue fine search if not at end and not early stopping
        if self._fine_index < len(self._fine_positions) and not should_early_stop:
            next_z = self._fine_positions[self._fine_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.FINE_SEARCH,
                current_score=score,
                best_score=self._best_score,
                refinement_step_mm=self._refine_current_step_mm,
                refinement_range_mm=self._refine_current_range_mm,
                progress=progress,
                message=f"Fine search: {self._fine_index}/{len(self._fine_positions)}"
            )

        # Fine search level complete (or early stopped) → possibly continue with refinement
        # Reset early stopping state for next level
        self._consecutive_decreasing = 0
        self._fine_best_score = 0.0

        if self.config.enable_multilevel and self._refine_current_step_mm > self.config.min_step_mm:
            # Narrow the range and choose a step size appropriate for the new range,
            # such that approximately `refinement_samples` points are scanned.
            self._refine_current_range_mm = max(
                self._refine_current_range_mm * self.config.refinement_shrink_factor,
                self.config.min_step_mm,
            )

            # step ≈ (2*range)/(samples-1)
            target_step = (2.0 * self._refine_current_range_mm) / max(
                1, (self.config.refinement_samples - 1))
            self._refine_current_step_mm = max(
                self.config.min_step_mm, target_step)

            forward = (self.config.scan_direction == ScanDirection.FORWARD)
            fine_start, fine_end = self._compute_refinement_window(
                self._best_z)
            self._fine_positions = self._generate_refinement_positions(
                fine_start, fine_end, self._refine_current_step_mm, forward=forward)
            self._fine_index = 0

            # Reposition to the start of the next level as before.
            self._phase = FocusPhase.FINE_REPOSITION
            return AutofocusResult(
                finished=False,
                next_z_mm=self._fine_positions[0],
                phase=FocusPhase.FINE_REPOSITION,
                best_score=self._best_score,
                refinement_step_mm=self._refine_current_step_mm,
                refinement_range_mm=self._refine_current_range_mm,
                progress=min(0.99, progress),
                message=(
                    f"Refinement level: range=±{self._refine_current_range_mm:.4f}mm "
                    f"step={self._refine_current_step_mm:.4f}mm"
                ),
                requires_repositioning=True,
                reposition_z_mm=self._fine_positions[0],
            )

        # Final fine search complete
        self._phase = FocusPhase.FINISHED
        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            refinement_step_mm=self._refine_current_step_mm,
            refinement_range_mm=self._refine_current_range_mm,
            progress=1.0,
            message=f"Focus found at Z={self._best_z:.4f}mm"
        )

    # ══════════════════════════════════════════════════════════════════════════
    # BIDIRECTIONAL SEARCH (HYSTERESIS MEASUREMENT)
    # ══════════════════════════════════════════════════════════════════════════

    def _process_coarse_forward(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Processes an image during the forward scan (bidirectional).
        """
        score = self._compute_focus_score(image)

        self._forward_measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        # Track the best forward result
        if not self._forward_measurements or score > max(m.score for m in self._forward_measurements[:-1] or [_FocusMeasurement(0, 0)]):
            self._forward_best_z = current_z_mm

        progress = (self._coarse_index + 1) / \
            len(self._coarse_positions) * 0.25

        self._coarse_index += 1

        if self._coarse_index < len(self._coarse_positions):
            next_z = self._coarse_positions[self._coarse_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.COARSE_FORWARD,
                current_score=score,
                progress=progress,
                message=f"Forward scan: {self._coarse_index}/{len(self._coarse_positions)}"
            )

        # Forward scan finished → start backward scan
        # Find the best forward result
        if self._forward_measurements:
            best_fwd = max(self._forward_measurements, key=lambda m: m.score)
            self._forward_best_z = best_fwd.z_mm

        # Generate positions for the backward scan
        self._coarse_positions = self._generate_positions(forward=False)
        self._coarse_index = 0
        self._phase = FocusPhase.COARSE_BACKWARD

        return AutofocusResult(
            finished=False,
            next_z_mm=self._coarse_positions[0],
            phase=FocusPhase.COARSE_BACKWARD,
            progress=0.25,
            message="Forward scan complete, starting backward scan",
            forward_focus_mm=self._forward_best_z
        )

    def _process_coarse_backward(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Processes an image during the backward scan (bidirectional).
        """
        score = self._compute_focus_score(image)

        self._backward_measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        progress = 0.25 + (self._coarse_index + 1) / \
            len(self._coarse_positions) * 0.25

        self._coarse_index += 1

        if self._coarse_index < len(self._coarse_positions):
            next_z = self._coarse_positions[self._coarse_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.COARSE_BACKWARD,
                current_score=score,
                progress=progress,
                message=f"Backward scan: {self._coarse_index}/{len(self._coarse_positions)}"
            )

        # Backward scan finished → compare results
        if self._backward_measurements:
            best_bwd = max(self._backward_measurements, key=lambda m: m.score)
            self._backward_best_z = best_bwd.z_mm

        self._phase = FocusPhase.COMPARE_RESULTS
        return self._compare_bidirectional_results()

    def _compare_bidirectional_results(self) -> AutofocusResult:
        """
        Compares forward and backward results, calculates hysteresis.
        """
        hysteresis = abs(self._forward_best_z - self._backward_best_z)
        is_significant = hysteresis > self.config.hysteresis_threshold_mm

        # Best result: average or the one with the better score
        fwd_score = max(
            m.score for m in self._forward_measurements) if self._forward_measurements else 0
        bwd_score = max(
            m.score for m in self._backward_measurements) if self._backward_measurements else 0

        if fwd_score >= bwd_score:
            self._best_z = self._forward_best_z
            self._best_score = fwd_score
        else:
            self._best_z = self._backward_best_z
            self._best_score = bwd_score

        self._phase = FocusPhase.FINISHED

        if is_significant:
            message = (
                f"⚠️ Hysteresis is significant: {hysteresis:.3f}mm > {self.config.hysteresis_threshold_mm}mm\n"
                f"   Forward: {self._forward_best_z:.3f}mm, Backward: {self._backward_best_z:.3f}mm"
            )
        else:
            message = (
                f"✓ Hysteresis is negligible: {hysteresis:.3f}mm\n"
                f"   Forward: {self._forward_best_z:.3f}mm, Backward: {self._backward_best_z:.3f}mm"
            )

        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message=message,
            hysteresis_mm=hysteresis,
            forward_focus_mm=self._forward_best_z,
            backward_focus_mm=self._backward_best_z,
            hysteresis_significant=is_significant
        )

    # ══════════════════════════════════════════════════════════════════════════
    # CONTROL METHODS
    # ══════════════════════════════════════════════════════════════════════════

    def abort(self) -> AutofocusResult:
        """
        Aborts the current autofocus search.

        Behavior:
            - The algorithm immediately transitions to the FINISHED phase.
            - The result will be the best position found so far (if any
              measurements were taken).

        Returns:
            An AutofocusResult with the best position found so far.
        """
        self._phase = FocusPhase.FINISHED

        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z if self._best_score > 0 else None,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message="Autofocus aborted"
        )

    def get_measurements(self) -> List[Tuple[float, float]]:
        """
        Returns all measurement points taken during the search.

        Returns:
            A list of (z_mm, score) tuples.
        """
        return [(m.z_mm, m.score) for m in self._measurements]

    @property
    def phase(self) -> FocusPhase:
        """The current phase of the autofocus algorithm."""
        return self._phase

    @property
    def is_running(self) -> bool:
        """True if the autofocus process is currently running."""
        return self._phase not in (FocusPhase.IDLE, FocusPhase.FINISHED)
