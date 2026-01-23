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


def tenengrad(image: np.ndarray) -> float:
    """
    Calculate Tenengrad sharpness metric (gradient-based).
    
    Args:
        image: Input image (BGR or grayscale)
        
    Returns:
        Sharpness score (higher = sharper)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Sobel gradients
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    
    # Gradient magnitude squared
    gradient_magnitude = gx**2 + gy**2
    
    return float(np.sum(gradient_magnitude))


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


class Autofocus:
    """
    Simple autofocus with multi-level refinement.
    
    Algorithm:
    1. Coarse Scan: Linear scan from start to end with step_mm
    2. Find coarse maximum
    3. Refinement Loop:
       - Reduce search range around maximum
       - Sample ~refinement_samples points in new range
       - Find new maximum
       - Repeat until step size < min_step_mm
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
        self._coarse_positions = [
            max(self.config.start_mm, min(self.config.end_mm, pos))
            for pos in self._coarse_positions
        ]
        
        # Remove duplicates that may occur from clamping
        seen = set()
        unique_positions = []
        for pos in self._coarse_positions:
            if pos not in seen:
                seen.add(pos)
                unique_positions.append(pos)
        self._coarse_positions = unique_positions
        
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
            return AutofocusResult(
                finished=True,
                best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
                best_score=self._best_measurement.score if self._best_measurement else 0.0,
                phase=Phase.FINISHED
            )

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
    
    def _handle_coarse_scan(self) -> AutofocusResult:
        """Handle coarse scan phase."""
        self._coarse_index += 1
        
        # Check for early exit (Peak crossed)
        current_score = self._measurements[-1].score
        best_score = self._best_measurement.score if self._best_measurement else 0.0

        if not self.config.disable_coarse_early_termination and best_score > 0 and self._coarse_index > 3:  # Ensure we have some data
            if current_score < best_score * self.config.coarse_terminate_threshold:
                self._coarse_drop_counter += 1
            else:
                self._coarse_drop_counter = 0

            if self._coarse_drop_counter >= self.config.coarse_terminate_count:
                # We crossed the peak! Abort coarse scan and start refinement
                # Prepare refinement but don't change phase yet
                self._prepare_refinement()
                
                # Return result showing this was a COARSE_SCAN measurement
                result = AutofocusResult(
                    finished=False,
                    next_position_mm=self._refinement_positions[0],
                    best_position_mm=self._best_measurement.position_mm,
                    best_score=self._best_measurement.score,
                    current_score=current_score,
                    phase=Phase.COARSE_SCAN,  # This result is for last coarse scan point
                    progress=0.5,
                    current_level=self._refinement_level,  # Show upcoming level
                    current_step_mm=self._current_step_mm,
                    current_range_mm=self._current_range_mm
                )
                
                # Now transition to refinement for next iteration
                self._phase = Phase.REFINEMENT
                return result

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
        
        # Coarse scan complete → start refinement
        if not self._best_measurement:
            # No measurements? Should not happen
            return AutofocusResult(
                finished=True,
                phase=Phase.FINISHED,
                best_position_mm=self.config.start_mm,
                best_score=0.0
            )
        
        # Prepare refinement but don't change phase yet
        self._prepare_refinement()
        
        # Refinement positions are already sorted ascending (unidirectional scan)
        # Always start at the beginning for consistent forward motion
        result = AutofocusResult(
            finished=False,
            next_position_mm=self._refinement_positions[0],
            best_position_mm=self._best_measurement.position_mm,
            best_score=self._best_measurement.score,
            current_score=self._measurements[-1].score,
            phase=Phase.COARSE_SCAN,  # This result is for last coarse scan point
            progress=0.5,  # Coarse done, refinement starting
            current_level=self._refinement_level,  # Show upcoming level
            current_step_mm=self._current_step_mm,
            current_range_mm=self._current_range_mm
        )
        
        # Now transition to refinement for next iteration
        self._phase = Phase.REFINEMENT
        return result
    
    def _handle_refinement(self) -> AutofocusResult:
        """
        Handle refinement phase with early termination.
        
        Early termination saves time by skipping remaining measurements when
        we're clearly past the peak. Asymmetric range focuses next level on
        the side where the peak is located.
        """
        current_score = self._measurements[-1].score
        best_score = self._best_measurement.score if self._best_measurement else 0.0
        
        # Check for early termination
        if best_score > 0:
            threshold = best_score * self.config.early_termination_threshold
            if current_score < threshold:
                self._low_score_counter += 1
            else:
                self._low_score_counter = 0  # Reset if we get a good score
            
            # Early termination triggered?
            if self._low_score_counter >= self.config.early_termination_count:
                # Skip remaining positions, go to next refinement level
                self._low_score_counter = 0
                
                # NOTE: Do NOT use asymmetric range after early termination
                # We've already found the best position in this level,
                # so the next level should be centered around it symmetrically
                # The asymmetric logic is only useful during active scanning
                
                # Check if we need another level
                if self._current_step_mm <= self.config.min_step_mm:
                    # Refinement complete
                    self._phase = Phase.FINISHED
                    return AutofocusResult(
                        finished=True,
                        best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
                        best_score=self._best_measurement.score if self._best_measurement else 0.0,
                        current_score=current_score,
                        phase=Phase.FINISHED,
                        progress=1.0,
                        current_level=self._refinement_level,
                        current_step_mm=self._current_step_mm,
                        current_range_mm=self._current_range_mm
                    )
                
                # Start next refinement level (centered on current best)
                self._prepare_refinement()
                
                return AutofocusResult(
                    finished=False,
                    next_position_mm=self._refinement_positions[0],
                    best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
                    best_score=self._best_measurement.score if self._best_measurement else 0.0,
                    current_score=current_score,
                    phase=Phase.REFINEMENT,
                    progress=0.6 + 0.1 * self._refinement_level,
                    current_level=self._refinement_level,
                    current_step_mm=self._current_step_mm,
                    current_range_mm=self._current_range_mm
                )
        
        self._refinement_index += 1
        
        # Continue current refinement level?
        if self._refinement_index < len(self._refinement_positions):
            return AutofocusResult(
                finished=False,
                next_position_mm=self._refinement_positions[self._refinement_index],
                best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
                best_score=self._best_measurement.score if self._best_measurement else 0.0,
                current_score=self._measurements[-1].score,
                phase=Phase.REFINEMENT,
                progress=0.5 + 0.5 * (self._refinement_index / len(self._refinement_positions)),
                current_level=self._refinement_level,
                current_step_mm=self._current_step_mm,
                current_range_mm=self._current_range_mm
            )
        
        # Current level complete → check if we need another level
        if self._current_step_mm <= self.config.min_step_mm:
            # Refinement complete
            self._phase = Phase.FINISHED
            return AutofocusResult(
                finished=True,
                best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
                best_score=self._best_measurement.score if self._best_measurement else 0.0,
                current_score=self._measurements[-1].score,
                phase=Phase.FINISHED,
                progress=1.0,
                current_level=self._refinement_level,
                current_step_mm=self._current_step_mm,
                current_range_mm=self._current_range_mm
            )
        
        # Start next refinement level
        self._prepare_refinement()
        
        return AutofocusResult(
            finished=False,
            next_position_mm=self._refinement_positions[0],
            best_position_mm=self._best_measurement.position_mm if self._best_measurement else None,
            best_score=self._best_measurement.score if self._best_measurement else 0.0,
            current_score=self._measurements[-1].score,
            phase=Phase.REFINEMENT,
            progress=0.6 + 0.1 * self._refinement_level,  # Rough estimate
            current_level=self._refinement_level,
            current_step_mm=self._current_step_mm,
            current_range_mm=self._current_range_mm
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
        self._refinement_positions = list(np.arange(
            range_start,
            range_end + self._current_step_mm / 2,
            self._current_step_mm
        ))
        
        # Clamp all positions to valid range [start_mm, end_mm]
        self._refinement_positions = [
            max(self.config.start_mm, min(self.config.end_mm, pos))
            for pos in self._refinement_positions
        ]
        
        # Remove duplicates that may occur from clamping
        seen = set()
        unique_positions = []
        for pos in self._refinement_positions:
            if pos not in seen:
                seen.add(pos)
                unique_positions.append(pos)
        self._refinement_positions = unique_positions
        
        # Ensure positions are sorted ascending
        self._refinement_positions.sort()
        
        # **FIX: Start one step BEFORE the peak for unidirectional scanning**
        # Find position of current best in the list
        # Start scanning from one step before it (approaching from below)
        best_in_list = min(self._refinement_positions, key=lambda p: abs(p - center))
        best_idx = self._refinement_positions.index(best_in_list)
        
        if best_idx > 0:
            # Move list so we start one step before the peak
            # Example: [274.5, 274.6, ..., 276.9, 277.0, 277.1, ...]
            #          Start at 276.9 (one step before 277.0) instead of 274.5
            self._refinement_positions = self._refinement_positions[best_idx - 1:]
        # else: peak is at start of range, just scan from beginning
        
        self._refinement_level += 1


class ParabolicAutofocus(Autofocus):
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


class GoldenSectionAutofocus(Autofocus):
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
        
        # Golden Ratio
        PHI = (1 + 5**0.5) / 2
        
        center = self._best_measurement.position_mm
        
        # Initial Refinement: Define Bracket around the peak
        # We take the neighbor points from the coarse scan as bounds
        if self._refinement_level == 0:
            # Safer: just take +/- step_size * 2 as initial bracket
            bracket_width = self.config.step_mm * 2.0
            self.a = max(self.config.start_mm, center - bracket_width)
            self.b = min(self.config.end_mm, center + bracket_width)
            
            # Two inner probe points
            self.c = self.b - (self.b - self.a) / PHI
            self.d = self.a + (self.b - self.a) / PHI
            
            # We need to measure c and d next.
            self._refinement_positions = sorted([self.c, self.d])
            
        else:
            # Simple contraction for multi-level logic (simulated Golden Section)
            # Use standard Autofocus shrinkage but adapted for Golden Ratio
            self._current_range_mm *= 0.618 # Shrink by golden ratio
            
            p1 = center - self._current_range_mm * 0.382 # 1 - 1/phi
            p2 = center + self._current_range_mm * 0.382
            
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
            current_score=score
        )


class HillClimbingAutofocus(Autofocus):
    """
    Hill Climbing with Momentum and Adaptive Step Size.
    - Start with large steps.
    - If score improves: Keep direction, maybe accelerate.
    - If score drops: Don't turn back immediately (Momentum)! Check 1-2 more steps.
      If it's a real drop, reverse and decrease step size.
    """
    def __init__(self, config: AutofocusConfig):
        super().__init__(config)
        
        # Override start parameters
        self.current_pos = config.start_mm
        self.step = config.step_mm * 2.0 # Start fast!
        self.direction = 1 # 1 = forward, -1 = backward
        self.patience = 2 # How many bad steps allowed before turning back
        self.bad_steps = 0
        self.min_step = config.min_step_mm
        
        # State
        self.phase_state = "SCANNING" # SCANNING, REVERSING, FINISHED

    def start(self) -> float:
        self._phase = Phase.COARSE_SCAN # Reuse enum for compatibility
        return self.current_pos

    def process_image(self, position_mm: float, image: np.ndarray) -> AutofocusResult:
        score = self._calculate_score(image)
        self._measurements.append(_Measurement(position_mm, score))
        
        if self._best_measurement is None or score > self._best_measurement.score:
            self._best_measurement = _Measurement(position_mm, score)
            # Reset bad steps if we found a new high
            self.bad_steps = 0
        else:
            # Score dropped
            self.bad_steps += 1

        # --- Logic ---
        next_pos = position_mm
        finished = False

        if self.phase_state == "SCANNING":
            if self.bad_steps < self.patience:
                # Keep going (Momentum), maybe we bridge a gap
                next_pos = position_mm + (self.step * self.direction)
            else:
                # Patience exhausted. It's a real drop.
                # Go back to best known position and refine
                self.phase_state = "REVERSING"
                next_pos = self._best_measurement.position_mm
                
                # Make step smaller and reverse direction logic
                self.step *= 0.4 # Significant reduction
                self.bad_steps = 0
                
        elif self.phase_state == "REVERSING":
            # We jumped back to peak. Now scan fine grid around it.
            if self.step < self.min_step:
                finished = True
            else:
                # Switch back to scanning with smaller step
                self.phase_state = "SCANNING" 
                # Try small step forward first (or alternate? simple forward for now)
                next_pos = self._best_measurement.position_mm + self.step
                self.patience = 1 # Be stricter with small steps

        # Boundary Checks
        if next_pos > self.config.end_mm or next_pos < self.config.start_mm:
            # Hit wall. Force reverse or finish.
            if self.step < self.min_step:
                finished = True
            else:
                self.phase_state = "REVERSING"
                next_pos = self._best_measurement.position_mm
                self.step *= 0.5
                self.bad_steps = 100 # Force logic update next cycle

        return AutofocusResult(
            finished=finished,
            next_position_mm=next_pos,
            best_position_mm=self._best_measurement.position_mm,
            best_score=self._best_measurement.score,
            phase=Phase.FINISHED if finished else Phase.COARSE_SCAN,
            progress=0.5,
            current_score=score
        )


# Alias
AdaptiveHillClimbingAutofocus = HillClimbingAutofocus
