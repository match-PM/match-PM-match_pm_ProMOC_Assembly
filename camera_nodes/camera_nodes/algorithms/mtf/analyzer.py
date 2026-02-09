"""MTF analyzer implementation (slanted edge)."""

from typing import Optional, Tuple
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from ..roi_detection import RoiDetector
from .config import MTFConfig
from .result import MTFResult
from .processing import (
    compute_esf,
    smooth_esf,
    compute_lsf,
    compute_mtf_from_lsf,
    find_mtf_frequency,
    calculate_diffraction_mtf,
    validate_edge_crossing,
)
from .debug_export import export_debug


class MTFAnalyzer:
    """MTF Analysis using the slanted edge method."""

    def __init__(self, config: Optional[MTFConfig] = None,
                 camera_matrix: Optional[np.ndarray] = None,
                 dist_coeffs: Optional[np.ndarray] = None):
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required for MTF analysis")

        self.config = config or MTFConfig()
        self.config.validate()
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs

    def check_image_quality(self, roi: np.ndarray) -> dict:
        """Check image suitability for MTF analysis."""
        res = {'valid': True, 'reason': '', 'contrast': 0.0}

        if roi.size == 0:
            return {'valid': False, 'reason': 'Empty ROI'}

        michelson = RoiDetector.calculate_michelson_contrast(roi)
        res['contrast'] = michelson

        if michelson < 0.1:
            res['valid'] = False
            res['reason'] = f"Low Contrast ({michelson:.2f})"
            return res

        is_8bit = roi.dtype == np.uint8
        sat_high = 255 if is_8bit else 65535
        n_high = np.sum(roi >= (sat_high - 1))
        total_pixels = roi.size
        sat_percent = (n_high / total_pixels) * 100.0
        if sat_percent > 2.0:
            res['valid'] = False
            res['reason'] = f"Overexposure/Clipping ({sat_percent:.1f}% pixels saturated)"
            return res

        mx = np.max(roi)
        if mx < 50 and is_8bit:
            res['valid'] = False
            res['reason'] = f"Underexposed (Max value {mx} too low)"
            return res

        return res

    def compute_mtf(self, image: np.ndarray,
                    roi: Optional[Tuple[int, int, int, int]] = None,
                    debug_label: Optional[str] = None) -> MTFResult:
        """Compute MTF from image containing a slanted edge."""
        gray = self._prepare_gray_image(image)

        roi_img, roi_bounds = self._extract_roi(gray, roi)
        if roi_img is None:
            return MTFResult(valid=False, error_msg="Failed to extract ROI")

        quality_res = self.check_image_quality(roi_img)
        if not quality_res['valid']:
            return MTFResult(
                valid=False,
                error_msg=f"Image Quality Low: {quality_res['reason']}",
                roi_bounds=roi_bounds,
                contrast=quality_res.get('contrast', 0.0)
            )

        normal_angle = self._detect_gradient_normal_angle(roi_img)
        if normal_angle is None:
            return MTFResult(
                valid=False,
                error_msg="No edge detected",
                roi_bounds=roi_bounds
            )

        edge_warning = ""
        edge_line = None
        edge_hits = None
        edge_validation_ok = None
        if self.config.edge_validation_mode != "off":
            ok, msg, edge_line, edge_hits = validate_edge_crossing(roi_img, self.config)
            if not ok:
                if self.config.edge_validation_mode == "fail":
                    return MTFResult(
                        valid=False,
                        error_msg=f"Edge validation failed: {msg}",
                        roi_bounds=roi_bounds
                    )
                edge_warning = f"Edge validation warning: {msg}"
            edge_validation_ok = ok

        norm_angle_deg = normal_angle
        angle_mod = norm_angle_deg % 180
        if 45 <= angle_mod <= 135:
            roi_to_process = cv2.rotate(roi_img, cv2.ROTATE_90_CLOCKWISE)
            edge_direction = "horizontal"
            measure_angle = norm_angle_deg - 90
        else:
            roi_to_process = roi_img
            edge_direction = "vertical"
            measure_angle = norm_angle_deg

        measure_angle = ((measure_angle + 180) % 360) - 180
        if measure_angle > 90:
            measure_angle -= 180
        if measure_angle < -90:
            measure_angle += 180

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

        esf = compute_esf(roi_to_process.astype(np.float64), -measure_angle, self.config.oversample_factor)
        if len(esf) < 10:
            return MTFResult(
                esf=esf,
                edge_angle=measure_angle,
                valid=False,
                error_msg="ESF too short for analysis",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction
            )

        esf_raw = esf
        esf, smooth_warning = smooth_esf(esf, self.config)

        lsf = compute_lsf(esf, self.config)
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
                compute_mtf_from_lsf(lsf, self.config, measure_angle)
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

        mtf_raw_alt = None
        mtf_used_alt = None
        frequencies_alt = None
        if self.config.export_dual_curves and self.config.esf_smooth_mode != "none":
            lsf_raw = compute_lsf(esf_raw, self.config)
            if lsf_raw.size > 0:
                try:
                    frequencies_alt, mtf_raw_alt, mtf_used_alt, _, _ = \
                        compute_mtf_from_lsf(lsf_raw, self.config, measure_angle)
                except ValueError:
                    frequencies_alt = None
                    mtf_raw_alt = None
                    mtf_used_alt = None

        mtf_clipped = bool(self.config.mtf_clip_max > 0)
        mtf50 = find_mtf_frequency(frequencies, mtf_raw, 0.5)
        mtf20 = find_mtf_frequency(frequencies, mtf_raw, 0.2)
        mtf10 = find_mtf_frequency(frequencies, mtf_raw, 0.1)
        mtf_ideal = calculate_diffraction_mtf(frequencies, self.config)

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

        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)

        if self.config.debug_export_dir:
            esf_raw_dbg = esf_raw if self.config.esf_smooth_mode != "none" else None
            export_debug(
                config=self.config,
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

    def _prepare_gray_image(self, image: np.ndarray) -> np.ndarray:
        """Apply optional undistortion and return a grayscale image."""
        if len(image.shape) == 3:
            if self.camera_matrix is not None and self.dist_coeffs is not None:
                image = cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if self.camera_matrix is not None and self.dist_coeffs is not None:
            image = cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
        return image

    def _extract_roi(self, image: np.ndarray,
                     roi: Optional[Tuple[int, int, int, int]] = None
                     ) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """Extract ROI from image."""
        h, w = image.shape[:2]

        if roi is not None:
            x1, y1, x2, y2 = roi
        else:
            if self.config.roi_center is not None:
                cx, cy = self.config.roi_center
            else:
                cx, cy = w // 2, h // 2
            x1 = max(0, cx - self.config.roi_width // 2)
            x2 = min(w, cx + self.config.roi_width // 2)
            y1 = max(0, cy - self.config.roi_height // 2)
            y2 = min(h, cy + self.config.roi_height // 2)

        if x1 >= x2 or y1 >= y2:
            return None, None

        return image[y1:y2, x1:x2], (x1, y1, x2, y2)

    def _detect_gradient_normal_angle(self, roi: np.ndarray) -> Optional[float]:
        """Detect the gradient normal angle (perpendicular to edge)."""
        if roi is None or roi.size == 0:
            return None

        img_f = roi.astype(np.float64)

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

        a11_re = cv2.filter2D(img_f, cv2.CV_64F, k_re)
        a11_im = cv2.filter2D(img_f, cv2.CV_64F, k_im)

        magnitude = np.sqrt(a11_re**2 + a11_im**2)
        if np.max(magnitude) <= 1e-6:
            return None

        thresh = np.percentile(magnitude, 90)
        mask = magnitude > thresh
        if np.sum(mask) < 10:
            return None

        phis = np.arctan2(a11_im[mask], a11_re[mask])
        mean_sin = np.mean(np.sin(phis))
        mean_cos = np.mean(np.cos(phis))
        mean_phi = np.arctan2(mean_sin, mean_cos)
        return float(np.degrees(mean_phi))


def compute_mtf(image: np.ndarray,
                pixel_size_um: float = 2.40,
                roi: Optional[Tuple[int, int, int, int]] = None,
                debug_label: Optional[str] = None) -> MTFResult:
    """Convenience wrapper for MTF computation."""
    config = MTFConfig(pixel_size_um=pixel_size_um)
    analyzer = MTFAnalyzer(config)
    return analyzer.compute_mtf(image, roi=roi, debug_label=debug_label)
