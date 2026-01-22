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
        score = tenengrad(image)
        
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
        
        self._refinement_index = 0
        self._refinement_level += 1


class ParabolicAutofocus(Autofocus):
    """
    Optimized autofocus with local parabolic interpolation around peak.
    
    Improvements over basic Autofocus:
    1. Local Parabolic Fit: Fits parabola only through best point and its immediate neighbors
       - Ignores flat regions far from peak
       - More robust and accurate than global fit
    2. Smart Refinement Range: Uses much tighter range around predicted peak
    3. Faster Convergence: Dramatically reduces total measurement count
    
    This approach focuses computational effort on the actual peak region,
    ignoring the "tails" of the focus curve that don't contribute useful information.
    """
    
    def __init__(self, config: AutofocusConfig):
        """Initialize parabolic autofocus."""
        super().__init__(config)
        self._interpolated_peak: float | None = None
    
    def _fit_local_parabola(self) -> tuple[float, float] | None:
        """
        Fit parabola through best coarse point and its immediate neighbors.
        
        Uses only 3 points: best_point, left_neighbor, right_neighbor.
        This is the gold standard for focus peak fitting - it captures
        the peak shape while ignoring distant flat regions.
        
        Returns:
            (position_mm, estimated_score) of parabolic peak, or None if fit fails
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
        
        After coarse scan completes, fits a parabola through the 3 best points
        to estimate the true peak location, then starts a tight refinement there.
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
            # No measurements? Should not happen
            return AutofocusResult(
                finished=True,
                phase=Phase.FINISHED,
                best_position_mm=self.config.start_mm,
                best_score=0.0
            )
        
        # Attempt local parabolic fit (best + neighbors only)
        local_fit = self._fit_local_parabola()
        
        if local_fit:
            predicted_peak_pos, predicted_peak_score = local_fit
            
            # Update best measurement to predicted peak
            self._best_measurement = _Measurement(predicted_peak_pos, predicted_peak_score)
            self._interpolated_peak = predicted_peak_pos
            
            # OPTIMIZATION: Use very tight refinement range
            # Since the parabolic fit is already quite accurate,
            # we only need a small range to verify and refine
            # Override the range to be just ±2 coarse steps
            self._current_range_mm = self.config.step_mm * 2.0
        
        # Start refinement (centered on predicted or measured best)
        # Prepare refinement but don't change phase yet
        self._prepare_refinement()
        
        # Refinement positions are sorted, start at beginning
        result = AutofocusResult(
            finished=False,
            next_position_mm=self._refinement_positions[0],
            best_position_mm=self._best_measurement.position_mm,
            best_score=self._best_measurement.score,
            current_score=self._measurements[-1].score,
            phase=Phase.COARSE_SCAN,  # This result is for last coarse scan point
            progress=0.5,
            current_level=self._refinement_level,  # Show upcoming level
            current_step_mm=self._current_step_mm,
            current_range_mm=self._current_range_mm
        )
        
        # Now transition to refinement for next iteration
        self._phase = Phase.REFINEMENT
        return result
    
    def _handle_refinement(self) -> AutofocusResult:
        """
        Handle refinement - just use parent implementation since we already
        jumped to the predicted peak location after coarse scan.
        """
        return super()._handle_refinement()


@dataclass
class _Measurement:
    """Internal measurement data point."""
    position_mm: float
    score: float

class HillClimbingAutofocus(Autofocus):
    """
    Simple Hill Climbing Strategy:
    - Scan until we reach a HIGH peak (>threshold Tenengrad) and then it drops
    - Ignores small local maxima (< threshold)
    - Then do fine scan around best position found
    """
    
    def __init__(self, config: AutofocusConfig, estimated_peak_millions: float = 100.0):
        """
        Initialize HillClimbing autofocus.
        
        Args:
            config: Autofocus configuration
            estimated_peak_millions: Expected peak value in millions (e.g., 80.0 for 80M Tenengrad).
                                     Used to determine threshold for "real" peak detection.
                                     Default: 100.0 (100M)
        """
        super().__init__(config)
        
        # Coarse scan settings
        self.step_size = config.step_mm if config.step_mm > 0 else 0.5
        
        # Peak detection: Only stop at significant peaks
        # Set threshold to 80% of estimated peak (to catch it reliably even if estimate is slightly off)
        if estimated_peak_millions > 0:
            self.peak_threshold = estimated_peak_millions * 1_000_000 * 0.8
        else:
            self.peak_threshold = 100_000_000  # Default: 100M
            
        self.required_drops = 3  # Stop after 3 consecutive drops from a real peak
        self.drop_counter = 0
        self.reached_real_peak = False  # Flag: did we reach a score > threshold?
        
        # Track global maximum
        self.global_max_score = 0.0
        self.global_max_position = 0.0
        
        # Generate adaptive multi-level refinement based on coarse step size
        self.refinement_levels = self._generate_refinement_levels(self.step_size)
        self.current_refinement_level = 0
        
        # State
        self._current_pos = config.start_mm
        self._sweep_points = []
        self._sweep_index = 0
    
    def _generate_refinement_levels(self, coarse_step: float) -> list[dict]:
        """
        Generate refinement levels based on coarse scan step size.
        
        Logic: Start with step ~4x smaller than coarse, then progressively refine.
        Each level reduces step size by ~4-5x and range by ~2x.
        Skip intermediate steps below 0.025mm - jump directly to min_step (0.01mm).
        
        Args:
            coarse_step: Step size used in coarse scan (e.g., 4.0mm)
            
        Returns:
            List of refinement level dicts with 'step' and 'range'
        """
        min_step = self.config.min_step_mm if self.config.min_step_mm > 0 else 0.01
        threshold = 0.025  # Skip intermediate steps below this threshold
        
        levels = []
        current_step = coarse_step / 4.0  # Start with 1/4 of coarse step
        current_range = coarse_step * 1.5  # Range ~1.5x coarse step
        
        # Generate levels until we reach minimum step
        while current_step >= min_step:
            # Skip intermediate steps between threshold and min_step
            # Jump directly from >0.025mm to 0.01mm to save time
            if current_step < threshold and current_step > min_step:
                current_step = min_step
                current_range = min_step * 20  # 0.01mm step → 0.2mm range
            
            levels.append({
                'step': round(current_step, 4),
                'range': round(current_range, 4)
            })
            
            # If we just added min_step level, we're done
            if current_step == min_step:
                break
            
            # Next level: reduce step by 4x (or 5x), range by 2x
            current_step /= 4.0 if current_step > 0.1 else 5.0
            current_range /= 2.0
            
            # Safety: max 5 levels
            if len(levels) >= 5:
                break
        
        # Ensure at least one level with minimum step
        if not levels or levels[-1]['step'] > min_step:
            levels.append({
                'step': min_step,
                'range': min_step * 20  # 0.01mm step → 0.2mm range
            })
        
        return levels

    def _handle_coarse_scan(self) -> AutofocusResult:
        """Coarse scan: ignore small peaks, only stop at real peak (>100M)."""
        
        # 1. Initialization - first call
        if not self._measurements:
            self._current_pos = self.config.start_mm
            self._phase = Phase.COARSE_SCAN
            self.global_max_score = 0.0
            self.drop_counter = 0
            self.reached_real_peak = False
            return AutofocusResult(
                finished=False,
                next_position_mm=self._current_pos,
                phase=Phase.COARSE_SCAN,
                current_score=0.0
            )
        
        current_score = self._measurements[-1].score
        
        # 2. Update global maximum (track best position across entire scan)
        if current_score > self.global_max_score:
            self.global_max_score = current_score
            self.global_max_position = self._measurements[-1].position_mm
            self.drop_counter = 0  # Reset counter when we find new global max
            
            # Check if we reached a "real" peak (>100M)
            if current_score > self.peak_threshold:
                self.reached_real_peak = True
        else:
            # Score dropped
            # Only count drops if we already reached a real peak
            if self.reached_real_peak:
                self.drop_counter += 1
            # Otherwise ignore drops (we're just in a small local maximum)
        
        # 3. Check if we passed THE peak (only if we saw >100M and now dropping)
        if self.reached_real_peak and self.drop_counter >= self.required_drops:
            # We clearly passed the main peak! Start fine scan
            return self._start_fine_scan()
        
        # 4. Check if we reached end of range
        if self._current_pos >= self.config.end_mm:
            if self.global_max_score > 0:
                # Found something, do fine scan around best position
                return self._start_fine_scan()
            else:
                # Nothing found - just return best we have
                best = max(self._measurements, key=lambda m: m.score)
                return AutofocusResult(
                    finished=True,
                    best_position_mm=best.position_mm,
                    best_score=best.score,
                    phase=Phase.FINISHED,
                    progress=1.0
                )
        
        # 5. Continue coarse scan
        self._current_pos += self.step_size
        progress = 0.1 + 0.5 * (self._current_pos - self.config.start_mm) / (self.config.end_mm - self.config.start_mm)
        
        return AutofocusResult(
            finished=False,
            next_position_mm=self._current_pos,
            best_position_mm=self.global_max_position,
            best_score=self.global_max_score,
            current_score=current_score,
            phase=Phase.COARSE_SCAN,
            progress=min(progress, 0.6)
        )

    def _start_fine_scan(self) -> AutofocusResult:
        """Start first level of fine scan around detected peak."""
        self.current_refinement_level = 0
        
        # Use first refinement level
        level = self.refinement_levels[0]
        
        # Define fine scan range around global maximum
        start = max(self.config.start_mm, self.global_max_position - (level['range'] / 2))
        end = min(self.config.end_mm, self.global_max_position + (level['range'] / 2))
        
        # Generate sweep points
        self._sweep_points = list(np.arange(start, end + level['step']/2, level['step']))
        if not self._sweep_points:
            self._sweep_points = [self.global_max_position]
        
        self._sweep_index = 0
        
        # IMPORTANT: Set phase AFTER preparing the result for current measurement
        # The result should show COARSE_SCAN for the last coarse measurement,
        # then phase will be REFINEMENT for the next process_image() call
        current_score = self._measurements[-1].score if self._measurements else 0.0
        
        result = AutofocusResult(
            finished=False,
            next_position_mm=self._sweep_points[0],
            phase=Phase.COARSE_SCAN,  # This result is for the last coarse scan point
            progress=0.6,
            current_range_mm=level['range'],
            best_score=self.global_max_score,
            best_position_mm=self.global_max_position,
            current_score=current_score,
            current_step_mm=level['step'],
            current_level=self.current_refinement_level + 1  # Show upcoming level
        )
        
        # Now transition to refinement phase for next iteration
        self._phase = Phase.REFINEMENT
        
        return result
    
    def _handle_refinement(self) -> AutofocusResult:
        """Handle fine scan with multiple refinement levels."""
        
        # Check if we have more points in current level
        if self._sweep_index + 1 < len(self._sweep_points):
            self._sweep_index += 1
            
            # Get current best across all measurements
            current_best = max(self._measurements, key=lambda m: m.score)
            
            progress = 0.6 + 0.4 * (self.current_refinement_level / len(self.refinement_levels)) + \
                      0.4 * (self._sweep_index / len(self._sweep_points)) / len(self.refinement_levels)
            
            level = self.refinement_levels[self.current_refinement_level]
            
            return AutofocusResult(
                finished=False,
                next_position_mm=self._sweep_points[self._sweep_index],
                phase=Phase.REFINEMENT,
                progress=min(progress, 0.99),
                best_score=current_best.score,
                best_position_mm=current_best.position_mm,
                current_score=self._measurements[-1].score,
                current_step_mm=level['step'],
                current_range_mm=level['range'],
                current_level=self.current_refinement_level + 1
            )
        
        # Current level complete - check if we have more levels
        self.current_refinement_level += 1
        
        if self.current_refinement_level < len(self.refinement_levels):
            # Start next refinement level around current best
            current_best = max(self._measurements, key=lambda m: m.score)
            level = self.refinement_levels[self.current_refinement_level]
            
            # Center next level around current best position
            start = max(self.config.start_mm, current_best.position_mm - (level['range'] / 2))
            end = min(self.config.end_mm, current_best.position_mm + (level['range'] / 2))
            
            self._sweep_points = list(np.arange(start, end + level['step']/2, level['step']))
            if not self._sweep_points:
                self._sweep_points = [current_best.position_mm]
            
            self._sweep_index = 0
            
            return AutofocusResult(
                finished=False,
                next_position_mm=self._sweep_points[0],
                phase=Phase.REFINEMENT,
                progress=0.6 + 0.4 * (self.current_refinement_level / len(self.refinement_levels)),
                best_score=current_best.score,
                best_position_mm=current_best.position_mm,
                current_score=self._measurements[-1].score,
                current_step_mm=level['step'],
                current_range_mm=level['range'],
                current_level=self.current_refinement_level + 1
            )
        
        # All levels complete - find absolute best
        final_best = max(self._measurements, key=lambda m: m.score)
        self._phase = Phase.FINISHED
        
        return AutofocusResult(
            finished=True,
            best_position_mm=final_best.position_mm,
            best_score=final_best.score,
            phase=Phase.FINISHED,
            progress=1.0
        )

    def _fit_local_parabola(self):
        """Parabola fitting (optional, currently not used)."""
        if len(self._measurements) < 3:
            return None
        
        scores = [m.score for m in self._measurements]
        best_idx = np.argmax(scores)
        
        if best_idx == 0 or best_idx == len(self._measurements) - 1:
            return None
        
        subset = self._measurements[best_idx - 1 : best_idx + 2]
        x = np.array([m.position_mm for m in subset])
        y = np.array([m.score for m in subset])
        
        try:
            coeffs = np.polyfit(x, y, 2)
            a, b, c = coeffs
            if a >= 0:
                return None
            peak_x = -b / (2 * a)
            peak_y = a * peak_x**2 + b * peak_x + c
            if abs(peak_x - self._measurements[best_idx].position_mm) > self.step_size * 1.5:
                return None
            return (float(peak_x), float(peak_y))
        except:
            return None
