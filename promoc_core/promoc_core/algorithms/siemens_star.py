"""
Siemens Star (Spoke Target) Analysis for MTF and Astigmatism Measurement.

This module provides analysis of Siemens star (spoke) targets for:
- MTF measurement across all orientations
- Astigmatism detection (directional resolution differences)
- Limiting resolution determination

The Siemens star consists of radial spokes that converge at a center point.
As resolution decreases toward the center, spokes blur together at the
"limiting resolution radius". This radius directly indicates optical resolution.

Algorithm:
1. Detect star center using radial symmetry detection
2. Extract circular profiles at multiple radii
3. Analyze contrast vs. radius for each spoke direction
4. Compute MTF vs. spatial frequency
5. Detect astigmatism from directional differences

Usage:
    from promoc_core.algorithms.siemens_star import (
        SiemensStarAnalyzer, SiemensStarConfig, SiemensStarResult
    )
    
    config = SiemensStarConfig(
        num_spokes=36,
        pixel_size_um=3.45
    )
    analyzer = SiemensStarAnalyzer(config)
    
    result = analyzer.analyze(image)
    print(f"Limiting resolution: {result.limiting_resolution_lpmm:.1f} lp/mm")
    print(f"Astigmatism: {result.astigmatism_ratio:.2f}")

References:
    - ISO 12233:2017 - Resolution and spatial frequency responses
    - Burns, P.D. "Slanted-Edge MTF for Digital Camera and Scanner Analysis"
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from enum import Enum
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


class AnalysisStatus(Enum):
    """Status of Siemens star analysis."""
    SUCCESS = "success"
    CENTER_NOT_FOUND = "center_not_found"
    INSUFFICIENT_CONTRAST = "insufficient_contrast"
    INVALID_IMAGE = "invalid_image"
    SPOKE_DETECTION_FAILED = "spoke_detection_failed"


@dataclass
class SiemensStarConfig:
    """
    Configuration for Siemens star analysis.

    Attributes:
        num_spokes: Number of spoke pairs (black + white = 1 pair).
            Common values: 36, 72, 144. Must match physical target.
        pixel_size_um: Camera pixel size in micrometers.
        min_radius_px: Minimum radius for analysis (pixels).
            Should be > limiting resolution radius.
        max_radius_px: Maximum radius for analysis (pixels).
            None = use image size.
        num_radii: Number of radii to sample for MTF curve.
        angular_samples: Samples per full rotation for profile extraction.
        min_contrast: Minimum contrast threshold for valid measurement.
        center_search_radius: Search radius for center detection (pixels).
            None = auto-detect based on image size.
        blur_kernel_size: Gaussian blur kernel for noise reduction.
    """
    num_spokes: int = 36
    pixel_size_um: float = 3.45
    min_radius_px: int = 10
    max_radius_px: Optional[int] = None
    num_radii: int = 50
    angular_samples: int = 720
    min_contrast: float = 0.1
    center_search_radius: Optional[int] = None
    blur_kernel_size: int = 3

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.num_spokes < 4:
            raise ValueError(f"num_spokes must be >= 4, got {self.num_spokes}")
        if self.pixel_size_um <= 0:
            raise ValueError(
                f"pixel_size_um must be positive, got {self.pixel_size_um}")
        if self.min_radius_px < 1:
            raise ValueError(
                f"min_radius_px must be >= 1, got {self.min_radius_px}")
        if self.max_radius_px is not None and self.max_radius_px <= self.min_radius_px:
            raise ValueError(
                f"max_radius_px must be > min_radius_px")
        if self.num_radii < 5:
            raise ValueError(f"num_radii must be >= 5, got {self.num_radii}")
        if self.angular_samples < self.num_spokes * 4:
            raise ValueError(
                f"angular_samples must be >= 4 * num_spokes for proper sampling")


@dataclass
class DirectionalMTF:
    """
    MTF data for a specific direction (spoke orientation).

    Attributes:
        angle_deg: Angle of this direction in degrees (0-180).
        spatial_freq_lpmm: Array of spatial frequencies (lp/mm).
        mtf_values: Array of MTF values (0.0 - 1.0).
        mtf50_lpmm: Spatial frequency at MTF = 0.5.
        mtf20_lpmm: Spatial frequency at MTF = 0.2.
        limiting_resolution_lpmm: Resolution where contrast drops below threshold.
    """
    angle_deg: float
    spatial_freq_lpmm: np.ndarray
    mtf_values: np.ndarray
    mtf50_lpmm: float
    mtf20_lpmm: float
    limiting_resolution_lpmm: float


@dataclass
class SiemensStarResult:
    """
    Result of Siemens star analysis.

    Attributes:
        status: Analysis status.
        message: Human-readable status message.
        center_px: Detected center position (x, y) in pixels.
        limiting_resolution_lpmm: Overall limiting resolution (lp/mm).
        limiting_radius_px: Radius where spokes blur together (pixels).
        mtf50_lpmm: Average MTF50 across all directions.
        mtf20_lpmm: Average MTF20 across all directions.
        astigmatism_ratio: Ratio of max/min resolution (1.0 = no astigmatism).
        astigmatism_angle_deg: Angle of maximum resolution.
        directional_mtf: Per-direction MTF data.
        radii_px: Array of radii used for analysis.
        spatial_freq_lpmm: Array of corresponding spatial frequencies.
        contrast_vs_radius: 2D array of contrast [direction, radius].
    """
    status: AnalysisStatus
    message: str
    center_px: Optional[Tuple[float, float]] = None
    limiting_resolution_lpmm: float = 0.0
    limiting_radius_px: float = 0.0
    mtf50_lpmm: float = 0.0
    mtf20_lpmm: float = 0.0
    astigmatism_ratio: float = 1.0
    astigmatism_angle_deg: float = 0.0
    directional_mtf: List[DirectionalMTF] = field(default_factory=list)
    radii_px: Optional[np.ndarray] = None
    spatial_freq_lpmm: Optional[np.ndarray] = None
    contrast_vs_radius: Optional[np.ndarray] = None


class SiemensStarAnalyzer:
    """
    Analyzer for Siemens star (spoke) targets.

    Measures MTF across all orientations and detects astigmatism.

    The Siemens star has spokes that get closer together toward the center.
    At some radius, the camera can no longer resolve individual spokes.
    This "limiting resolution radius" directly indicates optical resolution.

    Spatial frequency at radius r:
        f = num_spokes / (2 * π * r * pixel_size)

    Example:
        >>> config = SiemensStarConfig(num_spokes=36, pixel_size_um=3.45)
        >>> analyzer = SiemensStarAnalyzer(config)
        >>> result = analyzer.analyze(image)
        >>> if result.status == AnalysisStatus.SUCCESS:
        ...     print(f"Resolution: {result.limiting_resolution_lpmm:.1f} lp/mm")
        ...     print(f"Astigmatism: {result.astigmatism_ratio:.2f}")
    """

    def __init__(self, config: Optional[SiemensStarConfig] = None):
        """
        Initialize Siemens star analyzer.

        Args:
            config: Analysis configuration. Uses defaults if None.

        Raises:
            ImportError: If OpenCV is not available.
        """
        if cv2 is None:
            raise ImportError(
                "OpenCV (cv2) is required for Siemens star analysis")

        self.config = config or SiemensStarConfig()
        self.config.validate()

    def analyze(self, image: np.ndarray) -> SiemensStarResult:
        """
        Analyze Siemens star image.

        Args:
            image: Input image containing Siemens star target.

        Returns:
            SiemensStarResult with MTF data and astigmatism measurements.
        """
        # Validate input
        if image is None or image.size == 0:
            return SiemensStarResult(
                status=AnalysisStatus.INVALID_IMAGE,
                message="Image is empty or None"
            )

        # Convert to grayscale
        gray = self._ensure_grayscale(image)

        # Apply blur for noise reduction
        if self.config.blur_kernel_size > 1:
            gray = cv2.GaussianBlur(
                gray,
                (self.config.blur_kernel_size, self.config.blur_kernel_size),
                0
            )

        # Detect center
        center = self._detect_center(gray)
        if center is None:
            return SiemensStarResult(
                status=AnalysisStatus.CENTER_NOT_FOUND,
                message="Could not detect Siemens star center"
            )

        # Determine radius range
        max_radius = self._compute_max_radius(gray, center)
        radii = np.linspace(
            self.config.min_radius_px,
            max_radius,
            self.config.num_radii
        )

        # Extract contrast vs radius for each direction
        contrast_data = self._extract_directional_contrast(gray, center, radii)
        if contrast_data is None:
            return SiemensStarResult(
                status=AnalysisStatus.SPOKE_DETECTION_FAILED,
                message="Failed to extract spoke contrast",
                center_px=center
            )

        # Compute spatial frequencies
        spatial_freq = self._radius_to_frequency(radii)

        # Compute directional MTF
        directional_mtf = self._compute_directional_mtf(
            contrast_data, radii, spatial_freq
        )

        # Check for sufficient contrast
        max_contrast = np.max(contrast_data)
        if max_contrast < self.config.min_contrast:
            return SiemensStarResult(
                status=AnalysisStatus.INSUFFICIENT_CONTRAST,
                message=f"Insufficient contrast: {max_contrast:.3f} < {self.config.min_contrast}",
                center_px=center,
                radii_px=radii,
                spatial_freq_lpmm=spatial_freq,
                contrast_vs_radius=contrast_data
            )

        # Compute overall metrics
        avg_mtf50 = np.mean([d.mtf50_lpmm for d in directional_mtf])
        avg_mtf20 = np.mean([d.mtf20_lpmm for d in directional_mtf])
        avg_limiting = np.mean(
            [d.limiting_resolution_lpmm for d in directional_mtf])

        # Compute astigmatism
        resolutions = [d.limiting_resolution_lpmm for d in directional_mtf]
        max_res = max(resolutions)
        min_res = min(resolutions) if min(resolutions) > 0 else 0.001
        astigmatism_ratio = max_res / min_res
        astigmatism_angle = directional_mtf[resolutions.index(
            max_res)].angle_deg

        # Compute limiting radius (where average contrast drops below threshold)
        avg_contrast = np.mean(contrast_data, axis=0)
        limiting_radius = self._find_limiting_radius(
            radii, avg_contrast, threshold=0.1
        )

        return SiemensStarResult(
            status=AnalysisStatus.SUCCESS,
            message="Analysis completed successfully",
            center_px=center,
            limiting_resolution_lpmm=avg_limiting,
            limiting_radius_px=limiting_radius,
            mtf50_lpmm=avg_mtf50,
            mtf20_lpmm=avg_mtf20,
            astigmatism_ratio=astigmatism_ratio,
            astigmatism_angle_deg=astigmatism_angle,
            directional_mtf=directional_mtf,
            radii_px=radii,
            spatial_freq_lpmm=spatial_freq,
            contrast_vs_radius=contrast_data
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

    def _detect_center(self, gray: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        Detect center of Siemens star using radial symmetry.

        Uses a combination of:
        1. Edge detection + Hough circles
        2. Radial gradient voting
        """
        h, w = gray.shape

        # Method 1: Hough circles for outer boundary
        search_radius = self.config.center_search_radius or min(h, w) // 4

        # Normalize to 8-bit for edge detection
        gray_8bit = cv2.normalize(
            gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # Detect circles
        circles = cv2.HoughCircles(
            gray_8bit,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=min(h, w) // 2,
            param1=100,
            param2=50,
            minRadius=search_radius // 2,
            maxRadius=min(h, w) // 2
        )

        if circles is not None and len(circles) > 0:
            # Return center of largest/best circle
            circle = circles[0][0]
            return (float(circle[0]), float(circle[1]))

        # Method 2: Gradient-based radial symmetry
        center = self._radial_symmetry_center(gray)
        if center is not None:
            return center

        # Fallback: image center
        return (w / 2.0, h / 2.0)

    def _radial_symmetry_center(
        self, gray: np.ndarray
    ) -> Optional[Tuple[float, float]]:
        """
        Find center using radial symmetry transform.

        The Siemens star has strong radial symmetry - gradients point
        toward or away from center.
        """
        h, w = gray.shape

        # Compute gradients
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        # Gradient magnitude and direction
        mag = np.sqrt(gx**2 + gy**2)
        mag_threshold = np.percentile(mag, 90)

        # Create voting accumulator
        accumulator = np.zeros((h, w), dtype=np.float64)

        # Sample strong gradient points
        strong_points = np.where(mag > mag_threshold)
        sample_step = max(1, len(strong_points[0]) // 5000)

        for i in range(0, len(strong_points[0]), sample_step):
            y, x = strong_points[0][i], strong_points[1][i]

            # Gradient direction (points toward brighter region)
            dx = gx[y, x]
            dy = gy[y, x]

            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                continue

            # Normalize
            length = np.sqrt(dx**2 + dy**2)
            dx /= length
            dy /= length

            # Vote along gradient direction (both ways for radial symmetry)
            for sign in [-1, 1]:
                for t in range(10, min(h, w) // 2, 5):
                    nx = int(x + sign * dx * t)
                    ny = int(y + sign * dy * t)
                    if 0 <= nx < w and 0 <= ny < h:
                        accumulator[ny, nx] += 1

        # Find maximum
        if accumulator.max() > 0:
            # Apply blur to smooth votes
            accumulator = cv2.GaussianBlur(accumulator, (21, 21), 0)
            max_idx = np.unravel_index(
                np.argmax(accumulator), accumulator.shape)
            return (float(max_idx[1]), float(max_idx[0]))

        return None

    def _compute_max_radius(
        self, gray: np.ndarray, center: Tuple[float, float]
    ) -> float:
        """Compute maximum usable radius based on image and config."""
        h, w = gray.shape
        cx, cy = center

        # Maximum radius that stays within image
        max_from_image = min(cx, w - cx, cy, h - cy) * 0.9

        if self.config.max_radius_px is not None:
            return min(self.config.max_radius_px, max_from_image)

        return max_from_image

    def _extract_directional_contrast(
        self,
        gray: np.ndarray,
        center: Tuple[float, float],
        radii: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Extract contrast vs radius for each spoke direction.

        Returns:
            2D array [num_directions, num_radii] of contrast values.
        """
        cx, cy = center
        num_directions = self.config.num_spokes  # One direction per spoke pair

        # Contrast array: [direction, radius]
        contrast = np.zeros((num_directions, len(radii)))

        # For each radius, extract circular profile and measure contrast
        for r_idx, radius in enumerate(radii):
            # Sample around circle
            profile = self._extract_circular_profile(gray, cx, cy, radius)
            if profile is None:
                continue

            # Compute contrast for each spoke direction
            samples_per_spoke = len(profile) // num_directions

            for d_idx in range(num_directions):
                # Extract segment for this direction
                start = d_idx * samples_per_spoke
                end = start + samples_per_spoke

                segment = profile[start:end]

                # Contrast = (max - min) / (max + min) (Michelson contrast)
                seg_max = np.max(segment)
                seg_min = np.min(segment)

                if seg_max + seg_min > 0:
                    contrast[d_idx, r_idx] = (
                        seg_max - seg_min) / (seg_max + seg_min)

        return contrast

    def _extract_circular_profile(
        self,
        gray: np.ndarray,
        cx: float,
        cy: float,
        radius: float
    ) -> Optional[np.ndarray]:
        """Extract intensity profile along circle at given radius."""
        h, w = gray.shape
        num_samples = self.config.angular_samples

        # Generate sample angles
        angles = np.linspace(0, 2 * np.pi, num_samples, endpoint=False)

        # Sample coordinates
        x_coords = cx + radius * np.cos(angles)
        y_coords = cy + radius * np.sin(angles)

        # Check bounds
        if (np.any(x_coords < 0) or np.any(x_coords >= w - 1) or
                np.any(y_coords < 0) or np.any(y_coords >= h - 1)):
            return None

        # Bilinear interpolation
        x0 = np.floor(x_coords).astype(int)
        y0 = np.floor(y_coords).astype(int)
        x1 = x0 + 1
        y1 = y0 + 1

        # Interpolation weights
        wx = x_coords - x0
        wy = y_coords - y0

        # Sample values
        values = (
            gray[y0, x0] * (1 - wx) * (1 - wy) +
            gray[y0, x1] * wx * (1 - wy) +
            gray[y1, x0] * (1 - wx) * wy +
            gray[y1, x1] * wx * wy
        )

        return values

    def _radius_to_frequency(self, radii: np.ndarray) -> np.ndarray:
        """
        Convert radius (pixels) to spatial frequency (lp/mm).

        For Siemens star:
            frequency = num_spokes / (2 * π * radius * pixel_size_mm)
        """
        pixel_size_mm = self.config.pixel_size_um / 1000.0
        circumference_mm = 2 * np.pi * radii * pixel_size_mm

        # Avoid division by zero
        with np.errstate(divide='ignore'):
            freq = self.config.num_spokes / (2 * circumference_mm)

        freq[~np.isfinite(freq)] = 0
        return freq

    def _compute_directional_mtf(
        self,
        contrast_data: np.ndarray,
        radii: np.ndarray,
        spatial_freq: np.ndarray
    ) -> List[DirectionalMTF]:
        """Compute MTF curve for each spoke direction."""
        num_directions = contrast_data.shape[0]
        results = []

        for d_idx in range(num_directions):
            angle = (d_idx * 180.0) / num_directions  # 0-180 degrees

            contrast = contrast_data[d_idx, :]

            # Normalize to get MTF (contrast at max radius = 1.0)
            max_contrast = np.max(contrast)
            if max_contrast > 0:
                mtf = contrast / max_contrast
            else:
                mtf = contrast.copy()

            # Find MTF50, MTF20, limiting resolution
            mtf50 = self._find_frequency_at_mtf(spatial_freq, mtf, 0.5)
            mtf20 = self._find_frequency_at_mtf(spatial_freq, mtf, 0.2)
            limiting = self._find_frequency_at_mtf(spatial_freq, mtf, 0.1)

            results.append(DirectionalMTF(
                angle_deg=angle,
                spatial_freq_lpmm=spatial_freq.copy(),
                mtf_values=mtf,
                mtf50_lpmm=mtf50,
                mtf20_lpmm=mtf20,
                limiting_resolution_lpmm=limiting
            ))

        return results

    def _find_frequency_at_mtf(
        self,
        freq: np.ndarray,
        mtf: np.ndarray,
        target_mtf: float
    ) -> float:
        """Find spatial frequency where MTF drops to target value."""
        # MTF decreases with increasing frequency (decreasing radius)
        # freq is sorted decreasing (large radius = low freq at start)

        # Find crossings
        for i in range(len(mtf) - 1):
            if mtf[i] >= target_mtf > mtf[i + 1]:
                # Linear interpolation
                t = (target_mtf - mtf[i]) / (mtf[i + 1] - mtf[i])
                return freq[i] + t * (freq[i + 1] - freq[i])

        # If never crosses, return max frequency if MTF stays above target
        if np.all(mtf >= target_mtf):
            return float(np.max(freq))

        return 0.0

    def _find_limiting_radius(
        self,
        radii: np.ndarray,
        contrast: np.ndarray,
        threshold: float
    ) -> float:
        """Find radius where contrast drops below threshold."""
        # Contrast should be high at large radius, low at small radius
        # Find where it crosses threshold (going from high to low radius)

        for i in range(len(contrast) - 1, 0, -1):
            if contrast[i] >= threshold > contrast[i - 1]:
                # Linear interpolation
                t = (threshold - contrast[i - 1]) / \
                    (contrast[i] - contrast[i - 1])
                return radii[i - 1] + t * (radii[i] - radii[i - 1])

        # If never drops below threshold
        if np.all(contrast >= threshold):
            return float(radii[0])  # Minimum radius

        return float(radii[-1])  # Maximum radius

    def get_mtf_at_angle(
        self,
        result: SiemensStarResult,
        angle_deg: float
    ) -> Optional[DirectionalMTF]:
        """
        Get MTF data for specific angle.

        Args:
            result: Analysis result.
            angle_deg: Desired angle in degrees (0-180).

        Returns:
            DirectionalMTF closest to requested angle, or None if not available.
        """
        if not result.directional_mtf:
            return None

        # Find closest direction
        best_match = None
        best_diff = float('inf')

        for mtf in result.directional_mtf:
            diff = abs(mtf.angle_deg - (angle_deg % 180))
            diff = min(diff, 180 - diff)  # Handle wrap-around

            if diff < best_diff:
                best_diff = diff
                best_match = mtf

        return best_match

    def get_astigmatism_axes(
        self,
        result: SiemensStarResult
    ) -> Tuple[float, float, float, float]:
        """
        Get astigmatism axis information.

        Returns:
            Tuple of (best_angle, best_resolution, worst_angle, worst_resolution)
            Angles in degrees, resolutions in lp/mm.
        """
        if not result.directional_mtf:
            return (0.0, 0.0, 0.0, 0.0)

        resolutions = [(m.angle_deg, m.limiting_resolution_lpmm)
                       for m in result.directional_mtf]

        best = max(resolutions, key=lambda x: x[1])
        worst = min(resolutions, key=lambda x: x[1])

        return (best[0], best[1], worst[0], worst[1])
