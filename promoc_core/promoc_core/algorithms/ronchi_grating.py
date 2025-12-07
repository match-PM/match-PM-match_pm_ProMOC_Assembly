"""
Ronchi Grating (Line Grating) Analysis for MTF Measurement.

This module provides analysis of Ronchi grating (periodic line pattern) targets for:
- MTF measurement at specific spatial frequency
- Contrast measurement (Michelson contrast)
- Grating orientation detection
- Focus quality assessment

A Ronchi grating consists of alternating black and white lines of equal width.
The spatial frequency is determined by the line period (pitch).

Algorithm:
1. Detect grating orientation using FFT or Hough transform
2. Extract intensity profile perpendicular to lines
3. Compute Michelson contrast
4. Calculate MTF at the grating frequency

Usage:
    from promoc_core.algorithms.ronchi_grating import (
        RonchiAnalyzer, RonchiConfig, RonchiResult
    )
    
    config = RonchiConfig(
        grating_frequency_lpmm=50.0,  # Known grating frequency
        pixel_size_um=3.45
    )
    analyzer = RonchiAnalyzer(config)
    
    result = analyzer.analyze(image)
    print(f"MTF at {result.frequency_lpmm:.1f} lp/mm: {result.mtf:.3f}")
    print(f"Contrast: {result.contrast:.3f}")

References:
    - Ronchi, V. "Le Frange di Combinazione Nello Studio delle Superfici e dei Sistemi Ottici"
    - ISO 12233:2017 - Resolution and spatial frequency responses
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


class RonchiStatus(Enum):
    """Status of Ronchi grating analysis."""
    SUCCESS = "success"
    GRATING_NOT_FOUND = "grating_not_found"
    INSUFFICIENT_CONTRAST = "insufficient_contrast"
    INVALID_IMAGE = "invalid_image"
    FREQUENCY_MISMATCH = "frequency_mismatch"


@dataclass
class RonchiConfig:
    """
    Configuration for Ronchi grating analysis.

    Attributes:
        grating_frequency_lpmm: Known grating frequency in line pairs per mm.
            If None, frequency will be auto-detected from image.
        pixel_size_um: Camera pixel size in micrometers.
        roi_center: Center of ROI as (x, y). None = image center.
        roi_size: Size of ROI as (width, height). None = full image.
        min_contrast: Minimum contrast threshold for valid measurement.
        frequency_tolerance: Allowed deviation from expected frequency (ratio).
        num_periods_min: Minimum number of line periods required.
        orientation_auto: Auto-detect grating orientation.
        expected_orientation_deg: Expected orientation if not auto-detecting.
            0° = vertical lines, 90° = horizontal lines.
    """
    grating_frequency_lpmm: Optional[float] = None
    pixel_size_um: float = 3.45
    roi_center: Optional[Tuple[int, int]] = None
    roi_size: Optional[Tuple[int, int]] = None
    min_contrast: float = 0.05
    frequency_tolerance: float = 0.2
    num_periods_min: int = 5
    orientation_auto: bool = True
    expected_orientation_deg: float = 0.0

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.pixel_size_um <= 0:
            raise ValueError(
                f"pixel_size_um must be positive, got {self.pixel_size_um}")
        if self.grating_frequency_lpmm is not None and self.grating_frequency_lpmm <= 0:
            raise ValueError(
                f"grating_frequency_lpmm must be positive, got {self.grating_frequency_lpmm}")
        if self.min_contrast < 0 or self.min_contrast > 1:
            raise ValueError(
                f"min_contrast must be in [0, 1], got {self.min_contrast}")
        if self.frequency_tolerance <= 0:
            raise ValueError(
                f"frequency_tolerance must be positive, got {self.frequency_tolerance}")


@dataclass
class RonchiResult:
    """
    Result of Ronchi grating analysis.

    Attributes:
        status: Analysis status.
        message: Human-readable status message.
        mtf: MTF value at the grating frequency (0.0 - 1.0).
        contrast: Michelson contrast of the grating.
        frequency_lpmm: Measured/used grating frequency (lp/mm).
        frequency_detected_lpmm: Auto-detected frequency (lp/mm).
        orientation_deg: Detected grating orientation (degrees).
        period_px: Grating period in pixels.
        num_periods: Number of complete periods in ROI.
        intensity_max: Maximum intensity in profile.
        intensity_min: Minimum intensity in profile.
        profile: Extracted intensity profile perpendicular to lines.
        fft_magnitude: FFT magnitude spectrum of profile.
        fft_frequencies: Corresponding frequencies for FFT.
    """
    status: RonchiStatus
    message: str
    mtf: float = 0.0
    contrast: float = 0.0
    frequency_lpmm: float = 0.0
    frequency_detected_lpmm: float = 0.0
    orientation_deg: float = 0.0
    period_px: float = 0.0
    num_periods: float = 0.0
    intensity_max: float = 0.0
    intensity_min: float = 0.0
    profile: Optional[np.ndarray] = None
    fft_magnitude: Optional[np.ndarray] = None
    fft_frequencies: Optional[np.ndarray] = None


class RonchiAnalyzer:
    """
    Analyzer for Ronchi grating (line grating) targets.

    Measures MTF at the specific grating frequency and provides
    contrast measurements for focus assessment.

    The Ronchi grating has a known spatial frequency, making it ideal for:
    - Verifying MTF at a specific frequency
    - Quick focus optimization
    - Production quality control

    Example:
        >>> config = RonchiConfig(
        ...     grating_frequency_lpmm=100.0,
        ...     pixel_size_um=3.45
        ... )
        >>> analyzer = RonchiAnalyzer(config)
        >>> result = analyzer.analyze(image)
        >>> if result.status == RonchiStatus.SUCCESS:
        ...     print(f"MTF at {result.frequency_lpmm:.0f} lp/mm: {result.mtf:.3f}")
    """

    def __init__(self, config: Optional[RonchiConfig] = None):
        """
        Initialize Ronchi grating analyzer.

        Args:
            config: Analysis configuration. Uses defaults if None.

        Raises:
            ImportError: If OpenCV is not available.
        """
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required for Ronchi analysis")

        self.config = config or RonchiConfig()
        self.config.validate()

    def analyze(self, image: np.ndarray) -> RonchiResult:
        """
        Analyze Ronchi grating image.

        Args:
            image: Input image containing Ronchi grating.

        Returns:
            RonchiResult with MTF and contrast measurements.
        """
        # Validate input
        if image is None or image.size == 0:
            return RonchiResult(
                status=RonchiStatus.INVALID_IMAGE,
                message="Image is empty or None"
            )

        # Convert to grayscale
        gray = self._ensure_grayscale(image)

        # Extract ROI
        roi = self._extract_roi(gray)

        # Detect orientation
        if self.config.orientation_auto:
            orientation = self._detect_orientation(roi)
        else:
            orientation = self.config.expected_orientation_deg

        if orientation is None:
            return RonchiResult(
                status=RonchiStatus.GRATING_NOT_FOUND,
                message="Could not detect grating orientation"
            )

        # Rotate to make lines vertical (simplifies profile extraction)
        roi_rotated = self._rotate_image(roi, -orientation)

        # Extract intensity profile (horizontal, perpendicular to vertical lines)
        profile = self._extract_profile(roi_rotated)

        # Analyze profile with FFT
        fft_result = self._analyze_profile_fft(profile)
        if fft_result is None:
            return RonchiResult(
                status=RonchiStatus.GRATING_NOT_FOUND,
                message="Could not analyze grating profile",
                orientation_deg=orientation,
                profile=profile
            )

        detected_freq_px, fft_magnitude, fft_frequencies = fft_result

        # Convert to physical units
        pixel_size_mm = self.config.pixel_size_um / 1000.0
        detected_freq_lpmm = detected_freq_px / pixel_size_mm

        # Determine which frequency to use
        if self.config.grating_frequency_lpmm is not None:
            expected_freq_lpmm = self.config.grating_frequency_lpmm
            freq_ratio = detected_freq_lpmm / expected_freq_lpmm

            if abs(freq_ratio - 1.0) > self.config.frequency_tolerance:
                return RonchiResult(
                    status=RonchiStatus.FREQUENCY_MISMATCH,
                    message=f"Detected frequency {detected_freq_lpmm:.1f} lp/mm "
                    f"differs from expected {expected_freq_lpmm:.1f} lp/mm",
                    frequency_lpmm=expected_freq_lpmm,
                    frequency_detected_lpmm=detected_freq_lpmm,
                    orientation_deg=orientation,
                    profile=profile,
                    fft_magnitude=fft_magnitude,
                    fft_frequencies=fft_frequencies / pixel_size_mm
                )

            use_freq_lpmm = expected_freq_lpmm
        else:
            use_freq_lpmm = detected_freq_lpmm

        # Calculate period
        period_px = 1.0 / detected_freq_px if detected_freq_px > 0 else 0
        num_periods = len(profile) * detected_freq_px

        # Check minimum periods
        if num_periods < self.config.num_periods_min:
            return RonchiResult(
                status=RonchiStatus.GRATING_NOT_FOUND,
                message=f"Only {num_periods:.1f} periods found, "
                f"need at least {self.config.num_periods_min}",
                frequency_lpmm=use_freq_lpmm,
                frequency_detected_lpmm=detected_freq_lpmm,
                orientation_deg=orientation,
                period_px=period_px,
                num_periods=num_periods,
                profile=profile,
                fft_magnitude=fft_magnitude,
                fft_frequencies=fft_frequencies / pixel_size_mm
            )

        # Compute contrast
        contrast, i_max, i_min = self._compute_contrast(profile, period_px)

        # Check minimum contrast
        if contrast < self.config.min_contrast:
            return RonchiResult(
                status=RonchiStatus.INSUFFICIENT_CONTRAST,
                message=f"Contrast {contrast:.3f} below threshold {self.config.min_contrast}",
                contrast=contrast,
                frequency_lpmm=use_freq_lpmm,
                frequency_detected_lpmm=detected_freq_lpmm,
                orientation_deg=orientation,
                period_px=period_px,
                num_periods=num_periods,
                intensity_max=i_max,
                intensity_min=i_min,
                profile=profile,
                fft_magnitude=fft_magnitude,
                fft_frequencies=fft_frequencies / pixel_size_mm
            )

        # MTF = measured contrast / ideal contrast
        # For a perfect square wave grating, ideal contrast = 1.0
        # But we need to account for the fundamental frequency component
        # MTF ≈ (π/4) * contrast for square wave -> sine wave relationship
        # Or simply use contrast as MTF approximation for practical purposes
        mtf = contrast

        return RonchiResult(
            status=RonchiStatus.SUCCESS,
            message="Analysis completed successfully",
            mtf=mtf,
            contrast=contrast,
            frequency_lpmm=use_freq_lpmm,
            frequency_detected_lpmm=detected_freq_lpmm,
            orientation_deg=orientation,
            period_px=period_px,
            num_periods=num_periods,
            intensity_max=i_max,
            intensity_min=i_min,
            profile=profile,
            fft_magnitude=fft_magnitude,
            fft_frequencies=fft_frequencies / pixel_size_mm
        )

    def _ensure_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale float."""
        if len(image.shape) == 3:
            if image.shape[2] == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif image.shape[2] == 4:
                gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            else:
                gray = image[:, :, 0]
        else:
            gray = image

        return gray.astype(np.float64)

    def _extract_roi(self, gray: np.ndarray) -> np.ndarray:
        """Extract region of interest from image."""
        h, w = gray.shape

        if self.config.roi_size is None and self.config.roi_center is None:
            return gray

        # Determine ROI parameters
        if self.config.roi_size is not None:
            roi_w, roi_h = self.config.roi_size
        else:
            roi_w, roi_h = w, h

        if self.config.roi_center is not None:
            cx, cy = self.config.roi_center
        else:
            cx, cy = w // 2, h // 2

        # Calculate ROI bounds
        x1 = max(0, cx - roi_w // 2)
        y1 = max(0, cy - roi_h // 2)
        x2 = min(w, x1 + roi_w)
        y2 = min(h, y1 + roi_h)

        return gray[y1:y2, x1:x2]

    def _detect_orientation(self, gray: np.ndarray) -> Optional[float]:
        """
        Detect grating orientation using FFT.

        Returns:
            Orientation in degrees (0° = vertical lines, 90° = horizontal).
        """
        h, w = gray.shape

        # Compute 2D FFT
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)

        # Mask out DC component
        cy, cx = h // 2, w // 2
        mask_radius = 5
        y_grid, x_grid = np.ogrid[:h, :w]
        mask = (x_grid - cx)**2 + (y_grid - cy)**2 > mask_radius**2
        magnitude = magnitude * mask

        # Find peak in FFT (corresponds to grating frequency)
        # The peak angle indicates grating orientation
        max_idx = np.unravel_index(np.argmax(magnitude), magnitude.shape)
        peak_y, peak_x = max_idx

        # Calculate angle from center
        dy = peak_y - cy
        dx = peak_x - cx

        if abs(dx) < 1 and abs(dy) < 1:
            # No clear peak found
            return None

        # Angle perpendicular to the peak direction gives line orientation
        angle_rad = np.arctan2(dy, dx)
        orientation_deg = np.degrees(angle_rad) + 90  # Perpendicular

        # Normalize to 0-180 range
        orientation_deg = orientation_deg % 180

        return orientation_deg

    def _rotate_image(self, gray: np.ndarray, angle_deg: float) -> np.ndarray:
        """Rotate image to align grating lines vertically."""
        h, w = gray.shape
        center = (w / 2, h / 2)

        # Rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)

        # Calculate new image size to contain full rotated image
        cos_a = abs(rotation_matrix[0, 0])
        sin_a = abs(rotation_matrix[0, 1])
        new_w = int(h * sin_a + w * cos_a)
        new_h = int(h * cos_a + w * sin_a)

        # Adjust translation
        rotation_matrix[0, 2] += (new_w - w) / 2
        rotation_matrix[1, 2] += (new_h - h) / 2

        rotated = cv2.warpAffine(
            gray, rotation_matrix, (new_w, new_h),
            borderMode=cv2.BORDER_REFLECT
        )

        return rotated

    def _extract_profile(self, gray: np.ndarray) -> np.ndarray:
        """
        Extract intensity profile perpendicular to grating lines.

        For vertical lines, this is a horizontal profile (average over rows).
        """
        # Average along vertical axis (columns) to get horizontal profile
        # This averages multiple lines for better SNR
        profile = np.mean(gray, axis=0)

        return profile

    def _analyze_profile_fft(
        self, profile: np.ndarray
    ) -> Optional[Tuple[float, np.ndarray, np.ndarray]]:
        """
        Analyze intensity profile using FFT to find grating frequency.

        Returns:
            Tuple of (frequency_cycles_per_pixel, magnitude, frequencies)
            or None if analysis fails.
        """
        n = len(profile)
        if n < 16:
            return None

        # Remove DC component
        profile_centered = profile - np.mean(profile)

        # Apply window to reduce spectral leakage
        window = np.hanning(n)
        profile_windowed = profile_centered * window

        # Compute FFT
        fft = np.fft.rfft(profile_windowed)
        magnitude = np.abs(fft)
        frequencies = np.fft.rfftfreq(n)  # Cycles per pixel

        # Ignore DC and very low frequencies
        min_freq_idx = max(1, n // 50)

        # Find peak frequency
        peak_idx = min_freq_idx + np.argmax(magnitude[min_freq_idx:])

        if peak_idx >= len(frequencies):
            return None

        # Refine peak with parabolic interpolation
        if 1 <= peak_idx < len(magnitude) - 1:
            y0 = magnitude[peak_idx - 1]
            y1 = magnitude[peak_idx]
            y2 = magnitude[peak_idx + 1]

            if y1 > y0 and y1 > y2:
                # Parabolic interpolation
                delta = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
                refined_freq = frequencies[peak_idx] + delta * (
                    frequencies[1] - frequencies[0]
                )
            else:
                refined_freq = frequencies[peak_idx]
        else:
            refined_freq = frequencies[peak_idx]

        return (refined_freq, magnitude, frequencies)

    def _compute_contrast(
        self, profile: np.ndarray, period_px: float
    ) -> Tuple[float, float, float]:
        """
        Compute Michelson contrast of the grating.

        Uses peak detection to find accurate min/max values.

        Returns:
            Tuple of (contrast, max_intensity, min_intensity)
        """
        if period_px < 2:
            # Fallback to simple min/max
            i_max = float(np.max(profile))
            i_min = float(np.min(profile))
        else:
            # Use local extrema for more robust measurement
            half_period = int(period_px / 2)

            # Find local maxima and minima
            maxima = []
            minima = []

            for i in range(half_period, len(profile) - half_period):
                window = profile[i - half_period:i + half_period + 1]
                center_val = profile[i]

                if center_val == np.max(window):
                    maxima.append(center_val)
                elif center_val == np.min(window):
                    minima.append(center_val)

            if maxima and minima:
                # Use median to reject outliers
                i_max = float(np.median(maxima))
                i_min = float(np.median(minima))
            else:
                # Fallback
                i_max = float(np.max(profile))
                i_min = float(np.min(profile))

        # Michelson contrast
        if i_max + i_min > 0:
            contrast = (i_max - i_min) / (i_max + i_min)
        else:
            contrast = 0.0

        return (contrast, i_max, i_min)

    def compute_focus_score(self, image: np.ndarray) -> float:
        """
        Compute a focus score based on grating contrast.

        This is a simplified method for focus optimization.

        Args:
            image: Input image containing Ronchi grating.

        Returns:
            Focus score (0.0 - 1.0). Higher = better focus.
        """
        result = self.analyze(image)

        if result.status == RonchiStatus.SUCCESS:
            return result.contrast
        elif result.status == RonchiStatus.INSUFFICIENT_CONTRAST:
            return result.contrast
        else:
            return 0.0

    def get_expected_period_px(self) -> Optional[float]:
        """
        Get expected grating period in pixels based on config.

        Returns:
            Expected period in pixels, or None if frequency not specified.
        """
        if self.config.grating_frequency_lpmm is None:
            return None

        pixel_size_mm = self.config.pixel_size_um / 1000.0
        freq_cycles_per_px = self.config.grating_frequency_lpmm * pixel_size_mm

        if freq_cycles_per_px > 0:
            return 1.0 / freq_cycles_per_px
        return None


def compute_ronchi_mtf(
    image: np.ndarray,
    grating_frequency_lpmm: float,
    pixel_size_um: float = 3.45
) -> float:
    """
    Convenience function to compute MTF at a specific grating frequency.

    Args:
        image: Input image containing Ronchi grating.
        grating_frequency_lpmm: Known grating frequency (lp/mm).
        pixel_size_um: Camera pixel size (micrometers).

    Returns:
        MTF value (0.0 - 1.0), or 0.0 if analysis fails.

    Example:
        >>> mtf = compute_ronchi_mtf(image, 100.0, pixel_size_um=3.45)
        >>> print(f"MTF at 100 lp/mm: {mtf:.3f}")
    """
    config = RonchiConfig(
        grating_frequency_lpmm=grating_frequency_lpmm,
        pixel_size_um=pixel_size_um
    )
    analyzer = RonchiAnalyzer(config)
    result = analyzer.analyze(image)

    return result.mtf if result.status == RonchiStatus.SUCCESS else 0.0
