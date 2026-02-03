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
    
    config = MTFConfig(pixel_size_um=2.40)  # IDS U3-3800CP (Sony IMX183)
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


from .roi_detection import RoiDetector

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
    pixel_size_um: float = 2.40  # IDS U3-3800CP (Sony IMX183)
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
        edge_name: Name of measured edge ('top', 'right', 'bottom', 'left')
        edge_direction: Direction of edge ('vertical' or 'horizontal')
        contrast: Michelson contrast of the ROI
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
    edge_name: str = ""
    edge_direction: str = ""
    contrast: float = 0.0

    def to_dict(self) -> dict:
        """Convert result to dictionary (for serialization)."""
        return {
            'mtf50': self.mtf50,
            'mtf20': self.mtf20,
            'mtf10': self.mtf10,
            'edge_angle': self.edge_angle,
            'valid': self.valid,
            'error_msg': self.error_msg,
            'nyquist_frequency': self.nyquist_frequency,
            'edge_name': self.edge_name,
            'edge_direction': self.edge_direction,
            'contrast': self.contrast,
            'roi_bounds': self.roi_bounds,
        }
    
    def format_edge_info(self) -> str:
        """Format edge information for display."""
        if not self.edge_name:
            return ""
        
        edge_str = f"{self.edge_name.capitalize()} Edge"
        
        if self.roi_bounds:
            x, y, w, h = self.roi_bounds
            edge_str += f" @ x={x},y={y} {w}x{h}px"
        
        return edge_str

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
        config = MTFConfig(pixel_size_um=2.40)  # IDS U3-3800CP (Sony IMX183)
        analyzer = MTFAnalyzer(config)

        # Compute MTF from image containing slanted edge
        result = analyzer.compute_mtf(image)

        if result.valid:
            print(f"MTF50: {result.mtf50:.2f} lp/mm")
            print(f"MTF20: {result.mtf20:.2f} lp/mm")
        else:
            print(f"Error: {result.error_msg}")
    """

    def __init__(self, config: Optional[MTFConfig] = None, 
                 camera_matrix: Optional[np.ndarray] = None, 
                 dist_coeffs: Optional[np.ndarray] = None):
        """
        Initialize MTF analyzer.

        Args:
            config: MTF configuration. Uses defaults if None.
            camera_matrix: Optional 3x3 camera matrix for distortion correction.
            dist_coeffs: Optional distortion coefficients vector.
        """
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required for MTF analysis")

        self.config = config or MTFConfig()
        self.config.validate()
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs

    def check_image_quality(self, roi: np.ndarray) -> dict:
        """
        Check image suitability for MTF analysis.
        
        Checks:
        1. Saturation/Clipping (Critical for slanted edge)
        2. Contrast (Michelson)
        3. Dynamic Range
        """
        res = {'valid': True, 'reason': '', 'contrast': 0.0}
        
        if roi.size == 0:
            return {'valid': False, 'reason': 'Empty ROI'}
            
        # 1. Contrast Check (Reuse existing algorithim)
        michelson = RoiDetector.calculate_michelson_contrast(roi)
        res['contrast'] = michelson
            
        if michelson < 0.1: # < 10% contrast is very poor
             res['valid'] = False
             res['reason'] = f"Low Contrast ({michelson:.2f})"
             return res
             
        # 2. Saturation/Clipping Check
        # Saturated pixels on the edge destroy the LSF calculation.
        # We allow SOME saturation in the ROI (e.g. background), but not "too much".
        # Strict check: > 1% pixels saturated high (255 for 8-bit)
        
        # Assuming 8-bit image for now, or check range
        is_8bit = roi.dtype == np.uint8
        sat_high = 255 if is_8bit else 65535 
        sat_low = 0
        
        n_high = np.sum(roi >= (sat_high - 1)) # count 254/255
        
        total_pixels = roi.size
        sat_percent = (n_high / total_pixels) * 100.0
        
        if sat_percent > 2.0: # Tolerance 2%
             res['valid'] = False
             res['reason'] = f"Overexposure/Clipping ({sat_percent:.1f}% pixels saturated)"
             return res
        
        # 3. Brightness check
        mx = np.max(roi)
        if mx < 50 and is_8bit: 
             res['valid'] = False
             res['reason'] = f"Underexposed (Max value {mx} too low)"
             return res

        return res

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
        if len(image.shape) == 3:
            # Apply distortion correction if available (on color image)
            if self.camera_matrix is not None and self.dist_coeffs is not None:
                image = cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            # Apply distortion correction if available (on grayscale)
            if self.camera_matrix is not None and self.dist_coeffs is not None:
                image = cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
            gray = image

        # Extract ROI
        roi_img, roi_bounds = self._extract_roi(gray, roi)
        if roi_img is None:
            return MTFResult(valid=False, error_msg="Failed to extract ROI")

        # --- Image Quality Checks ---
        quality_res = self.check_image_quality(roi_img)
        if not quality_res['valid']:
            return MTFResult(
                valid=False,
                error_msg=f"Image Quality Low: {quality_res['reason']}",
                roi_bounds=roi_bounds,
                contrast=quality_res.get('contrast', 0.0)
            )

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
        Detect edge angle using PCA (Structure Tensor) for sub-pixel accuracy.
        
        Method:
        1. Compute gradients (Scharr/Sobel)
        2. Threshold to find edge pixels
        3. Compute Structure Tensor (Covariance of gradients)
        4. PCA to find dominant gradient direction
        
        This offers significantly higher accuracy (approx +/- 0.03 deg) compared 
        to Hough Transform (+/- 0.06 deg).
        """
        # Convert to float for gradient computation
        img_f = roi.astype(np.float64)
        
        # 1. Compute Gradients (Scharr is more rotationally symmetric than Sobel)
        gx = cv2.Scharr(img_f, cv2.CV_64F, 1, 0)
        gy = cv2.Scharr(img_f, cv2.CV_64F, 0, 1)
        
        # 2. Focus on the edge (Thresholding)
        mag = np.sqrt(gx**2 + gy**2)
        if np.max(mag) <= 1e-6:
            return None
            
        # Adaptive threshold: Top 5% of gradients
        thresh = np.percentile(mag, 95)
        # Use simple weighting or strict mask
        mask = mag > thresh
        
        if np.sum(mask) < 10:
            return None # Not enough edge pixels
            
        # 3. PCA on Gradient Vectors (Structure Tensor approach)
        # Construct data matrix of gradients [Gx, Gy] from edge pixels
        # We want the direction perpendicular to the edge (Gradient direction)
        gradients = np.column_stack((gx[mask], gy[mask]))
        
        # PCA via Covariance
        # mean_vec = np.mean(gradients, axis=0) # Should be non-zero for one-sided edge
        # We can use PCA directly on the scatter matrix of gradients
        # The eigenvector with LARGEST eigenvalue is the Gradient Direction (Normal to edge)
        # The eigenvector with SMALLEST eigenvalue is the Edge Direction
        
        # cv2.PCACompute is robust
        mean, eigenvectors, eigenvalues = cv2.PCACompute2(gradients, mean=None)
        
        # Eigenvectors[0] corresponds to largest eigenvalue -> Gradient Direction/Normal
        normal = eigenvectors[0] # [ny, nx] convention in OpenCV? No, [x, y] usually.
        # Check: PCACompute returns eigenvectors in rows.
        # normal = [nx, ny]
        nx, ny = normal[0], normal[1]
        
        # Angle of Normal vector
        angle_normal_rad = np.arctan2(ny, nx)
        
        # Edge is perpendicular to Normal
        angle_edge_rad = angle_normal_rad + (np.pi / 2.0)
        
        # Convert to degrees
        angle_deg = np.degrees(angle_edge_rad)
        
        # Normalize to [-90, 90] relative to vertical
        # Our reference is vertical edge (0 deg). 
        # So a horizontal line is 90.
        # Standard notation: 0 deg = Vertical.
        
        # Let's normalize carefully
        # First put in range [-180, 180]
        angle_deg = ((angle_deg + 180) % 360) - 180
        
        # 4. Refine with Hough (Sanity Check) - Optional
        # If PCA is wildly wrong (e.g. noise), Hough might be coarser but safer.
        # But PCA on thresholded gradients is extremely standard for ISO 12233.
        
        # Map to "deviation from vertical" (0 is vertical)
        # If angle is 85 (near horizontal), we effectively want 85.
        # If angle is 5 (near vertical), we want 5.
        # If angle is 175 (near vertical), we want -5.
        
        # Fold: If > 90, subtract 180. If < -90, add 180.
        if angle_deg > 90:
            angle_deg -= 180
        elif angle_deg < -90:
            angle_deg += 180
            
        # Final result is angle from Vertical axis
        # Note: If edge is Horizontal (90), this returns 90 or -90.
        # If edge is Vertical (0), returns 0.
        
        return float(angle_deg)

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
                pixel_size_um: float = 2.40,  # IDS U3-3800CP (Sony IMX183)
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
        result = compute_mtf(image, pixel_size_um=2.40)
        if result.valid:
            print(f"MTF50: {result.mtf50:.2f} lp/mm")
    """
    config = MTFConfig(pixel_size_um=pixel_size_um)
    analyzer = MTFAnalyzer(config)
    return analyzer.compute_mtf(image, roi=roi)
