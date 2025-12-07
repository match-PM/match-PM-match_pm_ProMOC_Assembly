"""
Hybrid Autofocus Algorithm.

This module provides a hybrid autofocus algorithm that combines:
1. Coarse Search: Linear scan with large steps using variance metric
2. Fine Search: Golden Section Search with tenengrad metric

The algorithm is designed to work with a linear axis for Z-positioning
and a camera for image acquisition.

Usage:
    from promoc_core.algorithms.autofocus import HybridAutofocus, AutofocusConfig
    
    config = AutofocusConfig(
        z_min_mm=0.0,
        z_max_mm=10.0,
        coarse_step_mm=0.5,
        fine_tolerance_mm=0.01
    )
    
    autofocus = HybridAutofocus(config)
    
    # During focus search loop:
    result = autofocus.process_image(current_z, image)
    if result.finished:
        print(f"Best focus at Z={result.best_z_mm:.3f}mm")
    else:
        move_to(result.next_z_mm)

Classes:
    AutofocusConfig: Configuration parameters for autofocus
    AutofocusResult: Result of processing a single image
    HybridAutofocus: Main autofocus algorithm implementation
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Tuple, Callable
import math
import numpy as np

from .focus_metrics import laplacian_variance, tenengrad


# Golden ratio for optimization
GS_PHI = (math.sqrt(5) - 1) / 2  # ≈ 0.618


class FocusPhase(Enum):
    """Current phase of the autofocus algorithm."""
    IDLE = auto()
    COARSE_SEARCH = auto()
    FINE_SEARCH_INIT = auto()
    FINE_SEARCH = auto()
    FINISHED = auto()


@dataclass
class AutofocusConfig:
    """
    Configuration for the hybrid autofocus algorithm.

    Attributes:
        z_min_mm: Minimum Z position in mm
        z_max_mm: Maximum Z position in mm
        coarse_step_mm: Step size for coarse linear scan
        fine_tolerance_mm: Tolerance for golden section search convergence
        fine_metric: Focus metric to use ('variance' or 'tenengrad')
        coarse_metric: Focus metric for coarse search
        min_focus_score: Minimum score to consider valid focus
    """
    z_min_mm: float = 0.0
    z_max_mm: float = 10.0
    coarse_step_mm: float = 0.5
    fine_tolerance_mm: float = 0.01
    fine_metric: str = 'tenengrad'
    coarse_metric: str = 'variance'
    min_focus_score: float = 100.0

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.z_min_mm >= self.z_max_mm:
            raise ValueError(
                f"z_min ({self.z_min_mm}) must be < z_max ({self.z_max_mm})")
        if self.coarse_step_mm <= 0:
            raise ValueError(
                f"coarse_step must be positive, got {self.coarse_step_mm}")
        if self.fine_tolerance_mm <= 0:
            raise ValueError(
                f"fine_tolerance must be positive, got {self.fine_tolerance_mm}")


@dataclass
class AutofocusResult:
    """
    Result of processing one image in the autofocus sequence.

    Attributes:
        finished: True if autofocus is complete
        best_z_mm: Best Z position found (valid when finished=True)
        next_z_mm: Next Z position to move to (valid when finished=False)
        phase: Current phase of the algorithm
        current_score: Focus score of the current image
        best_score: Best focus score found so far
        progress: Estimated progress 0.0 to 1.0
        message: Human-readable status message
    """
    finished: bool = False
    best_z_mm: Optional[float] = None
    next_z_mm: Optional[float] = None
    phase: FocusPhase = FocusPhase.IDLE
    current_score: float = 0.0
    best_score: float = 0.0
    progress: float = 0.0
    message: str = ""


@dataclass
class _FocusMeasurement:
    """Internal: Single focus measurement."""
    z_mm: float
    score: float


class HybridAutofocus:
    """
    Hybrid autofocus combining coarse linear scan with golden section search.

    The algorithm works in two phases:
    1. Coarse Search: Linear scan across Z range with large steps.
       Uses variance metric for speed. Identifies approximate focus region.
    2. Fine Search: Golden Section Search around the best coarse position.
       Uses tenengrad metric for accuracy.

    Usage:
        # Initialize
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
        Initialize the autofocus algorithm.

        Args:
            config: Autofocus configuration parameters
        """
        config.validate()
        self.config = config
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset internal state for new search."""
        self._phase = FocusPhase.IDLE
        self._measurements: List[_FocusMeasurement] = []

        # Coarse search state
        self._coarse_positions: List[float] = []
        self._coarse_index: int = 0

        # Fine search (Golden Section) state
        self._gs_a: float = 0.0  # Lower bound
        self._gs_b: float = 0.0  # Upper bound
        self._gs_c: float = 0.0  # Inner point 1
        self._gs_d: float = 0.0  # Inner point 2
        self._gs_fc: Optional[float] = None  # Score at c
        self._gs_fd: Optional[float] = None  # Score at d
        self._gs_waiting_for: Optional[str] = None  # 'c' or 'd'

        # Best result tracking
        self._best_z: float = 0.0
        self._best_score: float = 0.0

    def start(self) -> float:
        """
        Start a new autofocus search.

        Returns:
            First Z position to move to
        """
        self._reset_state()

        # Generate coarse search positions
        z_range = self.config.z_max_mm - self.config.z_min_mm
        num_steps = int(z_range / self.config.coarse_step_mm) + 1
        self._coarse_positions = [
            self.config.z_min_mm + i * self.config.coarse_step_mm
            for i in range(num_steps)
        ]

        # Ensure we don't exceed z_max
        if self._coarse_positions[-1] > self.config.z_max_mm:
            self._coarse_positions[-1] = self.config.z_max_mm

        self._coarse_index = 0
        self._phase = FocusPhase.COARSE_SEARCH

        return self._coarse_positions[0]

    def process_image(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Process an image and determine the next action.

        Args:
            current_z_mm: Current Z position in mm
            image: Captured image at current position

        Returns:
            AutofocusResult indicating next action or final result
        """
        if self._phase == FocusPhase.IDLE:
            return AutofocusResult(
                finished=False,
                next_z_mm=self.start(),
                phase=FocusPhase.COARSE_SEARCH,
                message="Starting autofocus"
            )

        if self._phase == FocusPhase.COARSE_SEARCH:
            return self._process_coarse(current_z_mm, image)

        if self._phase == FocusPhase.FINE_SEARCH_INIT:
            return self._init_fine_search(current_z_mm, image)

        if self._phase == FocusPhase.FINE_SEARCH:
            return self._process_fine(current_z_mm, image)

        # Already finished
        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message="Autofocus complete"
        )

    def _compute_metric(self, image: np.ndarray, metric_type: str) -> float:
        """Compute focus metric for image."""
        if metric_type == 'variance':
            return laplacian_variance(image)
        elif metric_type == 'tenengrad':
            return tenengrad(image)
        else:
            raise ValueError(f"Unknown metric: {metric_type}")

    def _process_coarse(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """Process image during coarse search phase."""
        # Compute focus metric
        score = self._compute_metric(image, self.config.coarse_metric)

        # Store measurement
        self._measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        # Track best
        if score > self._best_score:
            self._best_score = score
            self._best_z = current_z_mm

        # Calculate progress
        progress = (self._coarse_index + 1) / len(self._coarse_positions) * 0.5

        # Move to next position
        self._coarse_index += 1

        if self._coarse_index < len(self._coarse_positions):
            # Continue coarse search
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

        # Coarse search complete - transition to fine search
        return self._start_fine_search()

    def _start_fine_search(self) -> AutofocusResult:
        """Initialize fine search around best coarse position."""
        if not self._measurements:
            return AutofocusResult(
                finished=True,
                best_z_mm=self.config.z_min_mm,
                phase=FocusPhase.FINISHED,
                message="No measurements collected"
            )

        # Find best measurement and set search bounds
        best_idx = max(range(len(self._measurements)),
                       key=lambda i: self._measurements[i].score)
        best_z = self._measurements[best_idx].z_mm

        # Set bounds around best position (±1 coarse step)
        half_range = self.config.coarse_step_mm * 1.5
        self._gs_a = max(self.config.z_min_mm, best_z - half_range)
        self._gs_b = min(self.config.z_max_mm, best_z + half_range)

        # Golden section points
        self._gs_c = self._gs_b - GS_PHI * (self._gs_b - self._gs_a)
        self._gs_d = self._gs_a + GS_PHI * (self._gs_b - self._gs_a)

        self._gs_fc = None
        self._gs_fd = None
        self._gs_waiting_for = 'c'

        self._phase = FocusPhase.FINE_SEARCH_INIT

        return AutofocusResult(
            finished=False,
            next_z_mm=self._gs_c,
            phase=FocusPhase.FINE_SEARCH_INIT,
            best_score=self._best_score,
            progress=0.5,
            message="Starting fine search"
        )

    def _init_fine_search(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """Initialize golden section search with first measurements."""
        score = self._compute_metric(image, self.config.fine_metric)

        if self._gs_waiting_for == 'c':
            self._gs_fc = score
            self._gs_waiting_for = 'd'

            # Update best if needed
            if score > self._best_score:
                self._best_score = score
                self._best_z = current_z_mm

            return AutofocusResult(
                finished=False,
                next_z_mm=self._gs_d,
                phase=FocusPhase.FINE_SEARCH_INIT,
                current_score=score,
                best_score=self._best_score,
                progress=0.55,
                message="Fine search: measuring second point"
            )

        # Got both points, transition to fine search
        self._gs_fd = score
        if score > self._best_score:
            self._best_score = score
            self._best_z = current_z_mm

        self._phase = FocusPhase.FINE_SEARCH

        # Do first iteration
        return self._golden_section_step()

    def _process_fine(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """Process image during fine (golden section) search."""
        score = self._compute_metric(image, self.config.fine_metric)

        # Update the appropriate point
        if self._gs_waiting_for == 'c':
            self._gs_fc = score
        else:
            self._gs_fd = score

        # Update best
        if score > self._best_score:
            self._best_score = score
            self._best_z = current_z_mm

        return self._golden_section_step()

    def _golden_section_step(self) -> AutofocusResult:
        """Perform one step of golden section search."""
        # Check convergence
        interval = abs(self._gs_b - self._gs_a)

        progress = 0.5 + 0.5 * \
            (1.0 - interval / (self.config.coarse_step_mm * 3))
        progress = min(0.99, max(0.5, progress))

        if interval < self.config.fine_tolerance_mm:
            # Converged
            self._best_z = (self._gs_a + self._gs_b) / 2
            self._phase = FocusPhase.FINISHED

            return AutofocusResult(
                finished=True,
                best_z_mm=self._best_z,
                phase=FocusPhase.FINISHED,
                best_score=self._best_score,
                progress=1.0,
                message=f"Focus found at Z={self._best_z:.4f}mm"
            )

        # Golden section update
        # We want to MAXIMIZE focus score, so keep the side with higher score
        if self._gs_fc is not None and self._gs_fd is not None:
            if self._gs_fc > self._gs_fd:
                # Maximum is in [a, d]
                self._gs_b = self._gs_d
                self._gs_d = self._gs_c
                self._gs_fd = self._gs_fc
                self._gs_c = self._gs_b - GS_PHI * (self._gs_b - self._gs_a)
                self._gs_fc = None
                self._gs_waiting_for = 'c'
                next_z = self._gs_c
            else:
                # Maximum is in [c, b]
                self._gs_a = self._gs_c
                self._gs_c = self._gs_d
                self._gs_fc = self._gs_fd
                self._gs_d = self._gs_a + GS_PHI * (self._gs_b - self._gs_a)
                self._gs_fd = None
                self._gs_waiting_for = 'd'
                next_z = self._gs_d
        else:
            # Should not happen, but handle gracefully
            next_z = (self._gs_a + self._gs_b) / 2
            self._gs_waiting_for = 'c'

        return AutofocusResult(
            finished=False,
            next_z_mm=next_z,
            phase=FocusPhase.FINE_SEARCH,
            best_score=self._best_score,
            progress=progress,
            message=f"Fine search: interval={interval:.4f}mm"
        )

    def abort(self) -> AutofocusResult:
        """
        Abort the current autofocus search.

        Returns:
            Result with best position found so far
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
        Get all measurements taken during search.

        Returns:
            List of (z_mm, score) tuples
        """
        return [(m.z_mm, m.score) for m in self._measurements]

    @property
    def phase(self) -> FocusPhase:
        """Current phase of the autofocus algorithm."""
        return self._phase

    @property
    def is_running(self) -> bool:
        """True if autofocus is currently running."""
        return self._phase not in (FocusPhase.IDLE, FocusPhase.FINISHED)
