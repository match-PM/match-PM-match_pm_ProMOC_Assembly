"""
Simple Autofocus Algorithm with Multi-Level Refinement.

Simplified autofocus specifically designed for camera_nodes.
Features:
- Linear scan from start to end position
- Multi-level refinement around detected maximum
- Tenengrad sharpness metric
- No hysteresis compensation (assumed unidirectional movement)

Algorithm:
1. Coarse Scan: Scan full range with given step size
2. Refinement Levels: Iteratively narrow search range around maximum
   - Each level: sample ~N points in reduced range
   - Stop when step size reaches minimum threshold

Usage:
    from camera_nodes.autofocus import Autofocus, AutofocusConfig
    
    config = AutofocusConfig(
        start_mm=0.0,
        end_mm=10.0,
        step_mm=0.5,
        refinement_samples=51,
        min_step_mm=0.01
    )
    
    af = Autofocus(config)
    position = af.start()  # Returns initial position
    
    while True:
        image = get_camera_image()
        result = af.process_image(position, image)
        
        if result.finished:
            print(f"Best focus: {result.best_position_mm}mm")
            break
        
        position = result.next_position_mm
        move_axis(position)
"""

from dataclasses import dataclass
from enum import Enum, auto
import numpy as np
import cv2

# Import tenengrad from focus_metrics to avoid duplication
from .focus_metrics import tenengrad


# =============================================================================
# MATHEMATICAL CONSTANTS
# =============================================================================
GOLDEN_RATIO = (1 + 5**0.5) / 2  # φ ≈ 1.618
PHI_COMPLEMENT = 1 / GOLDEN_RATIO  # 1/φ ≈ 0.618 (golden section multiplier)
PHI_SMALL = 2 - GOLDEN_RATIO  # 2-φ ≈ 0.382 (for probe point placement)


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
        current_range_mm: Current search range (±)
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
        
    def start(self) -> float:
        """
        Start the autofocus process.
        
        Returns:
            Initial position to move to
        """
        # Generate coarse scan positions
        self._coarse_positions = list(np.arange(
            self.config.start_mm,
            self.config.end_mm + self.config.step_mm / 2,
            self.config.step_mm
        ))
        
        # Clamp all positions to valid range [start_mm, end_mm]
        # Clamp and deduplicate using helper
        self._coarse_positions = self._clamp_positions(self._coarse_positions)
        
        self._coarse_index = 0
        self._coarse_drop_counter = 0
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
        # Calculate sharpness
        score = self._calculate_score(image)
        
        # Store measurement
        measurement = _Measurement(position_mm, score)
        self._measurements.append(measurement)
        
        # Update best
        if self._best_measurement is None or score > self._best_measurement.score:
            self._best_measurement = measurement
        
        # State machine
        if self._phase == Phase.COARSE_SCAN:
            return self._handle_coarse_scan()
        elif self._phase == Phase.REFINEMENT:
            return self._handle_refinement()
        else:
            return self._make_result(finished=True, phase=Phase.FINISHED)

    def _get_sift(self):
        if self._sift is None:
            if hasattr(cv2, 'SIFT_create'):
                self._sift = cv2.SIFT_create()
            else:
                self._sift = False
        return self._sift

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

    def _calculate_score(self, image: np.ndarray) -> float:
        base_score = tenengrad(image)

        if self.config.use_sift_weighting and self._phase == Phase.REFINEMENT:
            try:
                gray = image
                if len(image.shape) == 3:
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                return base_score * self._sift_weight(gray)
            except Exception:
                return base_score

        return base_score

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

        # 3. Parabel-Fit (Inverse Parabolic Interpolation)
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
        self._coarse_index += 1
        
        # Check for early exit (Peak crossed)
        current_score = self._measurements[-1].score
        best_score = self._best_measurement.score if self._best_measurement else 0.0

        if not self.config.disable_coarse_early_termination and best_score > 0 and self._coarse_index > 3:
            if current_score < best_score * self.config.coarse_terminate_threshold:
                self._coarse_drop_counter += 1
            else:
                self._coarse_drop_counter = 0

            if self._coarse_drop_counter >= self.config.coarse_terminate_count:
                # Peak crossed - transition to refinement
                self._prepare_refinement()
                result = self._make_result(
                    next_position=self._refinement_positions[0],
                    phase=Phase.COARSE_SCAN,
                    progress=0.5
                )
                self._phase = Phase.REFINEMENT
                return result

        # Continue coarse scan?
        if self._coarse_index < len(self._coarse_positions):
            progress = self._coarse_index / len(self._coarse_positions)
            return self._make_result(
                next_position=self._coarse_positions[self._coarse_index],
                phase=Phase.COARSE_SCAN,
                progress=progress
            )
        
        # Coarse scan complete → start refinement
        if not self._best_measurement:
            return self._make_result(finished=True, phase=Phase.FINISHED)
        
        self._prepare_refinement()
        result = self._make_result(
            next_position=self._refinement_positions[0],
            phase=Phase.COARSE_SCAN,
            progress=0.5
        )
        self._phase = Phase.REFINEMENT
        return result
    
    def _handle_refinement(self) -> AutofocusResult:
        """
        Handle refinement phase with early termination.
        
        Early termination saves time by skipping remaining measurements when
        we're clearly past the peak.
        """
        current_score = self._measurements[-1].score
        best_score = self._best_measurement.score if self._best_measurement else 0.0
        
        # Check for early termination
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
        
        self._refinement_index += 1
        
        # Continue current refinement level?
        if self._refinement_index < len(self._refinement_positions):
            progress = 0.5 + 0.5 * (self._refinement_index / len(self._refinement_positions))
            return self._make_result(
                next_position=self._refinement_positions[self._refinement_index],
                phase=Phase.REFINEMENT,
                progress=progress
            )
        
        # Current level complete → check if we need another level
        if self._current_step_mm <= self.config.min_step_mm:
            # --- MSPR ENHANCEMENT: Quadratic Interpolation ---
            # Use the measurements from the final refinement level for subpixel accuracy
            final_coords = [(m.position_mm, m.score) for m in self._measurements 
                           if any(abs(m.position_mm - p) < 1e-6 for p in self._refinement_positions)]
            
            # Sort by position
            final_coords.sort(key=lambda x: x[0])
            if len(final_coords) >= 3:
                x_vals = [c[0] for c in final_coords]
                scores = [c[1] for c in final_coords]
                subpixel_pos = self._calculate_subpixel_peak(x_vals, scores)
                
                if abs(subpixel_pos - self._best_measurement.position_mm) > 1e-6:
                    # Update best measurement with interpolated position
                    # We keep the discrete best score as the "true" measured peak score
                    # but move the position to the interpolated maximum.
                    self._best_measurement.position_mm = subpixel_pos
            
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
    
    def _prepare_refinement(self):
        """Prepare a new refinement level around current best position.
        
        Note: This does NOT change self._phase - caller must do that after
        returning the result for the current measurement.
        """
        if not self._best_measurement:
            return
        
        # Reset early termination counter for new level
        self._low_score_counter = 0
        
        center = self._best_measurement.position_mm
        
        # Calculate new range and step size
        if self._refinement_level == 0:
            # First refinement: use configured shrink factor OR pre-set range
            # (ParabolicAutofocus may pre-set _current_range_mm for tight refinement)
            if self._current_range_mm == 0.0:
                total_range = self.config.end_mm - self.config.start_mm
                self._current_range_mm = total_range * self.config.shrink_factor
        else:
            # Subsequent levels: shrink further
            self._current_range_mm *= self.config.shrink_factor
        
        # Calculate step size to get approximately refinement_samples points
        self._current_step_mm = (2 * self._current_range_mm) / (self.config.refinement_samples - 1)
        
        # Clamp to min_step_mm
        if self._current_step_mm < self.config.min_step_mm:
            self._current_step_mm = self.config.min_step_mm
        
        # Generate refinement positions (symmetric or asymmetric)
        if self._asymmetric_range == 'lower':
            # Only search below best (focus peak is on lower side)
            range_start = max(self.config.start_mm, center - 2 * self._current_range_mm)
            range_end = center
        elif self._asymmetric_range == 'upper':
            # Only search above best (focus peak is on upper side)
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


class ParabolicAutofocus(MSPRAutofocus):
    """
    Optimized autofocus with local parabolic interpolation around peak.
    Base class providing local fit logic.
    """
    
    def __init__(self, config: AutofocusConfig):
        """Initialize parabolic autofocus."""
        super().__init__(config)
        self._interpolated_peak: float | None = None
    
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
        
        # Coarse scan complete → try local parabolic fit
        if not self._best_measurement:
             return AutofocusResult(finished=True, phase=Phase.FINISHED, best_position_mm=self.config.start_mm, best_score=0.0)
        
        # Attempt local parabolic fit (best + neighbors only)
        local_fit = self._fit_local_parabola()
        
        if local_fit:
            predicted_peak_pos, predicted_peak_score = local_fit
            self._best_measurement = _Measurement(predicted_peak_pos, predicted_peak_score)
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


class GoldenSectionAutofocus(MSPRAutofocus):
    """
    Robust autofocus using Golden Section Search for refinement.
    Reduces the search interval by factor 0.618 in each step.
    Guaranteed to find the maximum in a unimodal interval.
    """
    
    def __init__(self, config: AutofocusConfig):
        super().__init__(config)
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0
    
    def _prepare_refinement(self):
        if not self._best_measurement: return
        
        center = self._best_measurement.position_mm
        
        # Initial Refinement: Define Bracket around the peak
        if self._refinement_level == 0:
            # Take +/- step_size * 2 as initial bracket
            bracket_width = self.config.step_mm * 2.0
            self.a = max(self.config.start_mm, center - bracket_width)
            self.b = min(self.config.end_mm, center + bracket_width)
            
            # Two inner probe points using Golden Ratio
            self.c = self.b - (self.b - self.a) / GOLDEN_RATIO
            self.d = self.a + (self.b - self.a) / GOLDEN_RATIO
            
            self._refinement_positions = sorted([self.c, self.d])
            
        else:
            # Shrink by golden ratio complement (≈0.618)
            self._current_range_mm *= PHI_COMPLEMENT
            
            # Probe points at ≈0.382 from center
            p1 = center - self._current_range_mm * PHI_SMALL
            p2 = center + self._current_range_mm * PHI_SMALL
            
            self._refinement_positions = sorted([p1, p2])
        
        # Termination check handled by step size
        if len(self._refinement_positions) > 1:
            self._current_step_mm = self._refinement_positions[1] - self._refinement_positions[0]
        else:
            self._current_step_mm = 0.0
        
        self._refinement_index = 0
        self._refinement_level += 1


class IterativeParabolicAutofocus(ParabolicAutofocus):
    """
    Advanced Parabolic AF.
    Fits a parabola, moves to peak, measures, and FITS AGAIN.
    This corrects errors if the initial sampling was far off-center.
    """
    def __init__(self, config: AutofocusConfig):
        super().__init__(config)
        self.iteration_count = 0
        self.max_iterations = 2 # Usually 2 is enough for perfect focus

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

        # RE-FIT with the new data included
        local_fit = self._fit_local_parabola() 
        
        next_pos = self._best_measurement.position_mm
        
        if local_fit:
            pred_x, pred_y = local_fit
            next_pos = pred_x
            # Shrink range for safety check
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


class HillClimbingAutofocus(MSPRAutofocus):
    """
        Advanced Hill Climbing.
        1. Fast Search: Large steps until significant drop detected.
        2. Recursive Refinement: Jump back, shrink step, re-scan peak.
             Repeat until min_step is reached.
    """
    def __init__(self, config: AutofocusConfig):
        super().__init__(config)
        
        # Override start parameters
        self.current_pos = config.start_mm
        self.step = config.step_mm * 2.0 # Start fast!
        self.direction = 1 # 1 = forward, -1 = backward
        self.bad_steps = 0
        self.min_step = config.min_step_mm

        # Drop detection settings
        self.drop_threshold = 0.85
        self.refine_drop_threshold = 0.95
        self.drop_steps = 0
        self._refine_start_pos = 0.0

        # Blind zone: force forward motion to avoid early aborts
        total_range = config.end_mm - config.start_mm
        self.blind_zone_end = config.start_mm + (total_range * 0.3)
        
        # State
        self.phase_state = "SCANNING" # SCANNING, REVERSING, REFINING, FINISHED

    def start(self) -> float:
        self._phase = Phase.COARSE_SCAN # Reuse enum for compatibility
        return self.current_pos

    def process_image(self, position_mm: float, image: np.ndarray) -> AutofocusResult:
        score = self._calculate_score(image)
        if score <= 0 and self._measurements:
            score = self._measurements[-1].score
        self._measurements.append(_Measurement(position_mm, score))
        
        if self._best_measurement is None or score > self._best_measurement.score:
            self._best_measurement = _Measurement(position_mm, score)

        # --- Logic ---
        next_pos = position_mm
        finished = False

        if self.phase_state == "SCANNING":
            if position_mm < self.blind_zone_end:
                next_pos = position_mm + (self.step * self.direction)
            else:
                if self._best_measurement is not None and score < (self._best_measurement.score * self.drop_threshold):
                    self._start_refinement_cycle()
                    next_pos = self._calculate_refine_start()
                else:
                    # Keep going (Momentum)
                    next_pos = position_mm + (self.step * self.direction)
        
        elif self.phase_state == "REFINING":
            if self._best_measurement is not None and score < (self._best_measurement.score * self.refine_drop_threshold):
                if self.step <= self.min_step:
                    finished = True
                else:
                    self.step = max(self.step * 0.5, self.min_step)
                    next_pos = self._best_measurement.position_mm - (self.step * 3)
            else:
                # Continue in same direction
                next_pos = position_mm + self.step
                if self._best_measurement is not None:
                    dist = abs(next_pos - self._best_measurement.position_mm)
                    if dist > (self.step * 10):
                        if self.step <= self.min_step:
                            finished = True
                        else:
                            self._start_refinement_cycle()
                            next_pos = self._calculate_refine_start()

        # Boundary Checks
        if next_pos > self.config.end_mm or next_pos < self.config.start_mm:
            if self.step <= self.min_step:
                finished = True
            else:
                self._start_refinement_cycle()
                next_pos = self._calculate_refine_start()

        return AutofocusResult(
            finished=finished,
            next_position_mm=next_pos,
            best_position_mm=self._best_measurement.position_mm if self._best_measurement else 0.0,
            best_score=self._best_measurement.score if self._best_measurement else 0.0,
            phase=Phase.FINISHED if finished else (Phase.COARSE_SCAN if self.phase_state == "SCANNING" else Phase.REFINEMENT),
            progress=0.5,
            current_score=score
        )

    def _start_refinement_cycle(self) -> None:
        """Prepares the next finer pass."""
        self.phase_state = "REFINING"
        self.step = max(self.step * 0.4, self.min_step)
        self.bad_steps = 0
        self.drop_steps = 0

    def _calculate_refine_start(self) -> float:
        """Calculates a start position slightly before the peak."""
        if self._best_measurement is None:
            return self.current_pos
        self._refine_start_pos = self._best_measurement.position_mm - (self.step * 4.0)
        return self._refine_start_pos


class ThreeStageAutofocus(MSPRAutofocus):
    """
    3-Stage Autofocus for 10µm Precision without Backlash.

    Progression:
    1. Coarse (0.4 mm) -> Scans full range. Finds the "Hill".
    2. Fine   (0.1 mm) -> Scans +/- 0.6 mm. Finds the "Peak".
    3. Ultra  (0.01 mm)-> Scans +/- 0.15 mm. Finds the "Summit".

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

    def start(self) -> float:
        self._phase = Phase.COARSE_SCAN

        self.scan_points = list(np.arange(
            self.config.start_mm,
            self.config.end_mm + 0.001,
            self.step_coarse
        ))
        self.scan_points = self._clamp_positions(self.scan_points)
        self.scan_index = 0
        self.stage = "COARSE"

        return self.scan_points[0] if self.scan_points else float(self.config.start_mm)

    def process_image(self, position_mm: float, image: np.ndarray) -> AutofocusResult:
        score = self._calculate_score(image)
        if score <= 0 and self._measurements:
            score = self._measurements[-1].score
        self._measurements.append(_Measurement(position_mm, score))

        if self._best_measurement is None or score > self._best_measurement.score:
            self._best_measurement = _Measurement(position_mm, score)
            self.drop_counter = 0
        else:
            if self.stage == "ULTRA":
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
                if self.scan_points:
                    next_pos = self.scan_points[0]
                else:
                    finished = True

        elif self.stage == "ULTRA":
            if self.drop_counter >= 5:
                finished = True
            else:
                self.scan_index += 1
                if self.scan_index < len(self.scan_points):
                    next_pos = self.scan_points[self.scan_index]
                else:
                    finished = True

        return AutofocusResult(
            finished=finished,
            next_position_mm=next_pos,
            best_position_mm=self._best_measurement.position_mm if self._best_measurement else 0.0,
            best_score=self._best_measurement.score if self._best_measurement else 0.0,
            phase=Phase.FINISHED if finished else self._phase,
            progress=self._get_progress(),
            current_score=score
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

        self.scan_points = list(np.arange(start, end + 0.00001, step_size))
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
        # Generate ALL positions with minimum step size
        self._coarse_positions = list(np.arange(
            self.config.start_mm,
            self.config.end_mm + self._scan_step / 2,
            self._scan_step
        ))
        
        # Clamp to valid range
        self._coarse_positions = [
            max(self.config.start_mm, min(self.config.end_mm, pos))
            for pos in self._coarse_positions
        ]
        
        # Remove duplicates
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
        self._coarse_index += 1
        
        total = len(self._coarse_positions)
        progress = self._coarse_index / total
        
        # Continue scanning?
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
        
        # Scan complete - return best position directly (no refinement needed)
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
        self._state = "INIT"  # INIT, PROBE_C, PROBE_D, SHRINK
    
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
            # Initial bracket: ± 2 * step_mm around peak
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
        current_pos = self._measurements[-1].position_mm
        
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
            # Converged - return best position
            best_pos = self._c if self._fc > self._fd else self._d
            best_score = max(self._fc, self._fd)
            
            self._phase = Phase.FINISHED
            return AutofocusResult(
                finished=True,
                best_position_mm=best_pos,
                best_score=best_score,
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


# Aliases for convenience
Autofocus = MSPRAutofocus
AdaptiveHillClimbingAutofocus = HillClimbingAutofocus
BruteForceAutofocus = ExhaustiveAutofocus  # Alternative name
