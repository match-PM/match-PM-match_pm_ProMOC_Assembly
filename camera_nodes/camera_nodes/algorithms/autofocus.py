"""Autofocus API and core algorithm logic for camera_nodes.

This module contains:
- Shared data structures (`AutofocusConfig`, `AutofocusResult`, `Phase`)
- The core MSPR autofocus implementation (`MSPRAutofocus`)
- Lazy exports for optional strategy variants from `autofocus_strategies`
"""

from dataclasses import dataclass
from enum import Enum, auto
from importlib import import_module
from typing import TYPE_CHECKING
import numpy as np
import cv2

# Import tenengrad from focus_metrics to avoid duplication.
from .focus_metrics import tenengrad


# =============================================================================
# MATHEMATICAL CONSTANTS
# =============================================================================
GOLDEN_RATIO = (1 + 5**0.5) / 2  # phi ~= 1.618
PHI_COMPLEMENT = 1 / GOLDEN_RATIO  # 1/phi ~= 0.618 (golden section multiplier)
PHI_SMALL = 2 - GOLDEN_RATIO  # 2-phi ~= 0.382 (probe point placement)


# =============================================================================
# ALGORITHM TUNING CONSTANTS  
# =============================================================================
DEFAULT_COARSE_STEP_MM = 0.5
DEFAULT_MIN_STEP_MM = 0.01
DEFAULT_SHRINK_FACTOR = 0.45
DEFAULT_EARLY_TERM_THRESHOLD = 0.7
DEFAULT_EARLY_TERM_COUNT = 3



class Phase(Enum):
    """Current phase of the autofocus algorithm."""
    IDLE = auto()
    COARSE_SCAN = auto()
    REFINEMENT = auto()
    FINISHED = auto()


@dataclass
class AutofocusConfig:
    """
    Configuration for autofocus algorithm.
    
    Attributes:
        start_mm: Starting position in mm
        end_mm: Ending position in mm
        step_mm: Step size for coarse scan in mm
        refinement_samples: Number of samples per refinement level
        min_step_mm: Minimum step size (stop refinement when reached)
        shrink_factor: Factor to reduce search range each level (0-1)
        early_termination_threshold: Score threshold for early termination (0-1)
            If score drops below (threshold * best_score) for consecutive measurements,
            skip remaining points in current refinement level. Default: 0.7 (70%)
        early_termination_count: Number of consecutive low measurements to trigger
            early termination. Default: 3
    """
    start_mm: float = 0.0
    end_mm: float = 10.0
    step_mm: float = 0.5
    refinement_samples: int = 31  # Reduced from 51 for speed
    min_step_mm: float = 0.01
    shrink_factor: float = 0.45   # Increased from 0.35 for safety (wider range)
    early_termination_threshold: float = 0.7
    early_termination_count: int = 3
    use_sift_weighting: bool = False
    
    # Coarse scan optimization
    coarse_terminate_threshold: float = 0.6  # Drop below 60% of peak triggers check
    coarse_terminate_count: int = 2          # Confirm over 2 measurements
    disable_coarse_early_termination: bool = False  # Set True to scan full range
    
    def validate(self):
        """Validate configuration parameters."""
        if self.start_mm >= self.end_mm:
            raise ValueError(f"start_mm ({self.start_mm}) must be < end_mm ({self.end_mm})")
        if self.step_mm <= 0:
            raise ValueError(f"step_mm must be positive, got {self.step_mm}")
        if self.refinement_samples < 5:
            raise ValueError(f"refinement_samples must be >= 5, got {self.refinement_samples}")
        if self.min_step_mm <= 0:
            raise ValueError(f"min_step_mm must be positive, got {self.min_step_mm}")
        if not (0.0 < self.shrink_factor < 1.0):
            raise ValueError(f"shrink_factor must be between 0 and 1, got {self.shrink_factor}")
        if not (0.0 < self.early_termination_threshold <= 1.0):
            raise ValueError(f"early_termination_threshold must be between 0 and 1, got {self.early_termination_threshold}")
        if self.early_termination_count < 1:
            raise ValueError(f"early_termination_count must be >= 1, got {self.early_termination_count}")


@dataclass
class AutofocusResult:
    """
    Result of a single autofocus iteration.
    
    Attributes:
        finished: True if autofocus is complete
        next_position_mm: Next position to move to (None if finished)
        best_position_mm: Best focus position found so far
        best_score: Best sharpness score found so far
        current_score: Sharpness score of current image
        phase: Current algorithm phase
        progress: Estimated progress (0.0 to 1.0)
        current_level: Current refinement level (0 = coarse scan)
        current_step_mm: Current step size
        current_range_mm: Current search range (+/-)
    """
    finished: bool = False
    next_position_mm: float | None = None
    best_position_mm: float | None = None
    best_score: float = 0.0
    current_score: float = 0.0
    phase: Phase = Phase.IDLE
    progress: float = 0.0
    current_level: int = 0
    current_step_mm: float | None = None
    current_range_mm: float | None = None


@dataclass
class _Measurement:
    """Internal class for storing a measurement."""
    position_mm: float
    score: float


class MSPRAutofocus:
    """
    Multi-Stage Parabolic Refinement (MSPR) Autofocus.
    
    Algorithm:
    1. Coarse Scan: Linear scan from start to end with step_mm
    2. Find coarse maximum
    3. Refinement Loop:
       - Reduce search range around maximum
       - Sample ~refinement_samples points in new range
       - Find new maximum
       - Repeat until step size < min_step_mm
    4. Subpixel Interpolation: Calculate quadratic peak around final best point
    """
    
    def __init__(self, config: AutofocusConfig):
        """
        Initialize autofocus algorithm.
        
        Args:
            config: Autofocus configuration
        """
        config.validate()
        self.config = config
        
        # State
        self._phase = Phase.IDLE
        self._measurements: list[_Measurement] = []
        self._best_measurement: _Measurement | None = None
        self._sift = None
        
        # Coarse scan state
        self._coarse_positions: list[float] = []
        self._coarse_index: int = 0
        
        # Refinement state
        self._refinement_level: int = 0
        self._refinement_positions: list[float] = []
        self._refinement_index: int = 0
        self._current_range_mm: float = 0.0
        self._current_step_mm: float = 0.0
        self._low_score_counter: int = 0  # Counter for early termination
        self._coarse_drop_counter: int = 0  # Counter for coarse scan early termination
        self._asymmetric_range: str | None = None  # 'lower', 'upper', or None for symmetric

    def _reset_runtime_state(self) -> None:
        """Reset per-run algorithm state before starting a new autofocus cycle."""
        self._phase = Phase.IDLE
        self._measurements = []
        self._best_measurement = None

        self._coarse_positions = []
        self._coarse_index = 0

        self._refinement_level = 0
        self._refinement_positions = []
        self._refinement_index = 0
        self._current_range_mm = 0.0
        self._current_step_mm = 0.0
        self._low_score_counter = 0
        self._coarse_drop_counter = 0
        self._asymmetric_range = None

    def start(self) -> float:
        """
        Start the autofocus process.
        
        Returns:
            Initial position to move to
        """
        # --- Step 1: Reset any state from a previous autofocus run. ---
        self._reset_runtime_state()

        # --- Step 2: Generate the coarse linear scan grid. ---
        self._coarse_positions = list(np.arange(
            self.config.start_mm,
            self.config.end_mm + self.config.step_mm / 2,
            self.config.step_mm
        ))

        # --- Step 3: Clamp the grid to valid travel and remove duplicates. ---
        self._coarse_positions = self._clamp_positions(self._coarse_positions)
        
        self._phase = Phase.COARSE_SCAN
        
        return self._coarse_positions[0]
    
    def process_image(self, position_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Process an image and determine next action.
        
        Args:
            position_mm: Current axis position in mm
            image: Current camera image
            
        Returns:
            AutofocusResult with next action
        """
        # --- Step 1: Score the current image at the current axis position. ---
        score = self._calculate_score(image)
        self._store_measurement(position_mm, score)

        # --- Step 2: Let the current algorithm phase decide the next move. ---
        if self._phase == Phase.COARSE_SCAN:
            return self._handle_coarse_scan()
        elif self._phase == Phase.REFINEMENT:
            return self._handle_refinement()
        else:
            return self._make_result(finished=True, phase=Phase.FINISHED)

    def _set_best_measurement(self, position_mm: float, score: float) -> _Measurement:
        """Set and return the best measurement explicitly."""
        measurement = _Measurement(float(position_mm), float(score))
        self._best_measurement = measurement
        return measurement

    def _store_measurement(
        self,
        position_mm: float,
        score: float,
        fallback_to_previous: bool = False
    ) -> tuple[_Measurement, bool]:
        """
        Store a measurement and update the current best measurement.

        Returns:
            Tuple of (stored measurement, improved flag).
        """
        final_score = float(score)
        if fallback_to_previous and final_score <= 0.0 and self._measurements:
            final_score = float(self._measurements[-1].score)

        measurement = _Measurement(float(position_mm), final_score)
        self._measurements.append(measurement)

        improved = self._best_measurement is None or final_score > self._best_measurement.score
        if improved:
            self._best_measurement = measurement

        return measurement, improved

    def _get_sift(self):
        if self._sift is None:
            if hasattr(cv2, 'SIFT_create'):
                self._sift = cv2.SIFT_create()
            else:
                self._sift = False
        return self._sift

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Return a grayscale view of the image for texture-based scoring."""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def _sift_weight(self, gray: np.ndarray) -> float:
        sift = self._get_sift()
        if sift is False:
            return 1.0

        if gray.size == 0:
            return 1.0

        roi_small = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        if roi_small.size == 0:
            return 1.0

        keypoints = sift.detect(roi_small, None)
        area = float(roi_small.shape[0] * roi_small.shape[1])
        density = (len(keypoints) / area) if area > 0 else 0.0
        return 1.0 + (density * 1000.0)

    def _should_apply_sift_weighting(self) -> bool:
        """SIFT weighting is only meaningful during local refinement."""
        return self.config.use_sift_weighting and self._phase == Phase.REFINEMENT

    def _compute_base_focus_score(self, image: np.ndarray) -> float:
        """Compute the baseline sharpness metric for a frame."""
        return float(tenengrad(image))

    def _calculate_score(self, image: np.ndarray) -> float:
        # --- Step 1: Compute the baseline sharpness score. ---
        base_score = self._compute_base_focus_score(image)

        # --- Step 2: Optionally emphasize textured regions during refinement. ---
        if self._should_apply_sift_weighting():
            try:
                gray = self._to_grayscale(image)
                return base_score * self._sift_weight(gray)
            except Exception:
                return base_score

        return base_score

    # =========================================================================
    # PUBLIC HOOKS (HANDLER-FACING API)
    # =========================================================================

    def score_image(self, image: np.ndarray) -> float:
        """Public score hook for external orchestrators."""
        return float(self._calculate_score(image))

    def get_measurement_series(self) -> tuple[list[float], list[float]]:
        """Return measured positions and scores in acquisition order."""
        positions = [float(measure.position_mm) for measure in self._measurements]
        scores = [float(measure.score) for measure in self._measurements]
        return positions, scores

    def get_best_result(self) -> tuple[float | None, float]:
        """Return best (position, score) found so far."""
        if self._best_measurement is None:
            return None, 0.0
        return float(self._best_measurement.position_mm), float(
            self._best_measurement.score
        )

    def get_scan_step_mm(self) -> float:
        """Return active scan step if strategy defines one, otherwise config step."""
        return float(getattr(self, "_scan_step", self.config.step_mm))

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _calculate_subpixel_peak(self, x_vals: list[float], scores: list[float]) -> float:
        """
        Perform quadratic interpolation around the best measured point.
        
        Args:
            x_vals: List of positions
            scores: List of corresponding focus scores
            
        Returns:
            Interpolated subpixel peak position
        """
        if len(scores) < 3:
            return x_vals[np.argmax(scores)] if x_vals else 0.0
            
        # 1. Find index of maximum
        best_idx = int(np.argmax(scores))
        
        # Check boundary conditions (peak must not be at start or end)
        if best_idx == 0 or best_idx == len(scores) - 1:
            return x_vals[best_idx] # Fallback to discrete value

        # 2. Extract the 3 points
        x1, y1 = x_vals[best_idx - 1], scores[best_idx - 1]
        x2, y2 = x_vals[best_idx],     scores[best_idx]
        x3, y3 = x_vals[best_idx + 1], scores[best_idx + 1]

        # 3. Parabola fit (inverse parabolic interpolation)
        # Using the vertex formula for a parabola passing through 3 points
        denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
        if abs(denom) < 1e-12:
            return x2

        a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
        b = (x3**2 * (y1 - y2) + x2**2 * (y3 - y1) + x1**2 * (y2 - y3)) / denom
        
        # If a >= 0, it's not a downward opening parabola (maximum)
        if a >= 0 or abs(a) < 1e-9:
            return x2

        # Vertex (maximum) at x = -b / (2 * a)
        exact_peak_x = -b / (2 * a)

        # Plausibility check: The calculated peak must be within the interval of neighbors
        if not (min(x1, x3) <= exact_peak_x <= max(x1, x3)):
            return x2

        return float(exact_peak_x)

    def _make_result(self, 
                     finished: bool = False,
                     next_position: float | None = None,
                     phase: Phase | None = None,
                     progress: float = 0.0) -> AutofocusResult:
        """
        Create an AutofocusResult with current state.
        
        Reduces boilerplate by auto-filling common fields from internal state.
        
        Args:
            finished: Whether autofocus is complete
            next_position: Next position to move to (None if finished)
            phase: Current phase (defaults to self._phase)
            progress: Progress 0.0-1.0
            
        Returns:
            AutofocusResult with all fields populated
        """
        current_score = self._measurements[-1].score if self._measurements else 0.0
        
        return AutofocusResult(
            finished=finished,
            next_position_mm=next_position,
            best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
            best_score=self._best_measurement.score if self._best_measurement else 0.0,
            current_score=current_score,
            phase=phase or self._phase,
            progress=progress,
            current_level=self._refinement_level,
            current_step_mm=self._current_step_mm,
            current_range_mm=self._current_range_mm
        )

    def _transition_to_refinement(self, progress: float) -> AutofocusResult:
        """Prepare the next refinement window and return its first move."""
        self._prepare_refinement()
        result = self._make_result(
            next_position=self._refinement_positions[0],
            phase=Phase.COARSE_SCAN,
            progress=progress,
        )
        self._phase = Phase.REFINEMENT
        return result

    def _collect_measurements_for_positions(
        self, positions: list[float]
    ) -> list[tuple[float, float]]:
        """Return measured (position, score) pairs that belong to a probe list."""
        return [
            (measurement.position_mm, measurement.score)
            for measurement in self._measurements
            if any(abs(measurement.position_mm - pos) < 1e-6 for pos in positions)
        ]

    def _finalize_subpixel_peak(self) -> None:
        """Refine the final best position by quadratic interpolation."""
        if not self._best_measurement or not self._refinement_positions:
            return

        final_coords = self._collect_measurements_for_positions(self._refinement_positions)
        final_coords.sort(key=lambda coord: coord[0])

        if len(final_coords) < 3:
            return

        x_vals = [coord[0] for coord in final_coords]
        scores = [coord[1] for coord in final_coords]
        subpixel_pos = self._calculate_subpixel_peak(x_vals, scores)

        if abs(subpixel_pos - self._best_measurement.position_mm) > 1e-6:
            # Keep the measured peak score, but replace the position with the
            # interpolated maximum of the fitted parabola.
            self._best_measurement.position_mm = subpixel_pos

    def _clamp_positions(self, positions: list[float]) -> list[float]:
        """
        Clamp positions to valid range and remove duplicates.
        
        Args:
            positions: List of positions to clamp
            
        Returns:
            Sorted list of unique positions within [start_mm, end_mm]
        """
        # Clamp to valid range
        clamped = [
            max(self.config.start_mm, min(self.config.end_mm, pos))
            for pos in positions
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for pos in clamped:
            # Round to avoid floating point duplicates
            rounded = round(pos, 6)
            if rounded not in seen:
                seen.add(rounded)
                unique.append(pos)
        
        # Sort ascending for unidirectional scanning
        unique.sort()
        return unique
    
    def _handle_coarse_scan(self) -> AutofocusResult:
        """Handle coarse scan phase."""
        # --- Step 1: Advance the coarse scan cursor. ---
        self._coarse_index += 1

        # --- Step 2: Detect whether the scan already moved past the peak. ---
        current_score = self._measurements[-1].score
        best_score = self._best_measurement.score if self._best_measurement else 0.0

        if not self.config.disable_coarse_early_termination and best_score > 0 and self._coarse_index > 3:
            if current_score < best_score * self.config.coarse_terminate_threshold:
                self._coarse_drop_counter += 1
            else:
                self._coarse_drop_counter = 0

            if self._coarse_drop_counter >= self.config.coarse_terminate_count:
                # Peak crossed - transition to refinement
                return self._transition_to_refinement(progress=0.5)

        # --- Step 3: Keep scanning while coarse positions remain. ---
        if self._coarse_index < len(self._coarse_positions):
            progress = self._coarse_index / len(self._coarse_positions)
            return self._make_result(
                next_position=self._coarse_positions[self._coarse_index],
                phase=Phase.COARSE_SCAN,
                progress=progress
            )
        
        # --- Step 4: Coarse scan is complete, so initialize refinement. ---
        if not self._best_measurement:
            return self._make_result(finished=True, phase=Phase.FINISHED)
        
        return self._transition_to_refinement(progress=0.5)
    
    def _handle_refinement(self) -> AutofocusResult:
        """
        Handle refinement phase with early termination.
        
        Early termination saves time by skipping remaining measurements when
        we're clearly past the peak.
        """
        current_score = self._measurements[-1].score
        best_score = self._best_measurement.score if self._best_measurement else 0.0
        
        # --- Step 1: Decide whether the current refinement level should stop early. ---
        if best_score > 0:
            threshold = best_score * self.config.early_termination_threshold
            if current_score < threshold:
                self._low_score_counter += 1
            else:
                self._low_score_counter = 0
            
            if self._low_score_counter >= self.config.early_termination_count:
                self._low_score_counter = 0
                
                # Check if we need another level
                if self._current_step_mm <= self.config.min_step_mm:
                    self._phase = Phase.FINISHED
                    return self._make_result(finished=True, phase=Phase.FINISHED, progress=1.0)
                
                # Start next refinement level
                self._prepare_refinement()
                progress = 0.6 + 0.1 * self._refinement_level
                return self._make_result(
                    next_position=self._refinement_positions[0],
                    phase=Phase.REFINEMENT,
                    progress=progress
                )
        
        # --- Step 2: Otherwise continue sampling inside the current refinement window. ---
        self._refinement_index += 1

        if self._refinement_index < len(self._refinement_positions):
            progress = 0.5 + 0.5 * (self._refinement_index / len(self._refinement_positions))
            return self._make_result(
                next_position=self._refinement_positions[self._refinement_index],
                phase=Phase.REFINEMENT,
                progress=progress
            )
        
        # --- Step 3: Current refinement level is complete. Decide whether to stop. ---
        if self._current_step_mm <= self.config.min_step_mm:
            # --- Step 3a: Fit a parabola around the final local maximum. ---
            self._finalize_subpixel_peak()
            self._phase = Phase.FINISHED
            return self._make_result(finished=True, phase=Phase.FINISHED, progress=1.0)
        
        # --- Step 4: Shrink the search window and start the next level. ---
        self._prepare_refinement()
        progress = 0.6 + 0.1 * self._refinement_level
        return self._make_result(
            next_position=self._refinement_positions[0],
            phase=Phase.REFINEMENT,
            progress=progress
        )
    
    def _prepare_refinement(self):
        """Prepare a new refinement level around current best position.
        
        Note: This does NOT change self._phase - caller must do that after
        returning the result for the current measurement.
        """
        if not self._best_measurement:
            return
        
        # --- Step 1: Reset counters and center the new window on the best sample. ---
        self._low_score_counter = 0
        
        center = self._best_measurement.position_mm
        
        # --- Step 2: Shrink the search range for the next refinement pass. ---
        if self._refinement_level == 0:
            # The first refinement either uses a caller-provided range or derives one
            # from the original full scan width.
            if self._current_range_mm == 0.0:
                total_range = self.config.end_mm - self.config.start_mm
                self._current_range_mm = total_range * self.config.shrink_factor
        else:
            self._current_range_mm *= self.config.shrink_factor
        
        # --- Step 3: Derive a step size that yields roughly refinement_samples points. ---
        self._current_step_mm = (2 * self._current_range_mm) / (self.config.refinement_samples - 1)
        
        # Clamp to min_step_mm
        if self._current_step_mm < self.config.min_step_mm:
            self._current_step_mm = self.config.min_step_mm
        
        # --- Step 4: Build the probe positions for the new window. ---
        if self._asymmetric_range == 'lower':
            range_start = max(self.config.start_mm, center - 2 * self._current_range_mm)
            range_end = center
        elif self._asymmetric_range == 'upper':
            range_start = center
            range_end = min(self.config.end_mm, center + 2 * self._current_range_mm)
        else:
            # Symmetric range (default)
            range_start = max(self.config.start_mm, center - self._current_range_mm)
            range_end = min(self.config.end_mm, center + self._current_range_mm)
        
        # Reset asymmetric flag after using it
        self._asymmetric_range = None
        
        # Ensure range_start < range_end
        if range_start > range_end:
            range_start, range_end = range_end, range_start
        
        # Generate positions
        raw_positions = list(np.arange(
            range_start,
            range_end + self._current_step_mm / 2,
            self._current_step_mm
        ))
        
        # Clamp and deduplicate using helper
        self._refinement_positions = self._clamp_positions(raw_positions)
        
        # Start one step BEFORE the peak for unidirectional scanning
        if self._refinement_positions:
            best_in_list = min(self._refinement_positions, key=lambda p: abs(p - center))
            best_idx = self._refinement_positions.index(best_in_list)
            
            if best_idx > 0:
                self._refinement_positions = self._refinement_positions[best_idx - 1:]
        
        self._refinement_level += 1

_STRATEGY_CLASS_TO_MODULE = {
    'ParabolicAutofocus': 'parabolic',
    'IterativeParabolicAutofocus': 'parabolic',
    'GoldenSectionAutofocus': 'golden_section',
    'HillClimbingAutofocus': 'hill_climbing',
    'FourStepAutofocus': 'four_step',
    'ExhaustiveAutofocus': 'exhaustive',
    'FibonacciAutofocus': 'fibonacci',
}


def __getattr__(name: str):
    module_name = _STRATEGY_CLASS_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    module = import_module(f'.autofocus_strategies.{module_name}', __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


if TYPE_CHECKING:
    from .autofocus_strategies.exhaustive import ExhaustiveAutofocus
    from .autofocus_strategies.fibonacci import FibonacciAutofocus
    from .autofocus_strategies.four_step import FourStepAutofocus
    from .autofocus_strategies.golden_section import GoldenSectionAutofocus
    from .autofocus_strategies.hill_climbing import HillClimbingAutofocus
    from .autofocus_strategies.parabolic import (
        IterativeParabolicAutofocus,
        ParabolicAutofocus,
    )

__all__ = [
    'AutofocusConfig',
    'AutofocusResult',
    'Phase',
    'MSPRAutofocus',
    'ParabolicAutofocus',
    'IterativeParabolicAutofocus',
    'GoldenSectionAutofocus',
    'HillClimbingAutofocus',
    'FourStepAutofocus',
    'ExhaustiveAutofocus',
    'FibonacciAutofocus',
    'tenengrad',
    'GOLDEN_RATIO',
    'PHI_COMPLEMENT',
    'PHI_SMALL',
    'DEFAULT_COARSE_STEP_MM',
    'DEFAULT_MIN_STEP_MM',
    'DEFAULT_SHRINK_FACTOR',
    'DEFAULT_EARLY_TERM_THRESHOLD',
    'DEFAULT_EARLY_TERM_COUNT',
]
