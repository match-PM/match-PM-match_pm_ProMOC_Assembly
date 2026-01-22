"""
MTF Analysis using Slanted Edge Method (ISO 12233).

This module provides MTF (Modulation Transfer Function) computation
using the slanted edge method according to ISO 12233.

The algorithm works as follows:
1. Extract ROI containing slanted edge
2. Detect edge angle using Hough transform
3. Compute Edge Spread Function (ESF) by projecting along edge
4. Compute Line Spread Function (LSF) = derivative of ESF
5. Compute MTF = |FFT(LSF)|
6. Extract MTF50, MTF20, MTF10 values

Usage:
    from camera_nodes.algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
    
    config = MTFConfig(pixel_size_um=3.45)
    analyzer = MTFAnalyzer(config)
    
    result = analyzer.compute_mtf(image)
    print(f"MTF50: {result.mtf50:.2f} lp/mm")

Classes:
    MTFConfig: Configuration for MTF analysis
    MTFResult: Result of MTF computation
    MTFAnalyzer: Main MTF analysis implementation
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


@dataclass
class MTFConfig:
    """
    Configuration for MTF analysis.

    Attributes:
        pixel_size_um: Pixel size in micrometers
        roi_width: Width of ROI for edge extraction (pixels)
        roi_height: Height of ROI for edge extraction (pixels)
        roi_center: Center of ROI as (x, y). None = image center
        min_edge_angle: Minimum acceptable edge angle (degrees)
        max_edge_angle: Maximum acceptable edge angle (degrees)
        oversample_factor: Oversampling factor for ESF
        canny_low: Canny edge detector low threshold
        canny_high: Canny edge detector high threshold
        hough_threshold: Hough transform vote threshold
    """
    pixel_size_um: float = 3.45
    roi_width: int = 200
    roi_height: int = 200
    roi_center: Optional[Tuple[int, int]] = None
    min_edge_angle: float = 2.0
    max_edge_angle: float = 10.0
    oversample_factor: int = 4
    canny_low: int = 50
    canny_high: int = 150
    hough_threshold: int = 50

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.pixel_size_um <= 0:
            raise ValueError(
                f"pixel_size_um must be positive, got {self.pixel_size_um}")
        if self.roi_width <= 0 or self.roi_height <= 0:
            raise ValueError(f"ROI dimensions must be positive")
        if self.min_edge_angle < 0 or self.max_edge_angle <= self.min_edge_angle:
            raise ValueError(
                f"Invalid edge angle range: [{self.min_edge_angle}, {self.max_edge_angle}]")
        if self.oversample_factor < 1:
            raise ValueError(
                f"oversample_factor must be >= 1, got {self.oversample_factor}")


@dataclass
class MTFResult:
    """
    Result of MTF computation.

    Attributes:
        mtf50: Frequency where MTF = 50% (lp/mm)
        mtf20: Frequency where MTF = 20% (lp/mm)
        mtf10: Frequency where MTF = 10% (lp/mm)
        frequencies: Frequency array (lp/mm)
        mtf_values: MTF values (normalized, 0-1)
        esf: Edge Spread Function
        lsf: Line Spread Function
        edge_angle: Detected edge angle (degrees)
        valid: True if measurement is valid
        error_msg: Error message if not valid
        roi_bounds: ROI bounds as (x1, y1, x2, y2)
    """
    mtf50: float = 0.0
    mtf20: float = 0.0
    mtf10: float = 0.0
    frequencies: np.ndarray = field(default_factory=lambda: np.array([]))
    mtf_values: np.ndarray = field(default_factory=lambda: np.array([]))
    esf: np.ndarray = field(default_factory=lambda: np.array([]))
    lsf: np.ndarray = field(default_factory=lambda: np.array([]))
    edge_angle: float = 0.0
    valid: bool = False
    error_msg: str = ""
    roi_bounds: Optional[Tuple[int, int, int, int]] = None

    def to_dict(self) -> dict:
        """Convert result to dictionary (for serialization)."""
        return {
            'mtf50': self.mtf50,
            'mtf20': self.mtf20,
            'mtf10': self.mtf10,
            'edge_angle': self.edge_angle,
            'valid': self.valid,
            'error_msg': self.error_msg,
            'nyquist_frequency': self.nyquist_frequency
        }

    @property
    def nyquist_frequency(self) -> float:
        """Nyquist frequency in lp/mm."""
        if len(self.frequencies) > 0:
            return float(np.max(self.frequencies))
        return 0.0


class MTFAnalyzer:
    """
    MTF Analysis using Slanted Edge Method (ISO 12233).

    The slanted edge method provides accurate MTF measurement by:
    - Using a slightly tilted edge (2-10°) to achieve oversampling
    - Computing the Edge Spread Function (ESF) by projection
    - Deriving Line Spread Function (LSF) from ESF
    - Computing MTF via FFT of LSF

    Usage:
        config = MTFConfig(pixel_size_um=3.45)
        analyzer = MTFAnalyzer(config)

        # Compute MTF from image containing slanted edge
        result = analyzer.compute_mtf(image)

        if result.valid:
            print(f"MTF50: {result.mtf50:.2f} lp/mm")
            print(f"MTF20: {result.mtf20:.2f} lp/mm")
        else:
            print(f"Error: {result.error_msg}")
    """

    def __init__(self, config: Optional[MTFConfig] = None):
        """
        Initialize MTF analyzer.

        Args:
            config: MTF configuration. Uses defaults if None.
        """
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required for MTF analysis")

        self.config = config or MTFConfig()
        self.config.validate()

    def compute_mtf(self, image: np.ndarray,
                    roi: Optional[Tuple[int, int, int, int]] = None) -> MTFResult:
        """
        Compute MTF from image containing a slanted edge.

        Args:
            image: Input image (grayscale or color)
            roi: Optional ROI as (x1, y1, x2, y2). Overrides config.

        Returns:
            MTFResult with computed values or error information
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Extract ROI
        roi_img, roi_bounds = self._extract_roi(gray, roi)
        if roi_img is None:
            return MTFResult(valid=False, error_msg="Failed to extract ROI")

        # Detect edge angle
        edge_angle = self._detect_edge_angle(roi_img)

        if edge_angle is None:
            return MTFResult(
                valid=False,
                error_msg="No edge detected",
                roi_bounds=roi_bounds
            )

        # Validate edge angle
        if abs(edge_angle) < self.config.min_edge_angle:
            return MTFResult(
                edge_angle=edge_angle,
                valid=False,
                error_msg=f"Edge angle too small: {edge_angle:.1f}° (min: {self.config.min_edge_angle}°)",
                roi_bounds=roi_bounds
            )

        if abs(edge_angle) > self.config.max_edge_angle:
            return MTFResult(
                edge_angle=edge_angle,
                valid=False,
                error_msg=f"Edge angle too large: {edge_angle:.1f}° (max: {self.config.max_edge_angle}°)",
                roi_bounds=roi_bounds
            )

        # Compute ESF
        esf = self._compute_esf(roi_img.astype(np.float64), edge_angle)

        if len(esf) < 10:
            return MTFResult(
                esf=esf,
                edge_angle=edge_angle,
                valid=False,
                error_msg="ESF too short for analysis",
                roi_bounds=roi_bounds
            )

        # Compute LSF = derivative of ESF
        lsf = np.diff(esf)

        # Apply Hamming window to reduce spectral leakage
        window = np.hamming(len(lsf))
        lsf_windowed = lsf * window

        # Compute MTF = |FFT(LSF)|
        fft_lsf = np.fft.fft(lsf_windowed)
        mtf = np.abs(fft_lsf[:len(fft_lsf)//2])

        # Normalize MTF(0) = 1
        if mtf[0] <= 0:
            return MTFResult(
                esf=esf,
                lsf=lsf,
                edge_angle=edge_angle,
                valid=False,
                error_msg="MTF(0) = 0, invalid measurement",
                roi_bounds=roi_bounds
            )

        mtf = mtf / mtf[0]

        # Compute frequency axis (lp/mm)
        effective_pixel_size = self.config.pixel_size_um / \
            self.config.oversample_factor  # µm
        sample_spacing = effective_pixel_size / 1000.0  # mm
        frequencies = np.fft.fftfreq(
            len(lsf_windowed), d=sample_spacing)[:len(mtf)]

        # Extract MTF50, MTF20, MTF10
        mtf50 = self._find_mtf_frequency(frequencies, mtf, 0.5)
        mtf20 = self._find_mtf_frequency(frequencies, mtf, 0.2)
        mtf10 = self._find_mtf_frequency(frequencies, mtf, 0.1)

        return MTFResult(
            mtf50=mtf50,
            mtf20=mtf20,
            mtf10=mtf10,
            frequencies=frequencies,
            mtf_values=mtf,
            esf=esf,
            lsf=lsf,
            edge_angle=edge_angle,
            valid=True,
            roi_bounds=roi_bounds
        )

    def _extract_roi(self, image: np.ndarray,
                     roi: Optional[Tuple[int, int, int, int]] = None
                     ) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """Extract ROI from image."""
        h, w = image.shape[:2]

        if roi is not None:
            x1, y1, x2, y2 = roi
        else:
            # Use config or center
            if self.config.roi_center is not None:
                cx, cy = self.config.roi_center
            else:
                cx, cy = w // 2, h // 2

            x1 = max(0, cx - self.config.roi_width // 2)
            x2 = min(w, cx + self.config.roi_width // 2)
            y1 = max(0, cy - self.config.roi_height // 2)
            y2 = min(h, cy + self.config.roi_height // 2)

        # Validate bounds
        if x1 >= x2 or y1 >= y2:
            return None, None

        return image[y1:y2, x1:x2], (x1, y1, x2, y2)

    def _detect_edge_angle(self, roi: np.ndarray) -> Optional[float]:
        """
        Detect edge angle using Hough transform.

        Args:
            roi: Grayscale ROI image

        Returns:
            Edge angle in degrees (relative to vertical), or None
        """
        # Convert to uint8 for Canny
        if roi.dtype != np.uint8:
            roi_u8 = ((roi - roi.min()) / (roi.max() -
                      roi.min() + 1e-10) * 255).astype(np.uint8)
        else:
            roi_u8 = roi

        # Canny edge detection (try multiple thresholds)
        edges = None
        lines = None
        canny_pairs = [
            (self.config.canny_low, self.config.canny_high),
            (max(5, self.config.canny_low // 2), max(20, self.config.canny_high // 2)),
            (10, 40),
        ]

        hough_thresholds = [
            self.config.hough_threshold,
            max(10, int(self.config.hough_threshold * 0.7)),
            max(5, int(self.config.hough_threshold * 0.4)),
        ]

        roi_blur = cv2.GaussianBlur(roi_u8, (3, 3), 0)

        for low, high in canny_pairs:
            edges = cv2.Canny(roi_blur, low, high)
            for ht in hough_thresholds:
                lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=ht)
                if lines is not None and len(lines) > 0:
                    break
            if lines is not None and len(lines) > 0:
                break

        if lines is None or len(lines) == 0:
            # Fallback: estimate angle from gradient orientation
            gx = cv2.Sobel(roi_blur, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(roi_blur, cv2.CV_64F, 0, 1, ksize=3)
            mag = np.sqrt(gx * gx + gy * gy)
            if np.max(mag) <= 0:
                return None
            thresh = np.percentile(mag, 95)
            mask = mag >= thresh
            if not np.any(mask):
                return None
            angles = np.degrees(np.arctan2(gy[mask], gx[mask]))
            # Normalize to [-90, 90]
            angles = ((angles + 90) % 180) - 90
            return float(np.median(angles))

        # Collect angles
        angles = []
        for line in lines:
            rho, theta = line[0]
            # Convert to degrees relative to vertical
            angle_deg = np.degrees(theta) - 90
            angles.append(angle_deg)

        # Use median for robustness
        angle = float(np.median(angles))
        # Normalize to [-90, 90]
        angle = ((angle + 90) % 180) - 90
        # Fold to smallest deviation (treat near-vertical/horizontal equivalently)
        if abs(angle) > 45.0:
            angle = angle - (90.0 * np.sign(angle))
        return angle

    def _compute_esf(self, roi: np.ndarray, edge_angle: float) -> np.ndarray:
        """
        Compute Edge Spread Function by projection along edge.

        Uses the slanted edge angle to achieve oversampling.

        Args:
            roi: Float64 ROI image
            edge_angle: Edge angle in degrees

        Returns:
            ESF array (oversampled)
        """
        h, w = roi.shape
        angle_rad = np.radians(edge_angle)

        # Collect all pixels with their perpendicular distance to edge
        esf_points = []

        for row in range(h):
            # Offset due to edge slant
            offset = row * np.tan(angle_rad)

            for col in range(w):
                # Position perpendicular to edge (oversampled)
                pos = (col - w/2 - offset) * self.config.oversample_factor
                esf_points.append((pos, roi[row, col]))

        # Sort by position
        esf_points.sort(key=lambda x: x[0])

        positions = np.array([p[0] for p in esf_points])
        values = np.array([p[1] for p in esf_points])

        # Bin the data for uniform sampling
        bin_edges = np.arange(positions.min(), positions.max(), 1)
        bin_indices = np.digitize(positions, bin_edges)

        # Average values in each bin
        esf = []
        for i in range(1, len(bin_edges)):
            mask = bin_indices == i
            if np.sum(mask) > 0:
                esf.append(np.mean(values[mask]))

        return np.array(esf)

    def _find_mtf_frequency(self, frequencies: np.ndarray, mtf: np.ndarray,
                            threshold: float) -> float:
        """
        Find frequency at given MTF threshold by interpolation.

        Args:
            frequencies: Frequency array (lp/mm)
            mtf: MTF values (0-1)
            threshold: MTF threshold (e.g., 0.5 for MTF50)

        Returns:
            Frequency in lp/mm where MTF crosses threshold
        """
        # Only positive frequencies
        mask = frequencies >= 0
        freq_pos = frequencies[mask]
        mtf_pos = mtf[mask]

        # Find crossing point
        for i in range(len(mtf_pos) - 1):
            if mtf_pos[i] >= threshold > mtf_pos[i+1]:
                # Linear interpolation
                f1, f2 = freq_pos[i], freq_pos[i+1]
                m1, m2 = mtf_pos[i], mtf_pos[i+1]

                if m1 != m2:
                    freq = f1 + (threshold - m1) * (f2 - f1) / (m2 - m1)
                    return float(freq)

        # Threshold not reached - return max frequency
        return float(freq_pos[-1]) if len(freq_pos) > 0 else 0.0


def compute_mtf(image: np.ndarray,
                pixel_size_um: float = 3.45,
                roi: Optional[Tuple[int, int, int, int]] = None) -> MTFResult:
    """
    Convenience function to compute MTF with default settings.

    Args:
        image: Input image containing slanted edge
        pixel_size_um: Pixel size in micrometers
        roi: Optional ROI as (x1, y1, x2, y2)

    Returns:
        MTFResult with computed values

    Example:
        result = compute_mtf(image, pixel_size_um=3.45)
        if result.valid:
            print(f"MTF50: {result.mtf50:.2f} lp/mm")
    """
    config = MTFConfig(pixel_size_um=pixel_size_um)
    analyzer = MTFAnalyzer(config)
    return analyzer.compute_mtf(image, roi=roi)
