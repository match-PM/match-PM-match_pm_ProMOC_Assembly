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
    canny_high: int = 150
    hough_threshold: int = 50
    f_number: float = 2.8 # Lens aperture (default assumption)
    wavelength_um: float = 0.555 # Green light default

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
    mtf_ideal: np.ndarray = field(default_factory=lambda: np.array([])) # Diffraction limit
    esf: np.ndarray = field(default_factory=lambda: np.array([]))
    lsf: np.ndarray = field(default_factory=lambda: np.array([]))
    edge_angle: float = 0.0
    valid: bool = False
    error_msg: str = ""
    roi_bounds: Optional[Tuple[int, int, int, int]] = None
    edge_name: str = ""
    edge_direction: str = ""
    sensor_nyquist: float = 0.0
    
    @property
    def nyquist_frequency(self) -> float:
        """Nyquist frequency in lp/mm (Sensor Limit)."""
        if self.sensor_nyquist > 0:
            return self.sensor_nyquist
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

        # Detect Gradient Normal Angle (Perpendicular to edge)
        normal_angle = self._detect_gradient_normal_angle(roi_img)

        if normal_angle is None:
            return MTFResult(
                valid=False,
                error_msg="No edge detected",
                roi_bounds=roi_bounds
            )
            
        # Determine Orientation and Rotate if needed
        # We need the edge to be roughly VERTICAL for the ESF projection algorithm.
        # Vertical Edge -> Normal is Horizontal (~0 or ~180 deg) -> Good.
        # Horizontal Edge -> Normal is Vertical (~90 or ~-90 deg) -> Needs Rotation.
        
        # Normalize to [-90, 90] range relative to X-axis
        # If angle is 175, it's -5 deg from X-axis.
        norm_angle_deg = normal_angle
        is_rotated = False
        
        # Check if Horizontal-ish (Deviation from Vertical axis > 45)
        # We look at deviation from X-axis (0).
        # if angle is near 90/-90 -> Horizontal Edge.
        
        # Map to [0, 180] for check
        angle_mod = norm_angle_deg % 180
        
        if 45 <= angle_mod <= 135:
            # Horizontal Edge case
            # Rotate image 90 degrees CW to make it Vertical
            roi_to_process = cv2.rotate(roi_img, cv2.ROTATE_90_CLOCKWISE)
            is_rotated = True
            edge_direction = "horizontal"
            
            # Adjust angle: The new normal will be (angle - 90)
            # e.g. 85 deg (Horizontal-ish) -> -5 deg (Vertical-ish)
            # e.g. 95 deg -> 5 deg
            measure_angle = norm_angle_deg - 90
        else:
            # Vertical Edge case
            roi_to_process = roi_img
            is_rotated = False
            edge_direction = "vertical"
            measure_angle = norm_angle_deg
            
        # Normalize effective angle to [-45, 45] for ESF calculation
        # This represents the "deviation from perfect vertical"
        measure_angle = ((measure_angle + 180) % 360) - 180 # to [-180, 180]
        if measure_angle > 90: measure_angle -= 180
        if measure_angle < -90: measure_angle += 180
        
        # Now measure_angle should be small (e.g. 5 deg) for a valid slanted edge
        
        # Validate edge angle
        if abs(measure_angle) < self.config.min_edge_angle:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=f"Edge angle too small: {measure_angle:.1f}° (min: {self.config.min_edge_angle}°)",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction
            )

        if abs(measure_angle) > self.config.max_edge_angle:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=f"Edge angle too large: {measure_angle:.1f}° (max: {self.config.max_edge_angle}°)",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction
            )

        # Compute ESF
        # Note: The gradient normal angle has opposite sign to the line slope.
        # Normal (nx, ny) -> Line slope is -nx/ny (if verticalish).
        # If Normal is +5 deg, Line slants -5 deg.
        # We pass -measure_angle to align the projection.
        esf = self._compute_esf(roi_to_process.astype(np.float64), -measure_angle)

        if len(esf) < 10:
            return MTFResult(
                esf=esf,
                edge_angle=measure_angle,
                valid=False,
                error_msg="ESF too short for analysis",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction
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
                edge_angle=measure_angle,
                valid=False,
                error_msg="Zero mean component in MTF",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction
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

        # Calculate Sensor Nyquist (Physical Limit)
        # Nyquist = 1 / (2 * pixel_pitch_mm)
        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)
        
        # Calculate Diffraction Limited MTF (Theoretical Max)
        mtf_ideal = self._calculate_diffraction_mtf(frequencies)

        return MTFResult(
            mtf50=mtf50,
            mtf20=mtf20,
            mtf10=mtf10,
            frequencies=frequencies,
            mtf_values=mtf,
            mtf_ideal=mtf_ideal,
            esf=esf,
            lsf=lsf,
            edge_angle=measure_angle,
            valid=True,
            roi_bounds=roi_bounds,
            edge_direction=edge_direction,
            sensor_nyquist=sensor_nyquist
        )

    def _calculate_diffraction_mtf(self, frequencies: np.ndarray) -> np.ndarray:
        """
        Calculates the theoretical diffraction-limited MTF for the given frequencies.
        Based on: MTF(f) = (2/pi) * (acos(f/fc) - (f/fc) * sqrt(1 - (f/fc)^2))
        where fc = 1 / (lambda * F#)
        """
        if self.config.f_number <= 0:
            return np.ones_like(frequencies)
            
        # Cutoff frequency in lp/mm
        # wavelength in mm = wavelength_um / 1000
        cutoff_freq = 1000.0 / (self.config.wavelength_um * self.config.f_number)
        
        # Normalized frequency
        v = np.abs(frequencies) / cutoff_freq
        v = np.clip(v, 0, 1) # Clip to valid range [0, 1]
        
        # Diffraction formula
        mtf_diff = (2.0 / np.pi) * (np.arccos(v) - v * np.sqrt(1 - v**2))
        
        # If frequency > cutoff, MTF is 0
        mtf_diff[frequencies > cutoff_freq] = 0.0
        
        return mtf_diff

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

    def _detect_gradient_normal_angle(self, roi: np.ndarray) -> Optional[float]:
        """
        Detect the angle of the gradient normal vector (perpendicular to edge).
        Returns angle in degrees [-180, 180].
        
        0 deg = Gradient in +X direction (Vertical Edge, Dark->Light)
        90 deg = Gradient in +Y direction (Horizontal Edge, Dark->Light)
        """
        # Convert to float for gradient computation
        img_f = roi.astype(np.float64)
        
        # 1. Compute Gradients
        gx = cv2.Scharr(img_f, cv2.CV_64F, 1, 0)
        gy = cv2.Scharr(img_f, cv2.CV_64F, 0, 1)
        
        # 2. Focus on the edge (Thresholding)
        mag = np.sqrt(gx**2 + gy**2)
        if np.max(mag) <= 1e-6:
            return None
            
        thresh = np.percentile(mag, 95)
        mask = mag > thresh
        
        if np.sum(mask) < 10:
            return None 
            
        # 3. Structure Tensor (Covariance of gradients without mean subtraction)
        # We want the dominant direction of the gradients themselves, not their spread.
        gx_masked = gx[mask]
        gy_masked = gy[mask]
        
        # Construct the Structure Tensor matrix Elements
        Sxx = np.sum(gx_masked**2)
        Syy = np.sum(gy_masked**2)
        Sxy = np.sum(gx_masked * gy_masked)
        
        # Eigen decomposition of [[Sxx, Sxy], [Sxy, Syy]]
        # This is a symmetric matrix, can use np.linalg.eigh or svd
        eigenvals, eigenvecs = np.linalg.eigh([[Sxx, Sxy], [Sxy, Syy]])
        
        # np.linalg.eigh returns eigenvalues in ASCENDING order
        # So the largest eigenvalue is at index 1 (last)
        normal = eigenvecs[:, 1]
        nx, ny = normal[0], normal[1]
        
        # Angle of Normal vector
        angle_normal_rad = np.arctan2(ny, nx)
        angle_deg = np.degrees(angle_normal_rad)
        
        return float(angle_deg)
        
    # Legacy alias for compatibility, wraps new method
    _detect_edge_angle = _detect_gradient_normal_angle

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
