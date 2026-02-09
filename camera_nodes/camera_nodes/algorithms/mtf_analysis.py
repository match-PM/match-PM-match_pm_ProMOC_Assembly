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
import csv
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
        lsf_window_mode: "full", "peak", or "none"
        lsf_peak_window_size: Window size (samples) for peak windowing (0 = auto)
        derivative_mode: "diff" (np.diff) or "iso" (central difference)
        apply_derivative_correction: Apply ISO derivative filter correction
        derivative_correction_max: Optional cap for derivative correction factor (0 disables)
        apply_angle_correction: Apply cos(theta) correction to frequency axis
        esf_smooth_mode: "none" or "sg" (Savitzky-Golay)
        esf_sg_window: Savitzky-Golay window length (odd)
        esf_sg_poly: Savitzky-Golay polynomial order
        edge_validation_mode: "off", "warn", or "fail" for edge-crossing validation
        edge_validation_percentile: Gradient magnitude percentile for edge points
        edge_validation_min_points: Minimum edge points required for validation
        clip_to_nyquist: Clip frequency axis/MTF to sensor Nyquist
        export_dual_curves: Export both smoothed and unsmoothed MTF curves (debug)
        mtf_clip_max: Optional max clamp for MTF values (0 disables)
        mtf_warn_threshold: Warning threshold for MTF overshoot
        debug_export_dir: Optional directory to export ESF/LSF/MTF debug data
        debug_export_prefix: Filename prefix for debug exports
        debug_export_csv: Export CSV debug data
        debug_export_png: Export PNG plots (requires matplotlib)
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
    # LSF windowing: "full" (default), "peak" (window around LSF peak), or "none"
    lsf_window_mode: str = "full"
    lsf_peak_window_size: int = 0  # samples; 0 = auto
    # Derivative / ISO options
    derivative_mode: str = "iso"  # "diff" or "iso"
    apply_derivative_correction: bool = True
    derivative_correction_max: float = 0.0  # 0 disables cap
    apply_angle_correction: bool = True
    # ESF smoothing
    esf_smooth_mode: str = "none"  # "none" or "sg"
    esf_sg_window: int = 11
    esf_sg_poly: int = 2
    # Edge geometry validation
    edge_validation_mode: str = "warn"  # "off" | "warn" | "fail"
    edge_validation_percentile: float = 90.0
    edge_validation_min_points: int = 50
    clip_to_nyquist: bool = True
    export_dual_curves: bool = False
    # MTF output handling
    mtf_clip_max: float = 0.0  # 0 disables clipping
    mtf_warn_threshold: float = 1.05  # warn if MTF peak exceeds this
    # Optional debug export
    debug_export_dir: Optional[str] = None
    debug_export_prefix: str = "mtf"
    debug_export_csv: bool = True
    debug_export_png: bool = False

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
        if self.lsf_window_mode not in {"full", "peak", "none"}:
            raise ValueError(
                f"lsf_window_mode must be one of ['full','peak','none'], got {self.lsf_window_mode}")
        if self.lsf_peak_window_size < 0:
            raise ValueError("lsf_peak_window_size must be >= 0")
        if self.derivative_mode not in {"diff", "iso"}:
            raise ValueError(
                f"derivative_mode must be one of ['diff','iso'], got {self.derivative_mode}")
        if self.derivative_correction_max < 0:
            raise ValueError("derivative_correction_max must be >= 0")
        if self.esf_smooth_mode not in {"none", "sg"}:
            raise ValueError(
                f"esf_smooth_mode must be one of ['none','sg'], got {self.esf_smooth_mode}")
        if self.esf_sg_window <= 0:
            raise ValueError("esf_sg_window must be > 0")
        if self.esf_sg_poly < 0:
            raise ValueError("esf_sg_poly must be >= 0")
        if self.edge_validation_mode not in {"off", "warn", "fail"}:
            raise ValueError(
                f"edge_validation_mode must be one of ['off','warn','fail'], got {self.edge_validation_mode}")
        if not (0 < self.edge_validation_percentile <= 100):
            raise ValueError("edge_validation_percentile must be in (0, 100]")
        if self.edge_validation_min_points < 0:
            raise ValueError("edge_validation_min_points must be >= 0")
        if self.mtf_clip_max < 0:
            raise ValueError("mtf_clip_max must be >= 0")
        if self.mtf_warn_threshold < 0:
            raise ValueError("mtf_warn_threshold must be >= 0")


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
        mtf_peak: Peak MTF value after optional clipping
        mtf_peak_raw: Peak MTF value before clipping
        mtf_clipped: True if clipping was applied
        warning_msg: Warning message (e.g., MTF overshoot)
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
    mtf_peak: float = 0.0
    mtf_peak_raw: float = 0.0
    mtf_clipped: bool = False
    warning_msg: str = ""
    
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
                    roi: Optional[Tuple[int, int, int, int]] = None,
                    debug_label: Optional[str] = None) -> MTFResult:
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

        # Optional edge geometry validation (edge should cross ROI boundaries)
        edge_warning = ""
        edge_line = None
        edge_hits = None
        edge_validation_ok = None
        if self.config.edge_validation_mode != "off":
            ok, msg, edge_line, edge_hits = self._validate_edge_crossing(roi_img)
            if not ok:
                if self.config.edge_validation_mode == "fail":
                    return MTFResult(
                        valid=False,
                        error_msg=f"Edge validation failed: {msg}",
                        roi_bounds=roi_bounds
                    )
                edge_warning = f"Edge validation warning: {msg}"
            edge_validation_ok = ok
            
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

        # Optional ESF smoothing (e.g., Savitzky-Golay)
        esf_raw = esf
        smooth_warning = ""
        esf, smooth_warning = self._smooth_esf(esf)

        # Compute LSF = derivative of ESF (ISO or diff)
        lsf = self._compute_lsf(esf)
        if lsf.size == 0:
            return MTFResult(
                esf=esf,
                edge_angle=measure_angle,
                valid=False,
                error_msg="LSF computation failed (empty)",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction
            )

        try:
            frequencies, mtf_raw, mtf_used, lsf_windowed, mtf_peak_raw = \
                self._compute_mtf_from_lsf(lsf, measure_angle)
        except ValueError as e:
            return MTFResult(
                esf=esf,
                lsf=lsf,
                edge_angle=measure_angle,
                valid=False,
                error_msg=str(e),
                roi_bounds=roi_bounds,
                edge_direction=edge_direction
            )

        # Optional dual-curve export (compute from unsmoothed ESF)
        mtf_raw_alt = None
        mtf_used_alt = None
        frequencies_alt = None
        if self.config.export_dual_curves and self.config.esf_smooth_mode != "none":
            lsf_raw = self._compute_lsf(esf_raw)
            if lsf_raw.size > 0:
                try:
                    frequencies_alt, mtf_raw_alt, mtf_used_alt, _, _ = \
                        self._compute_mtf_from_lsf(lsf_raw, measure_angle)
                except ValueError:
                    frequencies_alt = None
                    mtf_raw_alt = None
                    mtf_used_alt = None

        # Compute clipping flag
        mtf_clipped = False
        if self.config.mtf_clip_max > 0:
            mtf_clipped = True
            
        # Extract MTF50, MTF20, MTF10
        mtf50 = self._find_mtf_frequency(frequencies, mtf_raw, 0.5)
        mtf20 = self._find_mtf_frequency(frequencies, mtf_raw, 0.2)
        mtf10 = self._find_mtf_frequency(frequencies, mtf_raw, 0.1)
        
        # Calculate Diffraction Limited MTF (Theoretical Max)
        mtf_ideal = self._calculate_diffraction_mtf(frequencies)

        # Warning if MTF overshoots (>1) - likely sharpening/ROI issue
        warning_msgs = []
        if edge_warning:
            warning_msgs.append(edge_warning)
        if smooth_warning:
            warning_msgs.append(smooth_warning)
        if self.config.mtf_warn_threshold > 0 and mtf_peak_raw > self.config.mtf_warn_threshold:
            warning_msgs.append(
                f"MTF overshoot {mtf_peak_raw:.2f} (> {self.config.mtf_warn_threshold:.2f}). "
                "Possible sharpening/ISP or ROI/ESF issues."
            )
        warning_msg = "; ".join(warning_msgs)

        # Sensor Nyquist (Physical Limit)
        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)

        # Optional debug export (ESF/LSF/MTF)
        if self.config.debug_export_dir:
            esf_raw_dbg = esf_raw if self.config.esf_smooth_mode != "none" else None
            self._export_debug(
                esf=esf,
                lsf=lsf,
                lsf_windowed=lsf_windowed,
                frequencies=frequencies,
                mtf_raw=mtf_raw,
                mtf_used=mtf_used,
                mtf_ideal=mtf_ideal,
                debug_label=debug_label,
                esf_raw=esf_raw_dbg,
                roi_img=roi_img,
                edge_line=edge_line,
                mtf_raw_alt=mtf_raw_alt,
                mtf_used_alt=mtf_used_alt,
                frequencies_alt=frequencies_alt,
                edge_hits=edge_hits,
                edge_validation_ok=edge_validation_ok
            )

        return MTFResult(
            mtf50=mtf50,
            mtf20=mtf20,
            mtf10=mtf10,
            frequencies=frequencies,
            mtf_values=mtf_used,
            mtf_ideal=mtf_ideal,
            esf=esf,
            lsf=lsf,
            edge_angle=measure_angle,
            valid=True,
            roi_bounds=roi_bounds,
            edge_direction=edge_direction,
            sensor_nyquist=sensor_nyquist,
            mtf_peak=float(np.max(mtf_used)) if mtf_used.size > 0 else 0.0,
            mtf_peak_raw=mtf_peak_raw,
            mtf_clipped=mtf_clipped,
            warning_msg=warning_msg
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

    def _compute_lsf(self, esf: np.ndarray) -> np.ndarray:
        """Compute LSF from ESF using configured derivative mode."""
        if esf.size < 2:
            return np.array([])
        if self.config.derivative_mode == "iso":
            if esf.size < 3:
                return np.array([])
            kernel = np.array([-0.5, 0.0, 0.5], dtype=np.float64)
            return np.convolve(esf, kernel, mode="valid")
        return np.diff(esf)

    def _compute_mtf_from_lsf(self, lsf: np.ndarray, measure_angle: float) -> Tuple[
        np.ndarray, np.ndarray, np.ndarray, np.ndarray, float
    ]:
        """
        Compute frequency axis and MTF from an LSF.

        Returns: (frequencies, mtf_raw, mtf_used, lsf_windowed, mtf_peak_raw)
        """
        if lsf.size == 0:
            raise ValueError("LSF computation failed (empty)")

        lsf_windowed = self._apply_lsf_window(lsf)

        fft_lsf = np.fft.fft(lsf_windowed)
        mtf = np.abs(fft_lsf[:len(fft_lsf) // 2])

        if mtf.size == 0 or mtf[0] <= 0:
            raise ValueError("Zero mean component in MTF")

        mtf_raw = mtf / mtf[0]

        # Frequency axis (lp/mm)
        n = len(lsf_windowed)
        freq_cyc_per_pixel = np.fft.fftfreq(
            n, d=1.0 / self.config.oversample_factor)[:n // 2]
        pixel_pitch_mm = self.config.pixel_size_um / 1000.0
        frequencies_raw = freq_cyc_per_pixel / pixel_pitch_mm

        # Optional ISO derivative filter correction
        if self.config.apply_derivative_correction and self.config.derivative_mode == "iso":
            sample_spacing_mm = pixel_pitch_mm / self.config.oversample_factor
            omega = 2.0 * np.pi * frequencies_raw * sample_spacing_mm
            sin_omega = np.sin(omega)
            corr = np.ones_like(omega)
            mask = np.abs(sin_omega) > 1e-8
            corr[mask] = omega[mask] / sin_omega[mask]
            if self.config.derivative_correction_max > 0:
                corr = np.minimum(corr, self.config.derivative_correction_max)
            mtf_raw = mtf_raw * corr

        mtf_peak_raw = float(np.max(mtf_raw)) if mtf_raw.size > 0 else 0.0

        mtf_used = mtf_raw
        if self.config.mtf_clip_max > 0:
            mtf_used = np.minimum(mtf_raw, self.config.mtf_clip_max)

        # Optional cos(theta) correction for frequency axis
        if self.config.apply_angle_correction:
            cos_theta = float(abs(np.cos(np.radians(measure_angle))))
            frequencies = frequencies_raw * cos_theta
        else:
            frequencies = frequencies_raw

        # Optional Nyquist clipping
        if self.config.clip_to_nyquist:
            sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)
            mask = frequencies <= sensor_nyquist
            if np.any(mask):
                frequencies = frequencies[mask]
                mtf_raw = mtf_raw[mask]
                mtf_used = mtf_used[mask]

        if len(frequencies) != len(mtf_used):
            min_len = min(len(frequencies), len(mtf_used))
            frequencies = frequencies[:min_len]
            mtf_raw = mtf_raw[:min_len]
            mtf_used = mtf_used[:min_len]

        return frequencies, mtf_raw, mtf_used, lsf_windowed, mtf_peak_raw

    def _smooth_esf(self, esf: np.ndarray) -> Tuple[np.ndarray, str]:
        """Optional ESF smoothing. Returns (esf_used, warning)."""
        if esf.size == 0:
            return esf, ""

        mode = self.config.esf_smooth_mode
        if mode == "none":
            return esf, ""

        if mode == "sg":
            try:
                from scipy.signal import savgol_filter
                window = int(self.config.esf_sg_window)
                if window % 2 == 0:
                    window += 1
                if window < 5:
                    window = 5
                if window >= esf.size:
                    window = max(3, esf.size - 1)
                if window % 2 == 0:
                    window = max(3, window - 1)
                poly = int(self.config.esf_sg_poly)
                if poly >= window:
                    poly = max(1, window - 1)
                if window < 3 or window <= poly:
                    return esf, "ESF smoothing skipped (invalid window/poly)"
                esf_smoothed = savgol_filter(esf, window_length=window, polyorder=poly, mode="interp")
                return esf_smoothed, ""
            except Exception as e:
                return esf, f"ESF smoothing failed: {e}"

        return esf, f"ESF smoothing skipped (unknown mode: {mode})"

    def _validate_edge_crossing(self, roi: np.ndarray) -> Tuple[
        bool, str, Optional[Tuple[float, float, float, float]], Optional[str]
    ]:
        """
        Validate that the dominant edge crosses the ROI from one side to the opposite side.

        Returns (ok, message, (x0, y0, vx, vy)) if available.
        """
        if roi is None or roi.size == 0:
            return False, "empty ROI", None, None

        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi

        h, w = gray.shape[:2]
        if h < 4 or w < 4:
            return False, "ROI too small", None, None

        # Gradient magnitude
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        mag = np.sqrt(gx**2 + gy**2)

        max_mag = float(np.max(mag)) if mag.size > 0 else 0.0
        if max_mag <= 1e-6:
            return False, "no gradients", None, None

        thresh = np.percentile(mag, self.config.edge_validation_percentile)
        ys, xs = np.where(mag >= thresh)
        if len(xs) < max(1, self.config.edge_validation_min_points):
            return False, "insufficient edge points", None, None

        points = np.column_stack((xs, ys)).astype(np.float32)
        try:
            vx, vy, x0, y0 = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        except Exception:
            return False, "line fit failed", None, None

        eps = 1e-6
        hits = set()

        # Intersections with x=0 and x=w-1
        if abs(vx) > eps:
            t_left = (0 - x0) / vx
            y_left = y0 + t_left * vy
            if 0 <= y_left <= h - 1:
                hits.add("left")
            t_right = ((w - 1) - x0) / vx
            y_right = y0 + t_right * vy
            if 0 <= y_right <= h - 1:
                hits.add("right")

        # Intersections with y=0 and y=h-1
        if abs(vy) > eps:
            t_top = (0 - y0) / vy
            x_top = x0 + t_top * vx
            if 0 <= x_top <= w - 1:
                hits.add("top")
            t_bottom = ((h - 1) - y0) / vy
            x_bottom = x0 + t_bottom * vx
            if 0 <= x_bottom <= w - 1:
                hits.add("bottom")

        hits_str = ",".join(sorted(hits)) if hits else ""
        if ("left" in hits and "right" in hits) or ("top" in hits and "bottom" in hits):
            return True, "", (float(x0), float(y0), float(vx), float(vy)), hits_str

        if hits:
            return False, f"edge intersects only {sorted(hits)}", (float(x0), float(y0), float(vx), float(vy)), hits_str
        return False, "edge does not intersect ROI borders", (float(x0), float(y0), float(vx), float(vy)), hits_str

    def _apply_lsf_window(self, lsf: np.ndarray) -> np.ndarray:
        """Apply windowing to LSF based on configuration."""
        if lsf.size == 0:
            return lsf

        mode = self.config.lsf_window_mode
        if mode == "none":
            return lsf

        if mode == "peak":
            if self.config.lsf_peak_window_size > 0:
                size = min(int(self.config.lsf_peak_window_size), lsf.size)
            else:
                # Auto size: roughly one third of the LSF, minimum 9 samples
                size = min(lsf.size, max(9, lsf.size // 3))
            if size < 4:
                return lsf
            # Ensure odd window size for symmetry
            if size % 2 == 0:
                size += 1
                if size > lsf.size:
                    size = lsf.size
            peak_idx = int(np.argmax(np.abs(lsf)))
            half = size // 2
            start = max(0, peak_idx - half)
            end = min(lsf.size, peak_idx + half + 1)
            # Adjust to maintain window size if truncated
            if end - start < size:
                if start == 0:
                    end = min(lsf.size, start + size)
                elif end == lsf.size:
                    start = max(0, end - size)
            window = np.hamming(end - start)
            lsf_windowed = np.zeros_like(lsf)
            lsf_windowed[start:end] = lsf[start:end] * window
            return lsf_windowed

        # Default: full-length Hamming
        window = np.hamming(lsf.size)
        return lsf * window

    def _export_debug(self, esf: np.ndarray, lsf: np.ndarray, lsf_windowed: np.ndarray,
                      frequencies: np.ndarray, mtf_raw: np.ndarray, mtf_used: np.ndarray,
                      mtf_ideal: np.ndarray, debug_label: Optional[str],
                      esf_raw: Optional[np.ndarray] = None,
                      roi_img: Optional[np.ndarray] = None,
                      edge_line: Optional[Tuple[float, float, float, float]] = None,
                      mtf_raw_alt: Optional[np.ndarray] = None,
                      mtf_used_alt: Optional[np.ndarray] = None,
                      frequencies_alt: Optional[np.ndarray] = None,
                      edge_hits: Optional[str] = None,
                      edge_validation_ok: Optional[bool] = None) -> None:
        """Export ESF/LSF/MTF debug data to CSV/PNG (best-effort)."""
        try:
            from pathlib import Path
            import re
            import time
            out_dir = Path(self.config.debug_export_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            label = debug_label or "edge"
            safe_label = re.sub(r'[^A-Za-z0-9._-]+', '_', label).strip('_') or "edge"
            stem = f"{self.config.debug_export_prefix}_{safe_label}_{time.time_ns()}"

            if self.config.debug_export_csv:
                # ESF/LSF CSV (align to same index length if needed)
                max_len = max(esf.size, lsf.size, lsf_windowed.size)
                esf_pad = np.full(max_len, np.nan)
                lsf_pad = np.full(max_len, np.nan)
                lsfw_pad = np.full(max_len, np.nan)
                esf_pad[:esf.size] = esf
                lsf_pad[:lsf.size] = lsf
                lsfw_pad[:lsf_windowed.size] = lsf_windowed

                if esf_raw is not None and esf_raw.size > 0 and esf_raw.shape != esf.shape:
                    max_len = max(max_len, esf_raw.size)
                if esf_raw is not None and esf_raw.size > 0:
                    esf_raw_pad = np.full(max_len, np.nan)
                    esf_raw_pad[:esf_raw.size] = esf_raw
                    # Re-pad in case max_len changed
                    if max_len > esf_pad.size:
                        esf_pad = np.pad(esf_pad, (0, max_len - esf_pad.size), constant_values=np.nan)
                        lsf_pad = np.pad(lsf_pad, (0, max_len - lsf_pad.size), constant_values=np.nan)
                        lsfw_pad = np.pad(lsfw_pad, (0, max_len - lsfw_pad.size), constant_values=np.nan)
                    cols = [
                        np.arange(max_len),
                        esf_raw_pad,
                        esf_pad,
                        lsf_pad,
                        lsfw_pad,
                    ]
                    headers = ["index", "esf_raw", "esf_used", "lsf", "lsf_windowed"]
                else:
                    cols = [
                        np.arange(max_len),
                        esf_pad,
                        lsf_pad,
                        lsfw_pad,
                    ]
                    headers = ["index", "esf", "lsf", "lsf_windowed"]

                # Optional edge line parameters (constant columns)
                if edge_line is not None:
                    x0, y0, vx, vy = edge_line
                    cols.extend([
                        np.full(max_len, x0),
                        np.full(max_len, y0),
                        np.full(max_len, vx),
                        np.full(max_len, vy),
                    ])
                    headers.extend(["edge_x0", "edge_y0", "edge_vx", "edge_vy"])

                data_esf = np.column_stack(cols)
                headers_out = headers[:]
                edge_ok_val = "" if edge_validation_ok is None else str(int(edge_validation_ok))
                edge_hits_val = edge_hits if edge_hits is not None else ""
                if edge_validation_ok is not None:
                    headers_out.append("edge_validation_ok")
                if edge_hits is not None:
                    headers_out.append("edge_hits")

                with open(out_dir / f"{stem}_esf_lsf.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers_out)
                    for i in range(data_esf.shape[0]):
                        row = list(data_esf[i, :])
                        if edge_validation_ok is not None:
                            row.append(edge_ok_val)
                        if edge_hits is not None:
                            row.append(edge_hits_val)
                        writer.writerow(row)

                # MTF CSV
                # include raw and clipped if different
                freq = frequencies
                mtf_ideal_pad = mtf_ideal[:freq.size] if mtf_ideal.size > 0 else np.full(freq.size, np.nan)
                cols = [freq, mtf_raw[:freq.size], mtf_used[:freq.size], mtf_ideal_pad]
                headers = ["frequency_lpmm", "mtf_raw", "mtf_used", "mtf_ideal"]

                if mtf_raw_alt is not None and mtf_used_alt is not None and frequencies_alt is not None:
                    freq_alt = frequencies_alt
                    max_len = max(freq.size, freq_alt.size)
                    def _pad(arr, n):
                        out = np.full(n, np.nan)
                        out[:min(n, arr.size)] = arr[:min(n, arr.size)]
                        return out
                    cols = [
                        _pad(freq, max_len),
                        _pad(mtf_raw, max_len),
                        _pad(mtf_used, max_len),
                        _pad(mtf_ideal_pad, max_len),
                        _pad(freq_alt, max_len),
                        _pad(mtf_raw_alt, max_len),
                        _pad(mtf_used_alt, max_len),
                    ]
                    headers = [
                        "frequency_lpmm",
                        "mtf_raw",
                        "mtf_used",
                        "mtf_ideal",
                        "frequency_alt_lpmm",
                        "mtf_raw_alt",
                        "mtf_used_alt",
                    ]

                data_mtf = np.column_stack(cols)
                np.savetxt(
                    out_dir / f"{stem}_mtf.csv",
                    data_mtf,
                    delimiter=",",
                    header=",".join(headers),
                    comments=""
                )

            if self.config.debug_export_png:
                try:
                    import matplotlib.pyplot as plt
                    fig, axes = plt.subplots(3, 1, figsize=(8, 8), constrained_layout=True)
                    axes[0].plot(esf, color='tab:blue')
                    axes[0].set_title("ESF")
                    axes[0].set_ylabel("Intensity")

                    axes[1].plot(lsf, color='tab:orange', label='LSF')
                    axes[1].plot(lsf_windowed, color='tab:green', alpha=0.7, label='LSF windowed')
                    axes[1].set_title("LSF")
                    axes[1].set_ylabel("dI/dx")
                    axes[1].legend(loc="best", fontsize=8)

                    axes[2].plot(frequencies, mtf_raw[:frequencies.size], label='MTF raw')
                    if mtf_used is not mtf_raw:
                        axes[2].plot(frequencies, mtf_used[:frequencies.size], label='MTF used')
                    if mtf_ideal.size > 0:
                        axes[2].plot(frequencies, mtf_ideal[:frequencies.size], '--', label='MTF ideal')
                    if mtf_raw_alt is not None and mtf_used_alt is not None and frequencies_alt is not None:
                        axes[2].plot(
                            frequencies_alt, mtf_raw_alt[:frequencies_alt.size],
                            linestyle=':', color='tab:purple', label='MTF raw (unsmoothed)'
                        )
                        axes[2].plot(
                            frequencies_alt, mtf_used_alt[:frequencies_alt.size],
                            linestyle='--', color='tab:brown', label='MTF used (unsmoothed)'
                        )
                    axes[2].set_title("MTF")
                    axes[2].set_xlabel("Frequency (lp/mm)")
                    axes[2].set_ylabel("MTF")
                    axes[2].set_ylim(0, max(1.1, float(np.nanmax(mtf_raw)) if mtf_raw.size > 0 else 1.1))
                    axes[2].legend(loc="best", fontsize=8)

                    fig.savefig(out_dir / f"{stem}_debug.png", dpi=150)
                    plt.close(fig)
                except Exception:
                    # Matplotlib not available or failed; ignore PNG
                    pass

                # Optional ROI overlay with fitted edge line
                try:
                    if roi_img is not None and edge_line is not None:
                        if len(roi_img.shape) == 2:
                            roi_vis = cv2.cvtColor(roi_img, cv2.COLOR_GRAY2BGR)
                        else:
                            roi_vis = roi_img.copy()

                        x0, y0, vx, vy = edge_line
                        h, w = roi_vis.shape[:2]
                        eps = 1e-6
                        pts = []
                        if abs(vx) > eps:
                            t = (0 - x0) / vx
                            y = y0 + t * vy
                            if 0 <= y <= h - 1:
                                pts.append((0, int(round(y))))
                            t = ((w - 1) - x0) / vx
                            y = y0 + t * vy
                            if 0 <= y <= h - 1:
                                pts.append((w - 1, int(round(y))))
                        if abs(vy) > eps:
                            t = (0 - y0) / vy
                            x = x0 + t * vx
                            if 0 <= x <= w - 1:
                                pts.append((int(round(x)), 0))
                            t = ((h - 1) - y0) / vy
                            x = x0 + t * vx
                            if 0 <= x <= w - 1:
                                pts.append((int(round(x)), h - 1))

                        # Draw line if we have at least two intersections
                        if len(pts) >= 2:
                            p1, p2 = pts[0], pts[1]
                            cv2.line(roi_vis, p1, p2, (0, 255, 255), 1, cv2.LINE_AA)
                        for p in pts:
                            cv2.circle(roi_vis, p, 3, (0, 0, 255), -1, cv2.LINE_AA)

                        cv2.imwrite(str(out_dir / f"{stem}_roi_edge.png"), roi_vis)
                except Exception:
                    pass
        except Exception:
            # Best-effort debug export; never fail main pipeline
            return

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
        Uses Ghosal & Mehrotra Zernike Moment ($A_{11}$) method for sub-pixel accuracy.
        
        Returns:
            Angle in degrees [-180, 180]. 
            0 deg = Normal points +X (Vertical Edge, Dark->Light)
        """
        if roi is None or roi.size == 0:
            return None
            
        # Convert to float
        img_f = roi.astype(np.float64)
        
        # Zernike moments A11 masks (7x7 approximation)
        # N=7 masks for Re(A11) ~ Gx and Im(A11) ~ Gy
        k_re = np.array([
            [-0.0165, -0.0238, -0.0210, 0.0, 0.0210, 0.0238, 0.0165],
            [-0.0416, -0.0673, -0.0683, 0.0, 0.0683, 0.0673, 0.0416],
            [-0.0637, -0.1162, -0.1432, 0.0, 0.1432, 0.1162, 0.0637],
            [-0.0766, -0.1491, -0.2078, 0.0, 0.2078, 0.1491, 0.0766],
            [-0.0637, -0.1162, -0.1432, 0.0, 0.1432, 0.1162, 0.0637],
            [-0.0416, -0.0673, -0.0683, 0.0, 0.0683, 0.0673, 0.0416],
            [-0.0165, -0.0238, -0.0210, 0.0, 0.0210, 0.0238, 0.0165]
        ])
        k_im = k_re.T
        
        # Convolve
        a11_re = cv2.filter2D(img_f, cv2.CV_64F, k_re)
        a11_im = cv2.filter2D(img_f, cv2.CV_64F, k_im)
        
        # Magnitude check
        magnitude = np.sqrt(a11_re**2 + a11_im**2)
        if np.max(magnitude) <= 1e-6:
            return None
            
        thresh = np.percentile(magnitude, 90) # Top 10%
        mask = magnitude > thresh
        
        if np.sum(mask) < 10:
            return None
            
        # Calculate angles at strong edge pixels
        # phi is the angle of the normal vector
        phis = np.arctan2(a11_im[mask], a11_re[mask])
        
        # Robust averaging (circular mean)
        # Avoid issues at -180/180 transition
        mean_sin = np.mean(np.sin(phis))
        mean_cos = np.mean(np.cos(phis))
        mean_phi = np.arctan2(mean_sin, mean_cos)
        
        return float(np.degrees(mean_phi))
        
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
                roi: Optional[Tuple[int, int, int, int]] = None,
                debug_label: Optional[str] = None) -> MTFResult:
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
    return analyzer.compute_mtf(image, roi=roi, debug_label=debug_label)
