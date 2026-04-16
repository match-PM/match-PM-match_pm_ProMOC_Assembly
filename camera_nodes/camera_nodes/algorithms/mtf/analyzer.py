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
    compute_esf_from_samples,
    smooth_esf,
    compute_lsf,
    compute_mtf_from_lsf,
    find_mtf_frequency,
    calculate_diffraction_mtf,
    validate_edge_crossing,
    extract_rggb_green_samples,
    rotate_sample_coordinates_90_cw,
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

        # --- Step 2: Reject unusable ROIs before doing any signal processing. ---
        quality_res = self.check_image_quality(roi_img)
        if not quality_res['valid']:
            return MTFResult(
                valid=False,
                error_msg=f"Image Quality Low: {quality_res['reason']}",
                roi_bounds=roi_bounds,
                contrast=quality_res.get('contrast', 0.0)
            )

        # --- Step 3: Estimate the edge orientation from the ROI gradients. ---
        normal_angle = self._detect_gradient_normal_angle(roi_img)
        if normal_angle is None:
            return MTFResult(
                valid=False,
                error_msg="No edge detected",
                roi_bounds=roi_bounds
            )

        # --- Step 4: Verify that one dominant edge actually crosses the ROI. ---
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
        rotate_for_projection = False
        if 45 <= angle_mod <= 135:
            edge_direction = "horizontal"
            measure_angle = norm_angle_deg - 90
            rotate_for_projection = True
        else:
            edge_direction = "vertical"
            measure_angle = norm_angle_deg

        measure_angle = self._normalize_measure_angle(measure_angle)

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

        if self.config.input_mode == "raw_bayer_rggb":
            return self._compute_raw_green_result(
                roi_img=roi_img,
                roi_bounds=roi_bounds,
                measure_angle=measure_angle,
                edge_direction=edge_direction,
                rotate_for_projection=rotate_for_projection,
                edge_warning=edge_warning,
                edge_line=edge_line,
                edge_hits=edge_hits,
                edge_validation_ok=edge_validation_ok,
                debug_label=debug_label,
            )

        roi_to_process = roi_img
        if rotate_for_projection:
            roi_to_process = cv2.rotate(roi_img, cv2.ROTATE_90_CLOCKWISE)
        return self._compute_dense_result(
            roi_to_process=roi_to_process,
            roi_img=roi_img,
            roi_bounds=roi_bounds,
            measure_angle=measure_angle,
            edge_direction=edge_direction,
            edge_warning=edge_warning,
            edge_line=edge_line,
            edge_hits=edge_hits,
            edge_validation_ok=edge_validation_ok,
            debug_label=debug_label,
        )

    def _normalize_measure_angle(self, measure_angle: float) -> float:
        """Normalize measured edge angle into [-90°, 90°]."""
        measure_angle = ((measure_angle + 180) % 360) - 180
        if measure_angle > 90:
            measure_angle -= 180
        if measure_angle < -90:
            measure_angle += 180
        return float(measure_angle)

    def _analyze_esf_curve(self, esf: np.ndarray, measure_angle: float) -> dict:
        """Convert one ESF curve into LSF/MTF arrays plus headline metrics."""
        if len(esf) < 10:
            raise ValueError("ESF too short for analysis")

        esf_raw = esf
        esf, smooth_warning = smooth_esf(esf, self.config)

        lsf = compute_lsf(esf, self.config)
        if lsf.size == 0:
            raise ValueError("LSF computation failed (empty)")

        frequencies, mtf_raw, mtf_used, lsf_windowed, mtf_peak_raw = compute_mtf_from_lsf(
            lsf,
            self.config,
            measure_angle,
        )

        mtf_raw_alt = None
        mtf_used_alt = None
        frequencies_alt = None
        if self.config.export_dual_curves and self.config.esf_smooth_mode != "none":
            lsf_raw = compute_lsf(esf_raw, self.config)
            if lsf_raw.size > 0:
                try:
                    frequencies_alt, mtf_raw_alt, mtf_used_alt, _, _ = compute_mtf_from_lsf(
                        lsf_raw,
                        self.config,
                        measure_angle,
                    )
                except ValueError:
                    frequencies_alt = None
                    mtf_raw_alt = None
                    mtf_used_alt = None

        return {
            "esf_raw": esf_raw,
            "esf": esf,
            "lsf": lsf,
            "lsf_windowed": lsf_windowed,
            "frequencies": frequencies,
            "mtf_raw": mtf_raw,
            "mtf_used": mtf_used,
            "mtf_raw_alt": mtf_raw_alt,
            "mtf_used_alt": mtf_used_alt,
            "frequencies_alt": frequencies_alt,
            "smooth_warning": smooth_warning,
            "mtf_peak_raw": mtf_peak_raw,
            "mtf50": find_mtf_frequency(frequencies, mtf_raw, 0.5),
            "mtf20": find_mtf_frequency(frequencies, mtf_raw, 0.2),
            "mtf10": find_mtf_frequency(frequencies, mtf_raw, 0.1),
        }

    def _compute_dense_result(
        self,
        roi_to_process: np.ndarray,
        roi_img: np.ndarray,
        roi_bounds: Optional[Tuple[int, int, int, int]],
        measure_angle: float,
        edge_direction: str,
        edge_warning: str,
        edge_line,
        edge_hits,
        edge_validation_ok,
        debug_label: Optional[str],
    ) -> MTFResult:
        try:
            curve = self._analyze_esf_curve(
                compute_esf(
                    roi_to_process.astype(np.float64),
                    -measure_angle,
                    self.config.oversample_factor,
                ),
                measure_angle,
            )
        except ValueError as exc:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=str(exc),
                roi_bounds=roi_bounds,
                edge_direction=edge_direction,
            )

        mtf_ideal = calculate_diffraction_mtf(curve["frequencies"], self.config)
        warning_msg = self._build_warning_message(
            edge_warning=edge_warning,
            curve_warnings=[curve["smooth_warning"]],
            mtf_peak_raw=curve["mtf_peak_raw"],
        )
        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)

        if self.config.debug_export_dir:
            esf_raw_dbg = (
                curve["esf_raw"] if self.config.esf_smooth_mode != "none" else None
            )
            export_debug(
                config=self.config,
                esf=curve["esf"],
                lsf=curve["lsf"],
                lsf_windowed=curve["lsf_windowed"],
                frequencies=curve["frequencies"],
                mtf_raw=curve["mtf_raw"],
                mtf_used=curve["mtf_used"],
                mtf_ideal=mtf_ideal,
                debug_label=debug_label,
                esf_raw=esf_raw_dbg,
                roi_img=roi_img,
                edge_line=edge_line,
                mtf_raw_alt=curve["mtf_raw_alt"],
                mtf_used_alt=curve["mtf_used_alt"],
                frequencies_alt=curve["frequencies_alt"],
                edge_hits=edge_hits,
                edge_validation_ok=edge_validation_ok,
            )

        return MTFResult(
            mtf50=curve["mtf50"],
            mtf20=curve["mtf20"],
            mtf10=curve["mtf10"],
            frequencies=curve["frequencies"],
            mtf_values=curve["mtf_used"],
            mtf_ideal=mtf_ideal,
            esf=curve["esf"],
            lsf=curve["lsf"],
            edge_angle=measure_angle,
            valid=True,
            roi_bounds=roi_bounds,
            edge_direction=edge_direction,
            sensor_nyquist=sensor_nyquist,
            mtf_peak=float(np.max(curve["mtf_used"])) if curve["mtf_used"].size > 0 else 0.0,
            mtf_peak_raw=curve["mtf_peak_raw"],
            mtf_clipped=bool(self.config.mtf_clip_max > 0),
            warning_msg=warning_msg,
            capture_mode="dense_gray",
            capture_pixel_format=self.config.capture_pixel_format,
            capture_binning_h=self.config.capture_binning_h,
            capture_binning_v=self.config.capture_binning_v,
            capture_exposure_us=self.config.capture_exposure_us,
            capture_gain=self.config.capture_gain,
            illumination_wavelength_um=self.config.wavelength_um,
            source_encoding=self.config.source_encoding,
        )

    def _compute_raw_green_result(
        self,
        roi_img: np.ndarray,
        roi_bounds: Optional[Tuple[int, int, int, int]],
        measure_angle: float,
        edge_direction: str,
        rotate_for_projection: bool,
        edge_warning: str,
        edge_line,
        edge_hits,
        edge_validation_ok,
        debug_label: Optional[str],
    ) -> MTFResult:
        sample_groups = extract_rggb_green_samples(roi_img)
        roi_h, roi_w = roi_img.shape[:2]
        group_curves = {}
        curve_warnings = []

        for group_name, (sample_x, sample_y, sample_values) in sample_groups.items():
            if rotate_for_projection:
                proj_x, proj_y, proj_w, proj_h = rotate_sample_coordinates_90_cw(
                    sample_x,
                    sample_y,
                    roi_w,
                    roi_h,
                )
            else:
                proj_x, proj_y = sample_x, sample_y
                proj_w, proj_h = roi_w, roi_h

            esf = compute_esf_from_samples(
                proj_x,
                proj_y,
                sample_values.astype(np.float64),
                -measure_angle,
                self.config.oversample_factor,
                proj_w,
                proj_h,
            )
            try:
                curve = self._analyze_esf_curve(esf, measure_angle)
            except ValueError as exc:
                return MTFResult(
                    edge_angle=measure_angle,
                    valid=False,
                    error_msg=f"{group_name.upper()} analysis failed: {exc}",
                    roi_bounds=roi_bounds,
                    edge_direction=edge_direction,
                )
            group_curves[group_name] = curve
            if curve["smooth_warning"]:
                curve_warnings.append(f"{group_name.upper()}: {curve['smooth_warning']}")

        if {"g1", "g2"} - set(group_curves):
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg="Raw green analysis requires both G1 and G2 sample planes",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction,
            )

        frequencies, mtf_raw, mtf_used, mtf_ideal = self._merge_group_curves(group_curves)
        avg_esf = self._average_curve([curve["esf"] for curve in group_curves.values()])
        avg_lsf = self._average_curve([curve["lsf"] for curve in group_curves.values()])

        g1_mtf50 = group_curves["g1"]["mtf50"]
        g2_mtf50 = group_curves["g2"]["mtf50"]
        g1_mtf20 = group_curves["g1"]["mtf20"]
        g2_mtf20 = group_curves["g2"]["mtf20"]
        g1_mtf10 = group_curves["g1"]["mtf10"]
        g2_mtf10 = group_curves["g2"]["mtf10"]
        mean_pair = (g1_mtf50 + g2_mtf50) / 2.0
        g1_g2_delta_pct = (
            abs(g1_mtf50 - g2_mtf50) / mean_pair * 100.0 if mean_pair > 0 else 0.0
        )

        if (
            self.config.raw_green_pair_warn_pct > 0
            and g1_g2_delta_pct > self.config.raw_green_pair_warn_pct
        ):
            curve_warnings.append(
                f"G1/G2 mismatch {g1_g2_delta_pct:.1f}% exceeds "
                f"{self.config.raw_green_pair_warn_pct:.1f}%"
            )

        mtf_peak_raw = float(np.max(mtf_raw)) if mtf_raw.size > 0 else 0.0
        warning_msg = self._build_warning_message(
            edge_warning=edge_warning,
            curve_warnings=curve_warnings,
            mtf_peak_raw=mtf_peak_raw,
        )
        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)

        if self.config.debug_export_dir:
            export_debug(
                config=self.config,
                esf=avg_esf,
                lsf=avg_lsf,
                lsf_windowed=avg_lsf,
                frequencies=frequencies,
                mtf_raw=mtf_raw,
                mtf_used=mtf_used,
                mtf_ideal=mtf_ideal,
                debug_label=debug_label,
                roi_img=roi_img,
                edge_line=edge_line,
                edge_hits=edge_hits,
                edge_validation_ok=edge_validation_ok,
                metadata={
                    "capture_mode": "raw_green",
                    "capture_pixel_format": self.config.capture_pixel_format,
                    "capture_binning_h": self.config.capture_binning_h,
                    "capture_binning_v": self.config.capture_binning_v,
                    "capture_exposure_us": self.config.capture_exposure_us,
                    "capture_gain": self.config.capture_gain,
                    "illumination_wavelength_um": self.config.wavelength_um,
                    "source_encoding": self.config.source_encoding,
                    "g1_mtf50": g1_mtf50,
                    "g2_mtf50": g2_mtf50,
                    "g1_g2_delta_pct": g1_g2_delta_pct,
                },
                group_curves=group_curves,
            )

        return MTFResult(
            mtf50=find_mtf_frequency(frequencies, mtf_raw, 0.5),
            mtf20=find_mtf_frequency(frequencies, mtf_raw, 0.2),
            mtf10=find_mtf_frequency(frequencies, mtf_raw, 0.1),
            frequencies=frequencies,
            mtf_values=mtf_used,
            mtf_ideal=mtf_ideal,
            esf=avg_esf,
            lsf=avg_lsf,
            edge_angle=measure_angle,
            valid=True,
            roi_bounds=roi_bounds,
            edge_direction=edge_direction,
            sensor_nyquist=sensor_nyquist,
            mtf_peak=float(np.max(mtf_used)) if mtf_used.size > 0 else 0.0,
            mtf_peak_raw=mtf_peak_raw,
            mtf_clipped=bool(self.config.mtf_clip_max > 0),
            warning_msg=warning_msg,
            capture_mode="raw_green",
            capture_pixel_format=self.config.capture_pixel_format,
            capture_binning_h=self.config.capture_binning_h,
            capture_binning_v=self.config.capture_binning_v,
            capture_exposure_us=self.config.capture_exposure_us,
            capture_gain=self.config.capture_gain,
            illumination_wavelength_um=self.config.wavelength_um,
            source_encoding=self.config.source_encoding,
            g1_mtf50=g1_mtf50,
            g2_mtf50=g2_mtf50,
            g1_mtf20=g1_mtf20,
            g2_mtf20=g2_mtf20,
            g1_mtf10=g1_mtf10,
            g2_mtf10=g2_mtf10,
            g1_g2_delta_pct=g1_g2_delta_pct,
        )

    def _average_curve(self, curves: list[np.ndarray]) -> np.ndarray:
        """Average 1D curves of different length by NaN-padding."""
        valid_curves = [curve for curve in curves if curve is not None and curve.size > 0]
        if not valid_curves:
            return np.array([])
        max_len = max(curve.size for curve in valid_curves)
        stacked = np.full((len(valid_curves), max_len), np.nan, dtype=np.float64)
        for idx, curve in enumerate(valid_curves):
            stacked[idx, : curve.size] = curve
        return np.nanmean(stacked, axis=0)

    def _merge_group_curves(self, group_curves: dict[str, dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Interpolate group curves onto a common frequency axis and average them."""
        freq_arrays = [curve["frequencies"] for curve in group_curves.values() if curve["frequencies"].size > 0]
        if not freq_arrays:
            raise ValueError("No valid group frequency arrays for raw-green merge")
        common_max = min(float(freq[-1]) for freq in freq_arrays)
        common_len = min(int(freq.size) for freq in freq_arrays)
        common_len = max(common_len, 8)
        frequencies = np.linspace(0.0, common_max, common_len)

        raw_stack = []
        used_stack = []
        for curve in group_curves.values():
            raw_stack.append(np.interp(frequencies, curve["frequencies"], curve["mtf_raw"]))
            used_stack.append(np.interp(frequencies, curve["frequencies"], curve["mtf_used"]))

        mtf_raw = np.mean(np.vstack(raw_stack), axis=0)
        mtf_used = np.mean(np.vstack(used_stack), axis=0)
        mtf_ideal = calculate_diffraction_mtf(frequencies, self.config)
        return frequencies, mtf_raw, mtf_used, mtf_ideal

    def _build_warning_message(
        self,
        edge_warning: str,
        curve_warnings: list[str],
        mtf_peak_raw: float,
    ) -> str:
        """Build a compact warning string for one final result object."""
        warning_msgs = []
        if edge_warning:
            warning_msgs.append(edge_warning)
        warning_msgs.extend([msg for msg in curve_warnings if msg])
        if (
            self.config.mtf_warn_threshold > 0
            and mtf_peak_raw > self.config.mtf_warn_threshold
        ):
            warning_msgs.append(
                f"MTF overshoot {mtf_peak_raw:.2f} (> {self.config.mtf_warn_threshold:.2f}). "
                "Possible sharpening/ISP or ROI/ESF issues."
            )
        return "; ".join(warning_msgs)

    def _prepare_gray_image(self, image: np.ndarray) -> np.ndarray:
        """Apply optional undistortion and return a grayscale image."""
        if self.config.input_mode == "raw_bayer_rggb":
            return image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

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
