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
                    roi_origin: Optional[Tuple[int, int]] = None,
                    debug_label: Optional[str] = None) -> MTFResult:
        """Compute MTF from image containing a slanted edge."""
        # Step 1: normalize the input into the grayscale/raw view that the
        # slanted-edge core expects.
        gray = self._prepare_gray_image(image)

        roi_img, roi_bounds = self._extract_roi(gray, roi)
        if roi_img is None:
            return MTFResult(valid=False, error_msg="Failed to extract ROI")
        absolute_roi_origin = self._resolve_absolute_roi_origin(roi_bounds, roi_origin)

        # Step 2: reject unusable ROIs before any edge fitting or ESF work.
        quality_res = self.check_image_quality(roi_img)
        if not quality_res['valid']:
            return MTFResult(
                valid=False,
                error_msg=f"Image Quality Low: {quality_res['reason']}",
                roi_bounds=roi_bounds,
                contrast=quality_res.get('contrast', 0.0)
            )

        # Step 3: estimate the edge orientation and keep the diagnostic values
        # so later exports can explain why a measurement passed or failed.
        geometry = self._estimate_edge_geometry(roi_img)
        if geometry is None:
            return MTFResult(
                valid=False,
                error_msg="No edge detected",
                roi_bounds=roi_bounds
            )

        # Step 4: verify that one dominant edge actually crosses the ROI.
        edge_warnings = []
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
                        roi_bounds=roi_bounds,
                        **self._result_diagnostics(geometry, roi_bounds),
                    )
                edge_warnings.append(f"Edge validation warning: {msg}")
            edge_validation_ok = ok
        measure_angle = float(geometry["measure_angle"])
        edge_direction = str(geometry["edge_direction"])
        rotate_for_projection = bool(geometry["rotate_for_projection"])
        if edge_line is None:
            edge_line = geometry.get("edge_line")

        if (
            self.config.angle_consistency_warn_deg > 0
            and float(geometry.get("consistency_deg") or 0.0) > self.config.angle_consistency_warn_deg
        ):
            edge_warnings.append(
                "Angle estimator disagreement "
                f"{float(geometry['consistency_deg']):.2f}deg exceeds "
                f"{self.config.angle_consistency_warn_deg:.2f}deg"
            )

        analysis_roi_img, analysis_origin, analysis_roi_bounds = self._extract_analysis_roi(
            roi_img,
            absolute_roi_origin,
            geometry,
        )

        if abs(measure_angle) < self.config.min_edge_angle:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=f"Edge angle too small: {measure_angle:.1f}° (min: {self.config.min_edge_angle}°)",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction,
                **self._result_diagnostics(geometry, analysis_roi_bounds),
            )

        if abs(measure_angle) > self.config.max_edge_angle:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=f"Edge angle too large: {measure_angle:.1f}° (max: {self.config.max_edge_angle}°)",
                roi_bounds=roi_bounds,
                edge_direction=edge_direction,
                **self._result_diagnostics(geometry, analysis_roi_bounds),
            )

        if self.config.input_mode == "raw_bayer_rggb":
            return self._compute_raw_green_result(
                analysis_roi_img=analysis_roi_img,
                roi_img=roi_img,
                roi_bounds=roi_bounds,
                analysis_roi_bounds=analysis_roi_bounds,
                analysis_origin=analysis_origin,
                measure_angle=measure_angle,
                edge_direction=edge_direction,
                rotate_for_projection=rotate_for_projection,
                edge_warnings=edge_warnings,
                edge_line=edge_line,
                edge_hits=edge_hits,
                edge_validation_ok=edge_validation_ok,
                geometry=geometry,
                debug_label=debug_label,
            )

        roi_to_process = analysis_roi_img
        if rotate_for_projection:
            roi_to_process = cv2.rotate(analysis_roi_img, cv2.ROTATE_90_CLOCKWISE)
        return self._compute_dense_result(
            roi_to_process=roi_to_process,
            roi_img=roi_img,
            roi_bounds=roi_bounds,
            analysis_roi_bounds=analysis_roi_bounds,
            analysis_origin=analysis_origin,
            measure_angle=measure_angle,
            edge_direction=edge_direction,
            edge_warnings=edge_warnings,
            edge_line=edge_line,
            edge_hits=edge_hits,
            edge_validation_ok=edge_validation_ok,
            geometry=geometry,
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

    def _result_diagnostics(
        self,
        geometry: dict,
        analysis_roi_bounds: Optional[Tuple[int, int, int, int]],
    ) -> dict[str, object]:
        """Build reusable angle/ROI diagnostics for result objects."""
        return {
            "edge_angle_method": str(geometry.get("method") or ""),
            "edge_angle_geometric": float(geometry.get("geometric_measure_angle") or 0.0),
            "edge_angle_phase": float(geometry.get("phase_measure_angle") or 0.0),
            "edge_angle_consistency_deg": float(geometry.get("consistency_deg") or 0.0),
            "edge_fit_residual_px": float(geometry.get("fit_residual_px") or 0.0),
            "edge_support_points": int(geometry.get("support_points") or 0),
            "analysis_roi_bounds": analysis_roi_bounds,
        }

    def _angle_difference_deg(self, first: float, second: float) -> float:
        """Return the smallest absolute difference between two angles."""
        delta = self._normalize_measure_angle(float(first) - float(second))
        return abs(delta)

    def _phase_geometry_from_normal_angle(
        self,
        normal_angle: float,
        support_points: int = 0,
    ) -> dict[str, object]:
        """Translate one gradient-normal angle into analyzer measurement geometry."""
        norm_angle_deg = float(normal_angle)
        angle_mod = norm_angle_deg % 180.0
        if 45.0 <= angle_mod <= 135.0:
            edge_direction = "horizontal"
            measure_angle = norm_angle_deg - 90.0
            rotate_for_projection = True
        else:
            edge_direction = "vertical"
            measure_angle = norm_angle_deg
            rotate_for_projection = False
        return {
            "measure_angle": self._normalize_measure_angle(measure_angle),
            "edge_direction": edge_direction,
            "rotate_for_projection": rotate_for_projection,
            "support_points": int(support_points),
        }

    def _fit_weighted_line(
        self,
        axis_values: np.ndarray,
        centers: np.ndarray,
        weights: np.ndarray,
    ) -> Optional[tuple[float, float, float]]:
        """Fit a weighted first-order line and return slope, intercept and RMSE."""
        if axis_values.size < 2 or centers.size < 2 or weights.size < 2:
            return None
        safe_weights = np.maximum(weights.astype(np.float64), 1e-12)
        design = np.column_stack((axis_values.astype(np.float64), np.ones(axis_values.size)))
        weighted_design = design * np.sqrt(safe_weights)[:, None]
        weighted_centers = centers.astype(np.float64) * np.sqrt(safe_weights)
        coeffs, _, _, _ = np.linalg.lstsq(weighted_design, weighted_centers, rcond=None)
        slope = float(coeffs[0])
        intercept = float(coeffs[1])
        predicted = slope * axis_values + intercept
        residual = float(np.sqrt(np.average((predicted - centers) ** 2, weights=safe_weights)))
        return slope, intercept, residual

    def _collect_edge_support(self, roi: np.ndarray) -> Optional[dict[str, object]]:
        """Build the shared strong-edge support mask used by both angle estimators."""
        if roi is None or roi.size == 0:
            return None

        img_f = roi.astype(np.float64)
        gx = cv2.Sobel(img_f, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(img_f, cv2.CV_64F, 0, 1, ksize=3)
        mag = np.sqrt(gx**2 + gy**2)
        if float(np.max(mag)) <= 1e-6:
            return None

        height, width = roi.shape[:2]
        vertical_edge = float(np.sum(np.abs(gx))) >= float(np.sum(np.abs(gy)))
        positive_mag = mag[mag > 1e-6]
        if positive_mag.size < 2:
            return None
        strong_threshold = float(
            np.percentile(
                positive_mag,
                max(50.0, min(self.config.edge_validation_percentile, 99.5)),
            )
        )
        if strong_threshold <= 1e-6:
            return None

        if vertical_edge:
            component = np.abs(gx)
            orientation_mask = np.abs(gx) >= np.abs(gy)
        else:
            component = np.abs(gy)
            orientation_mask = np.abs(gy) > np.abs(gx)
        support_mask = (mag >= strong_threshold) & orientation_mask
        support_pixels = int(np.count_nonzero(support_mask))
        if support_pixels < 2:
            return None

        return {
            "gx": gx,
            "gy": gy,
            "mag": mag,
            "component": component,
            "support_mask": support_mask,
            "vertical_edge": vertical_edge,
            "height": height,
            "width": width,
            "support_pixels": support_pixels,
        }

    def _orientation_mean_deg(
        self,
        angles_rad: np.ndarray,
        weights: np.ndarray,
    ) -> Optional[float]:
        """Average orientations modulo 180 degrees so edge polarity cannot skew the mean."""
        if angles_rad.size == 0 or weights.size == 0:
            return None
        safe_weights = np.maximum(weights.astype(np.float64), 1e-12)
        doubled = 2.0 * angles_rad.astype(np.float64)
        mean_sin = float(np.sum(safe_weights * np.sin(doubled)))
        mean_cos = float(np.sum(safe_weights * np.cos(doubled)))
        if abs(mean_sin) <= 1e-12 and abs(mean_cos) <= 1e-12:
            return None
        return float(np.degrees(0.5 * np.arctan2(mean_sin, mean_cos)) % 180.0)

    def _detect_geometric_edge_geometry(
        self,
        roi: np.ndarray,
        edge_support: Optional[dict[str, object]] = None,
    ) -> Optional[dict[str, object]]:
        """Estimate the edge angle by fitting a centerline through strong gradients."""
        support = edge_support or self._collect_edge_support(roi)
        if support is None:
            return None

        axis_values = []
        centers = []
        weights = []
        vertical_edge = bool(support["vertical_edge"])
        height = int(support["height"])
        width = int(support["width"])
        support_mask = support["support_mask"]
        component = support["component"]

        if vertical_edge:
            x_coords = np.arange(width, dtype=np.float64)
            for row in range(height):
                row_mask = support_mask[row, :]
                if not np.any(row_mask):
                    continue
                row_weights = component[row, row_mask]
                weight_sum = float(np.sum(row_weights))
                if weight_sum <= 1e-6:
                    continue
                center_x = float(np.average(x_coords[row_mask], weights=row_weights))
                axis_values.append(float(row))
                centers.append(center_x)
                weights.append(weight_sum)
        else:
            y_coords = np.arange(height, dtype=np.float64)
            for col in range(width):
                col_mask = support_mask[:, col]
                if not np.any(col_mask):
                    continue
                col_weights = component[col_mask, col]
                weight_sum = float(np.sum(col_weights))
                if weight_sum <= 1e-6:
                    continue
                center_y = float(np.average(y_coords[col_mask], weights=col_weights))
                axis_values.append(float(col))
                centers.append(center_y)
                weights.append(weight_sum)

        if len(axis_values) < 2:
            return None

        axis_arr = np.asarray(axis_values, dtype=np.float64)
        center_arr = np.asarray(centers, dtype=np.float64)
        weight_arr = np.asarray(weights, dtype=np.float64)
        fit = self._fit_weighted_line(axis_arr, center_arr, weight_arr)
        if fit is None:
            return None
        slope, intercept, residual = fit

        if vertical_edge:
            center_y = (height - 1) / 2.0
            center_x = slope * center_y + intercept
            edge_line = (float(center_x), float(center_y), float(slope), 1.0)
            measure_angle = self._normalize_measure_angle(-np.degrees(np.arctan(slope)))
            edge_direction = "vertical"
            rotate_for_projection = False
        else:
            center_x = (width - 1) / 2.0
            center_y = slope * center_x + intercept
            edge_line = (float(center_x), float(center_y), 1.0, float(slope))
            measure_angle = self._normalize_measure_angle(np.degrees(np.arctan(slope)))
            edge_direction = "horizontal"
            rotate_for_projection = True

        return {
            "measure_angle": float(measure_angle),
            "edge_direction": edge_direction,
            "rotate_for_projection": rotate_for_projection,
            "edge_line": edge_line,
            "support_points": int(axis_arr.size),
            "fit_residual_px": float(residual),
        }

    def _detect_gradient_normal_angle(
        self,
        roi: np.ndarray,
        edge_support: Optional[dict[str, object]] = None,
    ) -> Optional[float]:
        """Estimate the gradient normal angle on the same strong-edge support as the fit."""
        support = edge_support or self._collect_edge_support(roi)
        if support is None:
            return None

        support_mask = support["support_mask"]
        if int(np.count_nonzero(support_mask)) < 2:
            return None

        weights = support["component"][support_mask]
        gx = support["gx"][support_mask]
        gy = support["gy"][support_mask]
        valid = np.isfinite(weights) & np.isfinite(gx) & np.isfinite(gy) & (weights > 1e-6)
        if int(np.count_nonzero(valid)) < 2:
            return None

        return self._orientation_mean_deg(
            np.arctan2(gy[valid], gx[valid]),
            weights[valid],
        )

    def _estimate_edge_geometry(
        self,
        roi: np.ndarray,
    ) -> Optional[dict[str, object]]:
        """Choose the configured edge-angle estimate and attach diagnostics."""
        # Build both angle estimates first so the analyzer can report how well
        # they agree even when only one of them drives the final decision.
        edge_support = self._collect_edge_support(roi)
        if edge_support is None:
            return None

        phase_normal_angle = self._detect_gradient_normal_angle(roi, edge_support)
        phase_geometry = None
        if phase_normal_angle is not None:
            phase_geometry = self._phase_geometry_from_normal_angle(
                phase_normal_angle,
                support_points=int(edge_support.get("support_pixels") or 0),
            )
        geometric_geometry = self._detect_geometric_edge_geometry(roi, edge_support)

        selected = None
        method = ""
        mode = self.config.angle_estimation_mode

        if mode == "phase":
            if phase_geometry is None:
                return None
            selected = dict(phase_geometry)
            method = "phase"
        elif mode == "geometric":
            if geometric_geometry is None:
                return None
            selected = dict(geometric_geometry)
            method = "geometric"
        else:
            if (
                geometric_geometry is not None
                and int(geometric_geometry.get("support_points") or 0)
                >= self.config.angle_min_support_points
            ):
                selected = dict(geometric_geometry)
                method = "geometric"
            elif phase_geometry is not None and self.config.angle_allow_phase_fallback:
                selected = dict(phase_geometry)
                method = "phase_fallback"
            elif geometric_geometry is not None:
                selected = dict(geometric_geometry)
                method = "geometric"
            elif phase_geometry is not None:
                selected = dict(phase_geometry)
                method = "phase"
            else:
                return None

        selected["method"] = method
        selected["geometric_measure_angle"] = (
            float(geometric_geometry["measure_angle"]) if geometric_geometry is not None else None
        )
        selected["phase_measure_angle"] = (
            float(phase_geometry["measure_angle"]) if phase_geometry is not None else None
        )
        selected["support_points"] = int(selected.get("support_points") or 0)
        selected["fit_residual_px"] = float(selected.get("fit_residual_px") or 0.0)
        selected["consistency_deg"] = (
            self._angle_difference_deg(
                float(geometric_geometry["measure_angle"]),
                float(phase_geometry["measure_angle"]),
            )
            if geometric_geometry is not None and phase_geometry is not None
            else 0.0
        )
        return selected

    def _absolute_bounds_from_local_crop(
        self,
        image_shape: tuple[int, int],
        absolute_roi_origin: Tuple[int, int],
        local_bounds: Tuple[int, int, int, int],
    ) -> Tuple[int, int, int, int]:
        """Translate one crop relative to a local ROI into full-image bounds."""
        x1, y1, x2, y2 = local_bounds
        height, width = image_shape
        x1 = max(0, min(int(x1), width))
        y1 = max(0, min(int(y1), height))
        x2 = max(x1, min(int(x2), width))
        y2 = max(y1, min(int(y2), height))
        return (
            absolute_roi_origin[0] + x1,
            absolute_roi_origin[1] + y1,
            absolute_roi_origin[0] + x2,
            absolute_roi_origin[1] + y2,
        )

    def _extract_analysis_roi(
        self,
        roi_img: np.ndarray,
        absolute_roi_origin: Tuple[int, int],
        geometry: dict[str, object],
    ) -> tuple[np.ndarray, Tuple[int, int], Tuple[int, int, int, int]]:
        """Extract a narrower analysis strip around the fitted edge when possible."""
        height, width = roi_img.shape[:2]
        full_bounds = self._absolute_bounds_from_local_crop(
            (height, width),
            absolute_roi_origin,
            (0, 0, width, height),
        )
        if (
            self.config.analysis_strip_width_px <= 0
            or geometry.get("edge_line") is None
            or geometry.get("method") in {"phase", "phase_fallback"}
        ):
            return roi_img, absolute_roi_origin, full_bounds

        # The external ROI stays untouched for traceability, but the actual ESF
        # integration runs on a tighter strip around the fitted edge so manual
        # oversizing or nearby structures do not dominate the angle/MTF result.
        x0, y0, vx, vy = geometry["edge_line"]
        half_width = max(4, int(self.config.analysis_strip_width_px) // 2)
        eps = 1e-6

        if geometry.get("edge_direction") == "vertical":
            sample_y = np.array([0.0, float(max(0, height - 1))], dtype=np.float64)
            if abs(vy) > eps:
                sample_t = (sample_y - float(y0)) / float(vy)
                sample_x = float(x0) + sample_t * float(vx)
            else:
                sample_x = np.full(sample_y.shape, float(x0), dtype=np.float64)
            center_min = float(np.min(sample_x))
            center_max = float(np.max(sample_x))
            x1 = max(0, int(np.floor(center_min - half_width)))
            x2 = min(width, int(np.ceil(center_max + half_width + 1)))
            if x2 - x1 < min(width, 16):
                center = int(round(0.5 * (center_min + center_max)))
                x1 = max(0, center - max(8, half_width))
                x2 = min(width, center + max(8, half_width) + 1)
            local_bounds = (x1, 0, x2, height)
        else:
            sample_x = np.array([0.0, float(max(0, width - 1))], dtype=np.float64)
            if abs(vx) > eps:
                sample_t = (sample_x - float(x0)) / float(vx)
                sample_y = float(y0) + sample_t * float(vy)
            else:
                sample_y = np.full(sample_x.shape, float(y0), dtype=np.float64)
            center_min = float(np.min(sample_y))
            center_max = float(np.max(sample_y))
            y1 = max(0, int(np.floor(center_min - half_width)))
            y2 = min(height, int(np.ceil(center_max + half_width + 1)))
            if y2 - y1 < min(height, 16):
                center = int(round(0.5 * (center_min + center_max)))
                y1 = max(0, center - max(8, half_width))
                y2 = min(height, center + max(8, half_width) + 1)
            local_bounds = (0, y1, width, y2)

        x1, y1, x2, y2 = local_bounds
        if x1 >= x2 or y1 >= y2:
            return roi_img, absolute_roi_origin, full_bounds

        analysis_img = roi_img[y1:y2, x1:x2]
        analysis_origin = (absolute_roi_origin[0] + x1, absolute_roi_origin[1] + y1)
        analysis_bounds = self._absolute_bounds_from_local_crop(
            (height, width),
            absolute_roi_origin,
            local_bounds,
        )
        return analysis_img, analysis_origin, analysis_bounds

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
        analysis_roi_bounds: Optional[Tuple[int, int, int, int]],
        analysis_origin: Tuple[int, int],
        measure_angle: float,
        edge_direction: str,
        edge_warnings: list[str],
        edge_line,
        edge_hits,
        edge_validation_ok,
        geometry: dict[str, object],
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
                **self._result_diagnostics(geometry, analysis_roi_bounds),
            )

        mtf_ideal = calculate_diffraction_mtf(curve["frequencies"], self.config)
        warning_msg = self._build_warning_message(
            edge_warnings=edge_warnings,
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
                metadata=self._build_debug_metadata(
                    capture_mode="dense_gray",
                    extra={
                        "roi_origin_x": analysis_origin[0],
                        "roi_origin_y": analysis_origin[1],
                        "analysis_roi_bounds": analysis_roi_bounds,
                        "edge_angle_deg": measure_angle,
                        "edge_angle_method": geometry.get("method"),
                        "edge_angle_geometric": geometry.get("geometric_measure_angle"),
                        "edge_angle_phase": geometry.get("phase_measure_angle"),
                        "edge_angle_consistency_deg": geometry.get("consistency_deg"),
                        "edge_fit_residual_px": geometry.get("fit_residual_px"),
                        "edge_support_points": geometry.get("support_points"),
                    },
                ),
            )

        return MTFResult(
            mtf50=curve["mtf50"],
            mtf20=curve["mtf20"],
            mtf10=curve["mtf10"],
            frequencies=curve["frequencies"],
            frequencies_alt=(
                curve["frequencies_alt"]
                if curve["frequencies_alt"] is not None
                else np.array([])
            ),
            mtf_values=curve["mtf_used"],
            mtf_raw=curve["mtf_raw"],
            mtf_raw_alt=(
                curve["mtf_raw_alt"] if curve["mtf_raw_alt"] is not None else np.array([])
            ),
            mtf_used_alt=(
                curve["mtf_used_alt"] if curve["mtf_used_alt"] is not None else np.array([])
            ),
            mtf_ideal=mtf_ideal,
            esf_raw=curve["esf_raw"],
            esf=curve["esf"],
            lsf=curve["lsf"],
            lsf_windowed=curve["lsf_windowed"],
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
            **self._result_diagnostics(geometry, analysis_roi_bounds),
        )

    def _compute_raw_green_result(
        self,
        analysis_roi_img: np.ndarray,
        roi_img: np.ndarray,
        roi_bounds: Optional[Tuple[int, int, int, int]],
        analysis_roi_bounds: Optional[Tuple[int, int, int, int]],
        analysis_origin: Tuple[int, int],
        measure_angle: float,
        edge_direction: str,
        rotate_for_projection: bool,
        edge_warnings: list[str],
        edge_line,
        edge_hits,
        edge_validation_ok,
        geometry: dict[str, object],
        debug_label: Optional[str],
    ) -> MTFResult:
        sample_groups = extract_rggb_green_samples(
            analysis_roi_img,
            origin_x=analysis_origin[0],
            origin_y=analysis_origin[1],
            pattern=self.config.raw_bayer_pattern,
        )
        roi_h, roi_w = analysis_roi_img.shape[:2]
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
                    **self._result_diagnostics(geometry, analysis_roi_bounds),
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
                **self._result_diagnostics(geometry, analysis_roi_bounds),
            )

        frequencies, mtf_raw, mtf_used, mtf_ideal = self._merge_group_curves(group_curves)
        frequencies_alt = self._average_curve(
            [curve["frequencies_alt"] for curve in group_curves.values()]
        )
        mtf_raw_alt = self._average_curve(
            [curve["mtf_raw_alt"] for curve in group_curves.values()]
        )
        mtf_used_alt = self._average_curve(
            [curve["mtf_used_alt"] for curve in group_curves.values()]
        )
        avg_esf_raw = self._average_curve([curve["esf_raw"] for curve in group_curves.values()])
        avg_esf = self._average_curve([curve["esf"] for curve in group_curves.values()])
        avg_lsf = self._average_curve([curve["lsf"] for curve in group_curves.values()])
        avg_lsf_windowed = self._average_curve(
            [curve["lsf_windowed"] for curve in group_curves.values()]
        )

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
            edge_warnings=edge_warnings,
            curve_warnings=curve_warnings,
            mtf_peak_raw=mtf_peak_raw,
        )
        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)

        if self.config.debug_export_dir:
            export_debug(
                config=self.config,
                esf=avg_esf,
                lsf=avg_lsf,
                lsf_windowed=avg_lsf_windowed,
                frequencies=frequencies,
                mtf_raw=mtf_raw,
                mtf_used=mtf_used,
                mtf_ideal=mtf_ideal,
                debug_label=debug_label,
                esf_raw=avg_esf_raw if avg_esf_raw.size > 0 else None,
                roi_img=roi_img,
                edge_line=edge_line,
                mtf_raw_alt=mtf_raw_alt if mtf_raw_alt.size > 0 else None,
                mtf_used_alt=mtf_used_alt if mtf_used_alt.size > 0 else None,
                frequencies_alt=frequencies_alt if frequencies_alt.size > 0 else None,
                edge_hits=edge_hits,
                edge_validation_ok=edge_validation_ok,
                metadata=self._build_debug_metadata(
                    capture_mode="raw_green",
                    extra={
                        "roi_origin_x": analysis_origin[0],
                        "roi_origin_y": analysis_origin[1],
                        "analysis_roi_bounds": analysis_roi_bounds,
                        "edge_angle_deg": measure_angle,
                        "g1_mtf50": g1_mtf50,
                        "g2_mtf50": g2_mtf50,
                        "g1_g2_delta_pct": g1_g2_delta_pct,
                        "edge_angle_method": geometry.get("method"),
                        "edge_angle_geometric": geometry.get("geometric_measure_angle"),
                        "edge_angle_phase": geometry.get("phase_measure_angle"),
                        "edge_angle_consistency_deg": geometry.get("consistency_deg"),
                        "edge_fit_residual_px": geometry.get("fit_residual_px"),
                        "edge_support_points": geometry.get("support_points"),
                    },
                ),
                group_curves=group_curves,
            )

        return MTFResult(
            mtf50=find_mtf_frequency(frequencies, mtf_raw, 0.5),
            mtf20=find_mtf_frequency(frequencies, mtf_raw, 0.2),
            mtf10=find_mtf_frequency(frequencies, mtf_raw, 0.1),
            frequencies=frequencies,
            frequencies_alt=frequencies_alt,
            mtf_values=mtf_used,
            mtf_raw=mtf_raw,
            mtf_raw_alt=mtf_raw_alt,
            mtf_used_alt=mtf_used_alt,
            mtf_ideal=mtf_ideal,
            esf_raw=avg_esf_raw,
            esf=avg_esf,
            lsf=avg_lsf,
            lsf_windowed=avg_lsf_windowed,
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
            **self._result_diagnostics(geometry, analysis_roi_bounds),
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
        edge_warnings: list[str],
        curve_warnings: list[str],
        mtf_peak_raw: float,
    ) -> str:
        """Build a compact warning string for one final result object."""
        warning_msgs = []
        warning_msgs.extend([msg for msg in edge_warnings if msg])
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

    def _resolve_absolute_roi_origin(
        self,
        roi_bounds: Optional[Tuple[int, int, int, int]],
        roi_origin: Optional[Tuple[int, int]],
    ) -> Tuple[int, int]:
        """Resolve ROI origin relative to the full sensor image."""
        base_x = 0
        base_y = 0
        if roi_origin is not None:
            base_x = int(roi_origin[0])
            base_y = int(roi_origin[1])
        if roi_bounds is None:
            return base_x, base_y
        return base_x + int(roi_bounds[0]), base_y + int(roi_bounds[1])

    def _build_debug_metadata(
        self,
        capture_mode: str,
        extra: Optional[dict[str, object]] = None,
    ) -> dict[str, object]:
        """Combine capture metadata with optional measurement/report context."""
        metadata = {
            "capture_mode": capture_mode,
            "capture_pixel_format": self.config.capture_pixel_format,
            "capture_binning_h": self.config.capture_binning_h,
            "capture_binning_v": self.config.capture_binning_v,
            "capture_exposure_us": self.config.capture_exposure_us,
            "capture_gain": self.config.capture_gain,
            "illumination_wavelength_um": self.config.wavelength_um,
            "source_encoding": self.config.source_encoding,
        }
        for key, value in (self.config.measurement_metadata or {}).items():
            if value is None:
                continue
            if isinstance(value, str) and value == "":
                continue
            metadata[key] = value
        for key, value in (extra or {}).items():
            if value is None:
                continue
            metadata[key] = value
        return metadata

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

def compute_mtf(image: np.ndarray,
                pixel_size_um: float = 2.40,
                roi: Optional[Tuple[int, int, int, int]] = None,
                roi_origin: Optional[Tuple[int, int]] = None,
                debug_label: Optional[str] = None) -> MTFResult:
    """Convenience wrapper for MTF computation."""
    config = MTFConfig(pixel_size_um=pixel_size_um)
    analyzer = MTFAnalyzer(config)
    return analyzer.compute_mtf(
        image,
        roi=roi,
        roi_origin=roi_origin,
        debug_label=debug_label,
    )
