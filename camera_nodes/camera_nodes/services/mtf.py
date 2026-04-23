"""MTF handler for Modulation Transfer Function measurements."""

from dataclasses import dataclass
from pathlib import Path
import re
import time

import cv2
import numpy as np

from promoc_core.promoc_exceptions import ImageProcessingError
from .base import CallbackBase
from .camera_format import CameraFormatController
from .mtf_export import (
    build_context_row,
    build_edge_summary_row,
    write_context_csv,
    write_selected_edge_marker,
    write_summary_csv,
)
from ..algorithms.mtf import MTFAnalyzer, MTFConfig, MTFResult
from ..algorithms.roi_detection import RoiDetector, EdgeROI
from ..preview import raw_array_to_bgr8_preview
from promoc_core.error_handling import handle_service_errors

MTF_AVG_SAMPLES = 10
MTF_DEFAULT_PIXEL_SIZE_UM = 2.40
MTF_AUTO_ROI_EDGE_WIDTH = 60
MTF_MIN_EDGE_CONTRAST = 0.2
MTF_SAMPLE_TIMEOUT_S = 1.0
MTF_EXPORT_CONTEXT_SCALE = 1.8
MTF_EXPORT_CONTEXT_MIN_MARGIN_PX = 24

MTF_PARAM_MAP = (
    ("mtf.lsf_window_mode", "lsf_window_mode", str, True),
    ("mtf.lsf_peak_window_size", "lsf_peak_window_size", int, False),
    ("mtf.derivative_mode", "derivative_mode", str, True),
    ("mtf.apply_derivative_correction", "apply_derivative_correction", bool, False),
    ("mtf.derivative_correction_max", "derivative_correction_max", float, False),
    ("mtf.apply_angle_correction", "apply_angle_correction", bool, False),
    ("mtf.esf_smooth_mode", "esf_smooth_mode", str, True),
    ("mtf.esf_sg_window", "esf_sg_window", int, False),
    ("mtf.esf_sg_poly", "esf_sg_poly", int, False),
    ("mtf.edge_validation_mode", "edge_validation_mode", str, True),
    ("mtf.edge_validation_percentile", "edge_validation_percentile", float, False),
    ("mtf.edge_validation_min_points", "edge_validation_min_points", int, False),
    ("mtf.angle_estimation_mode", "angle_estimation_mode", str, True),
    ("mtf.angle_allow_phase_fallback", "angle_allow_phase_fallback", bool, False),
    ("mtf.angle_consistency_warn_deg", "angle_consistency_warn_deg", float, False),
    ("mtf.angle_min_support_points", "angle_min_support_points", int, False),
    ("mtf.analysis_strip_width_px", "analysis_strip_width_px", int, False),
    ("mtf.clip_to_nyquist", "clip_to_nyquist", bool, False),
    ("mtf.export_dual_curves", "export_dual_curves", bool, False),
    ("mtf.clip_max", "mtf_clip_max", float, False),
    ("mtf.warn_threshold", "mtf_warn_threshold", float, False),
)


@dataclass
class _MeasuredEdge:
    """Container for one successfully measured edge and its averaged metrics."""

    edge_label: str
    edge_roi: EdgeROI
    result: MTFResult
    valid_samples: list[MTFResult]
    avg_mtf50: float
    avg_mtf20: float
    avg_mtf10: float
    avg_angle: float
    avg_g1_mtf50: float
    avg_g2_mtf50: float
    avg_delta_pct: float


@dataclass(frozen=True)
class _MeasurementRun:
    """Bundle the resolved edge candidates and run folder context."""

    edge_rois: list[EdgeROI]
    edge_count: int
    run_timestamp: str
    run_dir: Path
    run_id: str


def apply_mtf_param_mapping(config: MTFConfig, get_param_raw) -> None:
    """Apply declarative parameter overrides to a config object."""
    for param_name, attr_name, cast, require_truthy in MTF_PARAM_MAP:
        raw = get_param_raw(param_name, None)
        if raw is None:
            continue
        if require_truthy and not raw:
            continue
        try:
            setattr(config, attr_name, cast(raw))
        except Exception:
            continue


class MTFHandler(CallbackBase):
    """Handler for MTF measurements and ROI selection."""

    def __init__(self, node, camera_driver):
        """Initialize MTF handler and shared camera format controller."""
        super().__init__(node, camera_driver)
        self._camera_format_controller = CameraFormatController(node)

    def _select_roi_interactive(self, cv_image):
        """Opens window for ROI selection."""
        display_image = cv_image.copy()
        if len(display_image.shape) == 2 and display_image.dtype != np.uint8:
            display_image = cv2.normalize(
                display_image,
                None,
                0,
                255,
                cv2.NORM_MINMAX,
            ).astype(np.uint8)
        height, width = display_image.shape[:2]
        max_height = 800
        scale_factor = 1.0

        if height > max_height:
            scale_factor = max_height / height
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            display_image = cv2.resize(display_image, (new_width, new_height))

        window_name = "Select ROI"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, display_image.shape[1], display_image.shape[0])

        roi = cv2.selectROI(
            window_name, display_image, fromCenter=False, showCrosshair=True
        )
        cv2.destroyWindow(window_name)
        cv2.waitKey(1)

        if roi == (0, 0, 0, 0):
            return None, None

        x_scaled, y_scaled, w_scaled, h_scaled = roi
        x = int(x_scaled / scale_factor)
        y = int(y_scaled / scale_factor)
        w = int(w_scaled / scale_factor)
        h = int(h_scaled / scale_factor)

        img_h, img_w = cv_image.shape[:2]
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))

        roi = (x, y, w, h)
        roi_image = cv_image[y : y + h, x : x + w]
        return roi, roi_image

    @staticmethod
    def _with_next_step(message: str, next_step: str) -> str:
        """Attach one short operator-facing next step to an error message."""
        return f"{message} Next step: {next_step}"

    def _build_mtf_config(
        self,
        pixel_size_um: float,
        min_edge_angle: float,
        max_edge_angle: float,
        auto_roi: bool,
    ) -> MTFConfig:
        """Build MTFConfig from node parameters and profile overrides."""
        config = MTFConfig(
            pixel_size_um=pixel_size_um,
            min_edge_angle=min_edge_angle,
            max_edge_angle=max_edge_angle,
        )

        # Debug export
        debug_dir = self._param_str("mtf.debug_export_dir", "").strip()
        if debug_dir:
            config.debug_export_dir = debug_dir
            prefix = self._param_str("mtf.debug_export_prefix", "").strip()
            if prefix:
                config.debug_export_prefix = prefix
            if self._param_raw("mtf.debug_export_csv", None) is not None:
                config.debug_export_csv = self._param_bool(
                    "mtf.debug_export_csv", config.debug_export_csv
                )
            if self._param_raw("mtf.debug_export_png", None) is not None:
                config.debug_export_png = self._param_bool(
                    "mtf.debug_export_png", config.debug_export_png
                )

        # Centralized declarative parameter mapping
        apply_mtf_param_mapping(config, self._param_raw)

        # Validation-only switch for auto ROI mode
        if self._param_bool("mtf.edge_validation_only_auto", False) and not auto_roi:
            config.edge_validation_mode = "off"

        config.input_mode = (
            "raw_bayer_rggb"
            if self._param_bool("mtf.use_raw_capture", True)
            else "dense_gray"
        )
        config.raw_bayer_pattern = self._param_str(
            "mtf.capture_bayer_pattern",
            "RGGB",
        ).strip().upper()
        config.capture_pixel_format = self._param_str(
            "mtf.capture_pixel_format",
            "BayerRG12",
        ).strip()
        config.capture_binning_h = self._param_int("mtf.capture_binning", 1)
        config.capture_binning_v = self._param_int("mtf.capture_binning", 1)
        config.capture_exposure_us = self._param_float("mtf.capture_exposure_us", 0.0)
        config.capture_gain = self._param_float("mtf.capture_gain", 0.0)
        config.source_encoding = self._param_str("mtf.capture_pixel_format", "").strip()
        config.raw_green_pair_warn_pct = self._param_float(
            "mtf.raw_green_pair_warn_pct",
            config.raw_green_pair_warn_pct,
        )
        green_wavelength = self._param_float("mtf.green_wavelength_um", config.wavelength_um)
        if green_wavelength > 0:
            config.wavelength_um = green_wavelength

        # Apply profile last (overrides for ease-of-use)
        profile = self._param_str("mtf.profile", "default").strip().lower()
        if profile in ("scientific", "debug"):
            config.derivative_mode = "iso"
            config.apply_derivative_correction = True
            config.apply_angle_correction = True
            config.clip_to_nyquist = True
            config.lsf_window_mode = "peak"
            config.lsf_peak_window_size = 0
            config.edge_validation_mode = "warn"
        if profile == "debug":
            if not config.debug_export_dir:
                debug_root = self._get_output_dir("mtf_debug")
                run_dir = debug_root / self._get_timestamp()
                run_dir.mkdir(parents=True, exist_ok=True)
                config.debug_export_dir = str(run_dir)
            config.debug_export_csv = True
            config.debug_export_png = True
            if config.esf_smooth_mode == "none":
                config.esf_smooth_mode = "sg"
            config.export_dual_curves = True
        if profile not in ("default", "scientific", "debug", ""):
            self._node.get_logger().warn(
                f"Unknown mtf.profile='{profile}', using current configuration."
            )

        return config

    def _is_raw_bayer_encoding(self, encoding: str) -> bool:
        """Return whether a ROS image encoding looks like a Bayer/raw stream."""
        normalized = str(encoding or "").strip().lower()
        return "bayer" in normalized

    def _get_mtf_capture_image(self):
        """Get the latest image in the format required for scientific MTF."""
        if self._param_bool("mtf.use_raw_capture", True):
            return self._get_latest_passthrough_image()
        image, ts = self._get_latest_cv_image()
        return image, ts, "bgr8"

    def _wait_for_new_mtf_capture_image(self, last_timestamp: int, timeout: float = 1.0):
        """Wait for the next image in the format required for scientific MTF."""
        if self._param_bool("mtf.use_raw_capture", True):
            return self._wait_for_new_passthrough_image(last_timestamp, timeout=timeout)
        image, ts = self._wait_for_new_image(last_timestamp, timeout=timeout)
        return image, ts, "bgr8"

    def _current_stream_geometry(
        self,
        image: np.ndarray | None = None,
    ) -> tuple[int, int]:
        """Return current stream width/height from the live message or image."""
        msg = getattr(self._node, "latest_image_msg", None)
        if msg is not None:
            width = int(getattr(msg, "width", 0) or 0)
            height = int(getattr(msg, "height", 0) or 0)
            if width > 0 and height > 0:
                return width, height
        if image is not None:
            height, width = image.shape[:2]
            return int(width), int(height)
        return 0, 0

    def _annotate_capture_geometry(
        self,
        capture_values: dict[str, object],
        image: np.ndarray | None,
    ) -> dict[str, object]:
        """Attach actual/requested stream geometry to capture metadata."""
        stream_width, stream_height = self._current_stream_geometry(image)
        requested_width = self._param_int(
            "mtf.capture_width",
            self._param_int("camera.expected_width", 0),
        )
        requested_height = self._param_int(
            "mtf.capture_height",
            self._param_int("camera.expected_height", 0),
        )
        annotated = dict(capture_values or {})
        annotated["stream_width_px"] = int(stream_width)
        annotated["stream_height_px"] = int(stream_height)
        annotated["requested_stream_width_px"] = int(requested_width)
        annotated["requested_stream_height_px"] = int(requested_height)
        annotated["stream_geometry_matches_request"] = bool(
            stream_width > 0
            and stream_height > 0
            and requested_width > 0
            and requested_height > 0
            and stream_width == requested_width
            and stream_height == requested_height
        )
        return annotated

    def _wait_for_scientific_capture_frame(
        self,
        last_timestamp: int,
    ) -> tuple[np.ndarray | None, int | None, str]:
        """Wait for the next post-switch capture frame, preferring raw Bayer."""
        latest_image, latest_ts, latest_encoding = self._get_mtf_capture_image()
        if latest_image is not None and self._is_raw_bayer_encoding(latest_encoding):
            return latest_image, latest_ts, latest_encoding

        timeout_s = self._param_float("mtf.capture_image_timeout_s", 2.0)
        deadline = time.time() + max(0.1, float(timeout_s))
        current_ts = int(last_timestamp or 0)
        while time.time() < deadline:
            remaining = max(0.05, deadline - time.time())
            image, image_ts, encoding = self._wait_for_new_mtf_capture_image(
                current_ts,
                timeout=min(0.4, remaining),
            )
            if image is None:
                break
            latest_image, latest_ts, latest_encoding = image, image_ts, encoding
            if image_ts is not None:
                current_ts = int(image_ts)
            if self._is_raw_bayer_encoding(encoding):
                return latest_image, latest_ts, latest_encoding
        return latest_image, latest_ts, latest_encoding

    def _acquire_measurement_frame(self) -> tuple[np.ndarray, int | None, str, object | None]:
        """Fetch the current measurement frame after the optional MTF camera switch."""
        cv_image, image_ts_ns, image_encoding = self._get_mtf_capture_image()
        if cv_image is None:
            raise ImageProcessingError(
                self._with_next_step(
                    "No camera image available for MTF.",
                    f"check {self._camera_image_topic()} in rqt_image_view and retry.",
                )
            )

        live_geometry = self._current_stream_geometry(cv_image)
        restore_state, switched_image = self._camera_format_controller.switch_to_full_frame_for_mtf(
            image_ts_ns if image_ts_ns is not None else 0,
            get_latest_image_fn=self._get_mtf_capture_image,
            wait_for_new_image_fn=self._wait_for_new_mtf_capture_image,
            live_geometry=live_geometry,
            live_encoding=image_encoding,
        )
        if switched_image is not None:
            cv_image = switched_image

        capture_image, capture_ts_ns, capture_encoding = self._wait_for_scientific_capture_frame(
            image_ts_ns if image_ts_ns is not None else 0
        )
        if capture_image is None:
            capture_image, capture_ts_ns, capture_encoding = self._get_mtf_capture_image()
        if capture_image is not None:
            cv_image = capture_image
            image_ts_ns = capture_ts_ns
            image_encoding = capture_encoding
        return cv_image, image_ts_ns, image_encoding, restore_state

    def _read_capture_state(self) -> tuple[dict[str, object], list[str]]:
        """Read the latest camera state snapshot used for scientific validation."""
        capture_state = (
            self._camera_format_controller.get_last_capture_state()
            or self._camera_format_controller.read_capture_state()
            or {}
        )
        capture_values = dict((capture_state or {}).get("values", {}))
        capture_available_keys = list((capture_state or {}).get("available_keys", []))
        return capture_state, capture_values, capture_available_keys

    def _prepare_measurement_metadata(
        self,
        request,
    ) -> tuple[float, dict[str, object]]:
        """Resolve request metadata once before ROI selection and export writing."""
        # We resolve request metadata exactly once so the analyzer config, logs,
        # and exported CSV context all describe the same measurement conditions.
        pixel_size_um = self._resolve_pixel_size_um(request)
        measurement_metadata = self._collect_measurement_metadata(request, pixel_size_um)
        measurement_context = self._format_measurement_metadata(measurement_metadata)
        if measurement_context:
            self._node.get_logger().info(f"MTF measurement context: {measurement_context}")
        return pixel_size_um, measurement_metadata

    def _validate_capture_or_write_failure(
        self,
        *,
        request,
        measurement_metadata: dict[str, object],
        capture_state: dict[str, object],
        capture_values: dict[str, object],
        capture_available_keys: list[str],
        image_encoding: str,
    ) -> tuple[dict[str, object], str, list[str]]:
        """Validate the scientific raw capture state and preserve failed runs on disk."""
        try:
            return self._validate_scientific_capture_state(
                capture_state,
                image_encoding,
            )
        except ImageProcessingError as exc:
            capture_error = str(exc)
            capture_mismatches = []
            mismatch_prefix = "Scientific MTF capture readback mismatch: "
            if capture_error.startswith(mismatch_prefix):
                capture_mismatches = [
                    item.strip()
                    for item in capture_error[len(mismatch_prefix) :].split(",")
                    if item.strip()
                ]
            # Even a failed scientific capture should leave a traceable run
            # folder so later comparisons can exclude misconfigured attempts.
            summary_csv, context_csv = self._write_failed_measurement_run(
                request=request,
                measurement_metadata=measurement_metadata,
                capture_values=capture_values,
                capture_available_keys=capture_available_keys,
                capture_mismatches=capture_mismatches,
                image_encoding=image_encoding,
                measurement_error=capture_error,
            )
            self._node.get_logger().error(
                f"MTF capture validation failed: {capture_error}. "
                f"summary={summary_csv}, context={context_csv}"
            )
            raise

    def _prepare_measurement_run(
        self,
        cv_image: np.ndarray,
        request,
    ) -> _MeasurementRun:
        """Resolve ROI candidates and create the run folder used for all exports."""
        # Auto-ROI and manual ROI intentionally converge here so everything
        # after this point uses the same edge-measurement and export pipeline.
        edge_rois = self._resolve_edge_rois(cv_image, request)
        edge_count = len(edge_rois)
        run_timestamp = self._get_timestamp()
        run_dir, run_id = self._build_measurement_run_context(
            request,
            edge_rois,
            timestamp=run_timestamp,
        )
        return _MeasurementRun(
            edge_rois=edge_rois,
            edge_count=edge_count,
            run_timestamp=run_timestamp,
            run_dir=run_dir,
            run_id=run_id,
        )

    def _measure_run_edges(
        self,
        *,
        measurement_run: _MeasurementRun,
        request,
        measurement_metadata: dict[str, object],
        pixel_size_um: float,
        min_edge_angle: float,
        max_edge_angle: float,
        capture_values: dict[str, object],
        actual_pixel_format: str,
        image_encoding: str,
    ) -> tuple[list[dict[str, object]], list[_MeasuredEdge], _MeasuredEdge | None, str]:
        """Measure each candidate edge through the shared analyzer and averaging path."""
        edge_rows: list[dict[str, object]] = []
        measured_edges: list[_MeasuredEdge] = []
        selected_edge: _MeasuredEdge | None = None
        last_error = "Unknown error"

        for edge_index, edge_roi in enumerate(measurement_run.edge_rois):
            # The first valid edge wins the ROS response, but we still measure
            # every candidate so the run folder stays complete for later review.
            row, measured_edge, edge_error = self._measure_edge_candidate(
                edge_roi=edge_roi,
                edge_index=edge_index,
                edge_count=measurement_run.edge_count,
                run_dir=measurement_run.run_dir,
                run_id=measurement_run.run_id,
                request=request,
                measurement_metadata=measurement_metadata,
                pixel_size_um=pixel_size_um,
                min_edge_angle=min_edge_angle,
                max_edge_angle=max_edge_angle,
                capture_values=capture_values,
                actual_pixel_format=actual_pixel_format,
                image_encoding=image_encoding,
            )
            edge_rows.append(row)
            if measured_edge is not None:
                measured_edges.append(measured_edge)
                if selected_edge is None:
                    selected_edge = measured_edge
            if edge_error:
                last_error = edge_error

        if selected_edge is not None:
            for row in edge_rows:
                row["selected_for_response"] = int(
                    row["edge_label"] == selected_edge.edge_label
                )
        self._log_measurement_run_summary(edge_rows, selected_edge)
        return edge_rows, measured_edges, selected_edge, last_error

    def _log_measurement_run_summary(
        self,
        edge_rows: list[dict[str, object]],
        selected_edge: _MeasuredEdge | None,
    ) -> None:
        """Write one compact per-run summary after all edges have been evaluated."""
        valid_edge_count = sum(int(bool(row["valid"])) for row in edge_rows)
        if selected_edge is None:
            self._node.get_logger().info(
                f"MTF run summary: valid_edges={valid_edge_count}/{len(edge_rows)}, selected=none"
            )
            return

        self._node.get_logger().info(
            "MTF run summary: "
            f"valid_edges={valid_edge_count}/{len(edge_rows)}, "
            f"selected={selected_edge.edge_label}, "
            f"MTF50={selected_edge.avg_mtf50:.2f} lp/mm, "
            f"angle={selected_edge.avg_angle:.2f} deg"
        )

    def _write_measurement_exports(
        self,
        *,
        measurement_run: _MeasurementRun,
        source_image: np.ndarray,
        request,
        measurement_metadata: dict[str, object],
        capture_values: dict[str, object],
        capture_available_keys: list[str],
        capture_mismatches: list[str],
        image_encoding: str,
        edge_rows: list[dict[str, object]],
        measured_edges: list[_MeasuredEdge],
        selected_edge: _MeasuredEdge | None,
        last_error: str,
    ) -> tuple[Path, Path]:
        """Write per-edge and per-run artifacts after edge measurement finishes."""
        # The export step happens before we decide success/failure so even
        # failed runs keep their summary/context for later debugging.
        valid_edge_count = sum(int(bool(row["valid"])) for row in edge_rows)
        summary_csv = write_summary_csv(measurement_run.run_dir, edge_rows)
        context_csv = write_context_csv(
            measurement_run.run_dir,
            build_context_row(
                run_id=measurement_run.run_id,
                timestamp=measurement_run.run_timestamp,
                measurement_metadata=measurement_metadata,
                roi_mode=self._roi_mode_label(request, measurement_run.edge_count),
                focus_position_mm=self._focus_position_mm(),
                capture_values=capture_values,
                capture_available_keys=capture_available_keys,
                capture_readback_mismatches=capture_mismatches,
                capture_readback_ok=not capture_mismatches,
                image_encoding=image_encoding,
                edge_count=measurement_run.edge_count,
                valid_edge_count=valid_edge_count,
                selected_edge_label=selected_edge.edge_label if selected_edge else "",
                selected_result=selected_edge.result if selected_edge else None,
                selected_edge_angle_deg=(
                    selected_edge.avg_angle if selected_edge is not None else None
                ),
                selected_sample_count=(
                    len(selected_edge.valid_samples) if selected_edge is not None else 0
                ),
                measurement_success=selected_edge is not None,
                measurement_error="" if selected_edge is not None else last_error,
            ),
        )
        self._write_visual_measurement_exports(
            run_dir=measurement_run.run_dir,
            source_image=source_image,
            image_encoding=image_encoding,
            edge_rows=edge_rows,
            measured_edges=measured_edges,
            selected_edge=selected_edge,
        )
        self._node.get_logger().info(
            f"MTF export written: summary={summary_csv}, context={context_csv}"
        )
        return summary_csv, context_csv

    def _preview_image_for_export(
        self,
        image: np.ndarray | None,
        image_encoding: str,
    ) -> np.ndarray | None:
        """Convert the current measurement image into a drawable preview for exports."""
        if image is None or getattr(image, "size", 0) == 0:
            return None

        try:
            if (
                self._is_raw_bayer_encoding(image_encoding)
                or image.dtype != np.uint8
                or len(image.shape) == 2
            ):
                return raw_array_to_bgr8_preview(image, image_encoding)
            if len(image.shape) == 3:
                return image.copy()
        except Exception:
            pass

        try:
            if len(image.shape) == 2:
                normalized = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
                gray_u8 = normalized.astype(np.uint8)
                return cv2.cvtColor(gray_u8, cv2.COLOR_GRAY2BGR)
        except Exception:
            pass
        return None

    @staticmethod
    def _expanded_context_bbox(
        image_shape: tuple[int, ...],
        bbox: tuple[int, int, int, int],
        *,
        scale: float = MTF_EXPORT_CONTEXT_SCALE,
        min_margin_px: int = MTF_EXPORT_CONTEXT_MIN_MARGIN_PX,
    ) -> tuple[int, int, int, int]:
        """Expand one ROI bbox so exports keep more visual context around the edge."""
        img_h, img_w = image_shape[:2]
        x, y, w, h = [int(value) for value in bbox]
        margin_x = max(int(round(w * max(0.0, scale - 1.0) * 0.5)), int(min_margin_px))
        margin_y = max(int(round(h * max(0.0, scale - 1.0) * 0.5)), int(min_margin_px))
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(img_w, x + w + margin_x)
        y2 = min(img_h, y + h + margin_y)
        return x1, y1, max(1, x2 - x1), max(1, y2 - y1)

    @staticmethod
    def _draw_export_box(
        image: np.ndarray,
        bbox: tuple[int, int, int, int],
        color: tuple[int, int, int],
        *,
        label: str = "",
        thickness: int = 2,
    ) -> None:
        """Draw one labeled export rectangle if OpenCV drawing helpers are available."""
        if not hasattr(cv2, "rectangle"):
            return
        x, y, w, h = [int(value) for value in bbox]
        cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness, cv2.LINE_AA)
        if not label or not hasattr(cv2, "putText"):
            return
        text_y = max(16, y - 6)
        cv2.putText(
            image,
            label,
            (x + 2, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            label,
            (x + 2, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    def _write_visual_measurement_exports(
        self,
        *,
        run_dir: Path,
        source_image: np.ndarray,
        image_encoding: str,
        edge_rows: list[dict[str, object]],
        measured_edges: list[_MeasuredEdge],
        selected_edge: _MeasuredEdge | None,
    ) -> None:
        """Write one run overview and overwrite per-edge ROI images with larger context crops."""
        if not hasattr(cv2, "imwrite"):
            return

        preview_image = self._preview_image_for_export(source_image, image_encoding)
        if preview_image is None:
            return

        measured_by_label = {edge.edge_label: edge for edge in measured_edges}
        selected_label = selected_edge.edge_label if selected_edge is not None else ""

        overview = preview_image.copy()
        for row in edge_rows:
            edge_label = str(row.get("edge_label", "") or "")
            bbox = (
                int(row.get("roi_bbox_x", 0) or 0),
                int(row.get("roi_bbox_y", 0) or 0),
                int(row.get("roi_bbox_w", 0) or 0),
                int(row.get("roi_bbox_h", 0) or 0),
            )
            is_valid = bool(row.get("valid", 0))
            is_selected = edge_label == selected_label
            color = (0, 220, 0) if is_selected else ((0, 215, 255) if is_valid else (0, 0, 255))
            stats = ""
            if is_valid:
                stats = (
                    f" MTF50={float(row.get('mtf50_lpmm', 0.0) or 0.0):.1f}"
                    f" angle={float(row.get('edge_angle_deg', 0.0) or 0.0):.1f}"
                )
            self._draw_export_box(
                overview,
                bbox,
                color,
                label=f"{edge_label}{'*' if is_selected else ''}{stats}",
            )

            context_bbox = self._expanded_context_bbox(preview_image.shape, bbox)
            cx, cy, cw, ch = context_bbox
            roi_vis = preview_image[cy : cy + ch, cx : cx + cw].copy()
            local_bbox = (bbox[0] - cx, bbox[1] - cy, bbox[2], bbox[3])
            self._draw_export_box(
                roi_vis,
                local_bbox,
                color,
                label=f"{edge_label}{'*' if is_selected else ''}",
            )

            measured_edge = measured_by_label.get(edge_label)
            if measured_edge is not None and measured_edge.result.analysis_roi_bounds:
                if hasattr(cv2, "putText"):
                    info_text = (
                        f"MTF50={measured_edge.avg_mtf50:.2f} lp/mm  "
                        f"angle={measured_edge.avg_angle:.2f} deg"
                    )
                    cv2.putText(
                        roi_vis,
                        info_text,
                        (8, max(20, ch - 12)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.48,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        roi_vis,
                        info_text,
                        (8, max(20, ch - 12)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.48,
                        color,
                        1,
                        cv2.LINE_AA,
                    )

            cv2.imwrite(str(run_dir / f"{self._slugify_label(edge_label)}_roi.png"), roi_vis)

        cv2.imwrite(str(run_dir / "edges_overview.png"), overview)

    def _finalize_measurement_response(
        self,
        *,
        response,
        measurement_run: _MeasurementRun,
        selected_edge: _MeasuredEdge | None,
        edge_rows: list[dict[str, object]],
        summary_csv: Path,
        last_error: str,
    ):
        """Return the selected edge response or fail with the preserved run artifacts."""
        if selected_edge is None:
            raise ImageProcessingError(
                self._with_next_step(
                    f"MTF failed on all candidate edges. Last error: {last_error}. Summary: {summary_csv}",
                    "refocus, tighten the ROI, or switch between auto and manual ROI before retrying.",
                )
            )

        write_selected_edge_marker(measurement_run.run_dir, selected_edge.edge_label)
        return self._populate_success_response(
            response,
            selected_edge,
            edge_rows,
            summary_csv,
        )

    def _build_capture_summary(self, result) -> str:
        """Format compact capture metadata for logs and service status."""
        parts = [
            f"mode={result.capture_mode or 'dense_gray'}",
            f"pixfmt={result.capture_pixel_format or 'n/a'}",
        ]
        if result.capture_binning_h > 0 and result.capture_binning_v > 0:
            parts.append(f"bin={result.capture_binning_h}x{result.capture_binning_v}")
        if result.capture_exposure_us > 0:
            parts.append(f"exp_us={result.capture_exposure_us:.1f}")
        parts.append(f"gain={result.capture_gain:.2f}")
        if result.illumination_wavelength_um > 0:
            parts.append(f"lambda_um={result.illumination_wavelength_um:.3f}")
        if result.capture_mode == "raw_green":
            parts.append(f"G1={result.g1_mtf50:.2f}")
            parts.append(f"G2={result.g2_mtf50:.2f}")
            parts.append(f"delta={result.g1_g2_delta_pct:.1f}%")
        return ", ".join(parts)

    def _resolve_pixel_size_um(self, request) -> float:
        """Use request pixel size when positive, otherwise fall back to the node param."""
        try:
            request_pixel_size_um = float(getattr(request, "pixel_size_um", 0.0))
        except (TypeError, ValueError):
            request_pixel_size_um = 0.0
        if request_pixel_size_um > 0:
            return request_pixel_size_um

        pixel_size_um = self._param_float("pixel_size_um", MTF_DEFAULT_PIXEL_SIZE_UM)
        if pixel_size_um <= 0:
            return MTF_DEFAULT_PIXEL_SIZE_UM
        return pixel_size_um

    @staticmethod
    def _parse_objective_magnification_x(objective: str) -> float:
        """Extract a numeric magnification from free-text objective labels."""
        text = str(objective or "").strip().lower()
        if not text:
            return 0.0
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*x", text)
        if not match:
            match = re.search(r"(\d+(?:[.,]\d+)?)", text)
        if not match:
            return 0.0
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            return 0.0

    def _collect_measurement_metadata(self, request, pixel_size_um: float) -> dict[str, object]:
        """Collect request metadata for logs and optional debug export."""
        try:
            request_pixel_size_um = float(getattr(request, "pixel_size_um", 0.0))
        except (TypeError, ValueError):
            request_pixel_size_um = 0.0
        camera_objective = str(getattr(request, "camera_objective", "") or "").strip()
        if not camera_objective:
            camera_objective = self._param_str(
                "measurement_conditions.camera_objective",
                "unknown",
            ).strip() or "unknown"

        try:
            objective_magnification_x = float(getattr(request, "objective_magnification_x", 0.0))
        except (TypeError, ValueError):
            objective_magnification_x = 0.0
        if objective_magnification_x <= 0:
            objective_magnification_x = self._parse_objective_magnification_x(camera_objective)

        try:
            coaxial_light_voltage = float(getattr(request, "coaxial_light_voltage", 0.0))
        except (TypeError, ValueError):
            coaxial_light_voltage = 0.0
        if coaxial_light_voltage <= 0:
            coaxial_light_voltage = self._param_float(
                "measurement_conditions.coaxial_light_voltage",
                0.0,
            )

        try:
            coaxial_light_current = float(getattr(request, "coaxial_light_current", 0.0))
        except (TypeError, ValueError):
            coaxial_light_current = 0.0
        if coaxial_light_current <= 0:
            coaxial_light_current = self._param_float(
                "measurement_conditions.coaxial_light_current",
                0.0,
            )

        notes = str(getattr(request, "notes", "") or "").strip()
        if not notes:
            notes = self._param_str("measurement_conditions.notes", "").strip()

        metadata = {
            "measurement_operator": self._param_str(
                "measurement.username",
                "default_user",
            ).strip()
            or "default_user",
            "effective_pixel_size_um": float(pixel_size_um),
            "request_pixel_size_um": float(request_pixel_size_um),
            "pixel_size_source": "request" if request_pixel_size_um > 0 else "node_parameter",
            "auto_roi": bool(getattr(request, "auto_roi", False)),
            "target_edge": str(getattr(request, "target_edge", "") or "").strip(),
            "camera_objective": camera_objective,
            "objective_magnification_x": objective_magnification_x,
            "use_beamsplitter": bool(getattr(request, "use_beamsplitter", False)),
            "coaxial_light_voltage": coaxial_light_voltage,
            "coaxial_light_current": coaxial_light_current,
            "notes": notes,
        }
        return {
            key: value
            for key, value in metadata.items()
            if value is not None and not (isinstance(value, str) and value == "")
        }

    def _format_measurement_metadata(self, metadata: dict[str, object]) -> str:
        """Create a compact log line from request metadata."""
        if not metadata:
            return ""

        parts = [f"pixel_um={float(metadata['effective_pixel_size_um']):.4f}"]
        if metadata.get("pixel_size_source") == "request":
            parts.append("pixel_source=request")
        objective = metadata.get("camera_objective")
        if objective:
            parts.append(f"objective={objective}")
        magnification = float(metadata.get("objective_magnification_x", 0.0) or 0.0)
        if magnification > 0:
            parts.append(f"mag={magnification:.2f}x")
        if metadata.get("use_beamsplitter"):
            parts.append("beamsplitter=yes")
        coaxial_voltage = float(metadata.get("coaxial_light_voltage", 0.0) or 0.0)
        if coaxial_voltage > 0:
            parts.append(f"coaxV={coaxial_voltage:.3f}")
        coaxial_current = float(metadata.get("coaxial_light_current", 0.0) or 0.0)
        if coaxial_current > 0:
            parts.append(f"coaxI={coaxial_current:.3f}")
        if metadata.get("auto_roi"):
            parts.append("auto_roi=yes")
        target_edge = metadata.get("target_edge")
        if target_edge:
            parts.append(f"target_edge={target_edge}")
        notes = str(metadata.get("notes", "") or "").strip()
        if notes:
            parts.append(f"notes={notes[:60]}")
        return ", ".join(parts)

    def _slugify_label(self, value: object, fallback: str = "item") -> str:
        """Create a filesystem-safe label component."""
        text = str(value or "").strip()
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._-")
        return safe or fallback

    def _build_measurement_run_context(
        self,
        request,
        edge_rois: list[EdgeROI],
        timestamp: str | None = None,
    ) -> tuple[Path, str]:
        """Create one predictable run folder for a single service call."""
        timestamp = timestamp or self._get_timestamp()
        auto_roi = bool(getattr(request, "auto_roi", False))
        if auto_roi and len(edge_rois) >= 4:
            mode_label = "square4"
        elif auto_roi:
            mode_label = "auto"
        else:
            mode_label = "manual"
        requested_edge = str(getattr(request, "target_edge", "") or "").strip().lower()
        requested_label = ""
        if requested_edge and requested_edge not in {"any", "select", "interactive"}:
            requested_label = self._slugify_label(requested_edge, fallback="")
        run_parts = ["mtf", mode_label, timestamp]
        if requested_label:
            run_parts.append(requested_label)
        run_id = "_".join(part for part in run_parts if part)
        run_dir = self._get_output_dir("mtf_messungen") / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir, run_id

    def _build_edge_export_label(
        self,
        edge_roi: EdgeROI,
        edge_index: int,
        edge_count: int,
    ) -> str:
        """Build a deterministic per-edge label for debug exports."""
        edge_name = self._slugify_label(
            edge_roi.edge_name,
            fallback=f"edge_{edge_index + 1:02d}",
        )
        if edge_count <= 1:
            return edge_name
        return f"{edge_index + 1:02d}_{edge_name}"

    def _build_edge_measurement_metadata(
        self,
        base_metadata: dict[str, object],
        edge_roi: EdgeROI,
        edge_label: str,
        edge_index: int,
        edge_count: int,
        run_id: str,
    ) -> dict[str, object]:
        """Attach per-edge traceability metadata for exports and logs."""
        x, y, w, h = edge_roi.bbox
        metadata = dict(base_metadata)
        metadata.update(
            {
                "run_id": run_id,
                "edge_label": edge_label,
                "edge_name": edge_roi.edge_name,
                "edge_direction": edge_roi.edge_direction,
                "edge_index": edge_index + 1,
                "edge_count": edge_count,
                "edge_contrast": float(edge_roi.contrast),
                "roi_bbox_x": int(x),
                "roi_bbox_y": int(y),
                "roi_bbox_w": int(w),
                "roi_bbox_h": int(h),
                "parent_center_x": int(edge_roi.parent_center[0]),
                "parent_center_y": int(edge_roi.parent_center[1]),
            }
        )
        return metadata

    def _get_camera_calibration(self) -> tuple[np.ndarray | None, np.ndarray | None]:
        """Return camera calibration arrays when CameraInfo is available."""
        if self._node.latest_camera_info is None:
            return None, None
        try:
            camera_info = self._node.latest_camera_info
            return np.array(camera_info.k).reshape(3, 3), np.array(camera_info.d)
        except Exception as exc:
            self._node.get_logger().warn(f"Failed to process camera info: {exc}")
            return None, None

    def _detect_auto_edge_rois(self, cv_image: np.ndarray) -> list[EdgeROI]:
        """Detect square/bar targets and return candidate edge ROIs."""
        self._node.get_logger().info("Auto-ROI enabled: Detecting targets...")
        _, bars, squares = RoiDetector.detect_targets(cv_image)

        if squares:
            largest_square = max(squares, key=lambda rect: rect[1][0] * rect[1][1])
            edge_rois = RoiDetector.create_edge_rois_from_rect(
                cv_image,
                largest_square,
                roi_width=MTF_AUTO_ROI_EDGE_WIDTH,
            )
            valid_edges = [edge for edge in edge_rois if edge.is_valid]
            if valid_edges:
                self._node.get_logger().info(
                    f"Found {len(valid_edges)} valid edges from square "
                    f"(center: {valid_edges[0].parent_center})"
                )
                return valid_edges
            if edge_rois:
                self._node.get_logger().warn(
                    f"All {len(edge_rois)} square edges have low contrast, trying anyway..."
                )
                return edge_rois

        if bars:
            largest_bar = max(bars, key=lambda rect: rect[1][0] * rect[1][1])
            edge_rois = RoiDetector.create_edge_rois_from_rect(
                cv_image,
                largest_bar,
                roi_width=MTF_AUTO_ROI_EDGE_WIDTH,
            )
            if edge_rois:
                self._node.get_logger().info(
                    f"Found {len(edge_rois)} edges from bar target"
                )
                return edge_rois

        raise ImageProcessingError(
            self._with_next_step(
                "Auto-ROI found no square or bar target.",
                "align the target more centrally or retry with auto_roi=false for manual ROI.",
            )
        )

    def _build_manual_edge_roi(self, cv_image: np.ndarray) -> list[EdgeROI]:
        """Collect one manual ROI and wrap it in the shared EdgeROI structure."""
        roi, roi_img = self._select_roi_interactive(cv_image)
        if roi is None:
            raise ImageProcessingError(
                self._with_next_step(
                    "Manual ROI selection was cancelled.",
                    "draw one ROI around a clean slanted edge and retry the measurement.",
                )
            )

        x, y, w, h = roi
        contrast = RoiDetector.calculate_michelson_contrast(roi_img)
        return [
            EdgeROI(
                image=roi_img,
                bbox=(x, y, w, h),
                edge_direction="unknown",
                edge_name="manual",
                contrast=contrast,
                parent_center=(x + w // 2, y + h // 2),
            )
        ]

    def _apply_requested_edge_selection(
        self,
        edge_rois: list[EdgeROI],
        request,
    ) -> list[EdgeROI]:
        """Filter or interactively select candidate edges according to the request."""
        requested = str(getattr(request, "target_edge", "") or "").strip().lower()
        if requested in {"", "any"}:
            return edge_rois

        if requested in {"select", "interactive"}:
            candidates = [
                {
                    "image": edge_roi.image,
                    "name": f"{edge_roi.edge_name.capitalize()} Edge",
                    "edge_roi": edge_roi,
                }
                for edge_roi in edge_rois
            ]
            selected = self._select_candidate_interactive(candidates)
            if selected and "edge_roi" in selected:
                self._node.get_logger().info(f"User selected: {selected['name']}")
                return [selected["edge_roi"]]
            raise ImageProcessingError(
                self._with_next_step(
                    "Interactive edge selection was cancelled.",
                    "choose one detected edge or use target_edge='any' and retry.",
                )
            )

        filtered = [
            edge_roi for edge_roi in edge_rois if requested in edge_roi.edge_name.lower()
        ]
        if filtered:
            self._node.get_logger().info(
                f"Filtered to '{requested}' edges: {len(filtered)} candidates"
            )
            return filtered

        raise ImageProcessingError(
            self._with_next_step(
                f"Requested edge '{requested}' was not found in the detected targets.",
                "use target_edge='any' or pick one of top/right/bottom/left.",
            )
        )

    def _resolve_edge_rois(self, cv_image: np.ndarray, request) -> list[EdgeROI]:
        """Resolve auto/manual ROI selection into one shared candidate list."""
        edge_rois = (
            self._detect_auto_edge_rois(cv_image)
            if bool(getattr(request, "auto_roi", False))
            else self._build_manual_edge_roi(cv_image)
        )
        return self._apply_requested_edge_selection(edge_rois, request)

    def _prepare_edge_config(
        self,
        *,
        pixel_size_um: float,
        min_edge_angle: float,
        max_edge_angle: float,
        auto_roi: bool,
        run_dir: Path,
        run_id: str,
        edge_roi: EdgeROI,
        edge_label: str,
        edge_index: int,
        edge_count: int,
        measurement_metadata: dict[str, object],
        capture_values: dict[str, object],
        actual_pixel_format: str,
        image_encoding: str,
    ) -> MTFConfig:
        """Build one analyzer config for a concrete edge measurement."""
        config = self._build_mtf_config(
            pixel_size_um=pixel_size_um,
            min_edge_angle=min_edge_angle,
            max_edge_angle=max_edge_angle,
            auto_roi=auto_roi,
        )
        config.debug_export_dir = str(run_dir)
        config.debug_export_csv = True
        config.debug_export_png = True
        config.debug_export_prefix = self._slugify_label(
            run_id,
            fallback=config.debug_export_prefix,
        )
        config.measurement_metadata = self._build_edge_measurement_metadata(
            measurement_metadata,
            edge_roi,
            edge_label,
            edge_index,
            edge_count,
            run_id,
        )
        config.capture_pixel_format = actual_pixel_format or config.capture_pixel_format
        config.capture_binning_h = int(capture_values.get("bin_h", config.capture_binning_h))
        config.capture_binning_v = int(capture_values.get("bin_v", config.capture_binning_v))
        try:
            config.capture_exposure_us = float(
                capture_values.get("exposure_time", config.capture_exposure_us)
            )
        except (TypeError, ValueError):
            pass
        try:
            config.capture_gain = float(capture_values.get("gain", config.capture_gain))
        except (TypeError, ValueError):
            pass
        config.source_encoding = image_encoding or config.source_encoding
        return config

    def _measure_average_samples(
        self,
        analyzer: MTFAnalyzer,
        edge_roi: EdgeROI,
        first_result: MTFResult,
    ) -> list[MTFResult]:
        """Keep the first exported result and average later frames numerically."""
        valid_samples = [first_result]
        if MTF_AVG_SAMPLES <= 1:
            return valid_samples

        analyzer.config.debug_export_dir = None
        analyzer.config.debug_export_csv = False
        analyzer.config.debug_export_png = False

        roi_x, roi_y, roi_w, roi_h = edge_roi.bbox
        last_ts = int(self._get_latest_image_timestamp_ns() or 0)
        for _ in range(MTF_AVG_SAMPLES - 1):
            next_img, next_ts, next_encoding = self._wait_for_new_mtf_capture_image(
                last_ts,
                timeout=MTF_SAMPLE_TIMEOUT_S,
            )
            if next_img is None:
                self._node.get_logger().warn(
                    "Timeout waiting for next image in averaging loop"
                )
                continue

            if next_ts is not None:
                last_ts = int(next_ts)
            if (
                self._param_bool("mtf.capture_required_raw", True)
                and analyzer.config.input_mode == "raw_bayer_rggb"
                and not self._is_raw_bayer_encoding(next_encoding)
            ):
                self._node.get_logger().warn(
                    f"Skipping averaging frame with non-raw encoding '{next_encoding}'"
                )
                continue
            if roi_y + roi_h > next_img.shape[0] or roi_x + roi_w > next_img.shape[1]:
                continue

            crop_img = next_img[roi_y : roi_y + roi_h, roi_x : roi_x + roi_w]
            sample_result = analyzer.compute_mtf(
                crop_img,
                roi_origin=(roi_x, roi_y),
            )
            if sample_result.valid:
                valid_samples.append(sample_result)

        return valid_samples

    def _measure_edge_candidate(
        self,
        *,
        edge_roi: EdgeROI,
        edge_index: int,
        edge_count: int,
        run_dir: Path,
        run_id: str,
        request,
        measurement_metadata: dict[str, object],
        pixel_size_um: float,
        min_edge_angle: float,
        max_edge_angle: float,
        capture_values: dict[str, object],
        actual_pixel_format: str,
        image_encoding: str,
    ) -> tuple[dict[str, object], _MeasuredEdge | None, str]:
        """Measure one edge candidate and return its summary row plus optional result."""
        if edge_roi.contrast < MTF_MIN_EDGE_CONTRAST:
            self._node.get_logger().warn(
                f"Low contrast ({edge_roi.contrast:.2f}) for {edge_roi.edge_name} edge"
            )

        edge_label = self._build_edge_export_label(edge_roi, edge_index, edge_count)
        # Each edge gets its own analyzer config so debug exports, ROI origin,
        # and per-edge metadata stay tied to the physical edge on the target.
        config = self._prepare_edge_config(
            pixel_size_um=pixel_size_um,
            min_edge_angle=min_edge_angle,
            max_edge_angle=max_edge_angle,
            auto_roi=bool(getattr(request, "auto_roi", False)),
            run_dir=run_dir,
            run_id=run_id,
            edge_roi=edge_roi,
            edge_label=edge_label,
            edge_index=edge_index,
            edge_count=edge_count,
            measurement_metadata=measurement_metadata,
            capture_values=capture_values,
            actual_pixel_format=actual_pixel_format,
            image_encoding=image_encoding,
        )
        camera_matrix, dist_coeffs = self._get_camera_calibration()
        analyzer = MTFAnalyzer(config, camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)
        result = analyzer.compute_mtf(
            edge_roi.image,
            roi_origin=edge_roi.bbox[:2],
            debug_label=edge_label,
        )

        valid_samples: list[MTFResult] = []
        measured_edge = None
        last_error = str(result.error_msg or "Unknown error")
        if result.valid:
            if result.warning_msg:
                self._node.get_logger().warn(
                    f"MTF warning ({edge_roi.edge_name}): {result.warning_msg}"
                )
            # The first frame produces the exported debug artifacts. Additional
            # frames only improve the numeric average and do not rewrite files.
            valid_samples = self._measure_average_samples(analyzer, edge_roi, result)
            result.edge_name = edge_roi.edge_name
            result.edge_direction = edge_roi.edge_direction
            result.contrast = edge_roi.contrast
            result.roi_bounds = edge_roi.bbox
            measured_edge = _MeasuredEdge(
                edge_label=edge_label,
                edge_roi=edge_roi,
                result=result,
                valid_samples=valid_samples,
                avg_mtf50=float(np.mean([sample.mtf50 for sample in valid_samples])),
                avg_mtf20=float(np.mean([sample.mtf20 for sample in valid_samples])),
                avg_mtf10=float(np.mean([sample.mtf10 for sample in valid_samples])),
                avg_angle=float(np.mean([sample.edge_angle for sample in valid_samples])),
                avg_g1_mtf50=float(np.mean([sample.g1_mtf50 for sample in valid_samples])),
                avg_g2_mtf50=float(np.mean([sample.g2_mtf50 for sample in valid_samples])),
                avg_delta_pct=float(
                    np.mean([sample.g1_g2_delta_pct for sample in valid_samples])
                ),
            )
            last_error = ""

        row = build_edge_summary_row(
            run_id=run_id,
            edge_label=edge_label,
            edge_roi=edge_roi,
            result=result,
            valid_samples=valid_samples,
            selected_for_response=False,
        )
        return row, measured_edge, last_error

    def _roi_mode_label(self, request, edge_count: int) -> str:
        """Return one stable ROI mode label for exports."""
        auto_roi = bool(getattr(request, "auto_roi", False))
        if not auto_roi:
            return "manual"
        if edge_count >= 4:
            return "auto_square4"
        return "auto"

    def _focus_position_mm(self) -> float | None:
        """Return the cached axis position if it is known."""
        try:
            position = float(getattr(self._node, "current_axis_position", -1.0))
        except (TypeError, ValueError):
            return None
        return None if position < 0 else position

    def _write_failed_measurement_run(
        self,
        *,
        request,
        measurement_metadata: dict[str, object],
        capture_values: dict[str, object],
        capture_available_keys: list[str],
        capture_mismatches: list[str],
        image_encoding: str,
        measurement_error: str,
    ) -> tuple[Path, Path]:
        """Write a minimal run folder so invalid scientific captures stay traceable."""
        run_timestamp = self._get_timestamp()
        run_dir, run_id = self._build_measurement_run_context(
            request,
            [],
            timestamp=run_timestamp,
        )
        summary_csv = write_summary_csv(run_dir, [])
        context_csv = write_context_csv(
            run_dir,
            build_context_row(
                run_id=run_id,
                timestamp=run_timestamp,
                measurement_metadata=measurement_metadata,
                roi_mode=self._roi_mode_label(request, 0),
                focus_position_mm=self._focus_position_mm(),
                capture_values=capture_values,
                capture_available_keys=capture_available_keys,
                capture_readback_mismatches=(
                    capture_mismatches if capture_mismatches else [measurement_error]
                ),
                capture_readback_ok=False,
                image_encoding=image_encoding,
                edge_count=0,
                valid_edge_count=0,
                selected_edge_label="",
                selected_result=None,
                selected_edge_angle_deg=None,
                selected_sample_count=0,
                measurement_success=False,
                measurement_error=measurement_error,
            ),
        )
        return summary_csv, context_csv

    def _populate_success_response(
        self,
        response,
        measured_edge: _MeasuredEdge,
        edge_rows: list[dict[str, object]],
        summary_csv: Path,
    ):
        """Fill the ROS response once one selected edge has been finalized."""
        result = measured_edge.result
        edge_roi = measured_edge.edge_roi
        response.success = True
        response.mtf50 = measured_edge.avg_mtf50
        response.mtf20 = measured_edge.avg_mtf20
        response.mtf10 = measured_edge.avg_mtf10
        response.edge_angle = measured_edge.avg_angle
        response.nyquist_frequency = float(result.nyquist_frequency)

        roi_mode = "manual" if edge_roi.edge_name == "manual" else "auto"
        valid_edge_count = sum(int(bool(row["valid"])) for row in edge_rows)
        response.status_message = (
            f"MTF complete: mode={roi_mode}, selected={measured_edge.edge_label}, "
            f"MTF50={response.mtf50:.2f} lp/mm, angle={response.edge_angle:.1f}deg, "
            f"valid_edges={valid_edge_count}/{len(edge_rows)}, "
            f"summary={summary_csv}"
        )
        if result.warning_msg:
            response.status_message += f", warn={result.warning_msg}"

        self._node.get_logger().info(
            f"MTF measurement successful: {response.status_message}"
        )
        return response

    def _validate_scientific_capture_state(
        self,
        capture_state: dict,
        image_encoding: str,
    ) -> tuple[dict, str, list[str]]:
        """Fail fast when the scientific raw capture state is not actually active."""
        capture_values = dict((capture_state or {}).get("values", {}))
        actual_pixel_format = str(
            capture_values.get(
                "pixel_format",
                self._param_str("mtf.capture_pixel_format", ""),
            )
        )

        if not self._param_bool("mtf.use_raw_capture", True):
            return capture_values, actual_pixel_format, []
        if not self._param_bool("mtf.capture_required_raw", True):
            return capture_values, actual_pixel_format, []

        raw_switch_error = self._camera_format_controller.get_last_operation_error().strip()
        raw_switch_hint = f" Raw-switch status: {raw_switch_error}" if raw_switch_error else ""

        if actual_pixel_format and not actual_pixel_format.startswith("Bayer"):
            raise ImageProcessingError(
                self._with_next_step(
                    f"Scientific MTF requires Bayer raw, but readback is '{actual_pixel_format}'."
                    f"{raw_switch_hint}",
                    "check the camera pixel format and retry the measurement.",
                )
            )
        if not self._is_raw_bayer_encoding(image_encoding):
            raise ImageProcessingError(
                self._with_next_step(
                    f"Scientific MTF requires raw Bayer input, got encoding "
                    f"'{image_encoding or 'unknown'}'.{raw_switch_hint}",
                    "check the camera stream encoding and retry the measurement.",
                )
            )

        mismatches = self._camera_format_controller.collect_scientific_capture_mismatches(
            capture_state,
            self._camera_format_controller.build_mtf_scientific_capture_target(capture_values),
        )
        if mismatches:
            raise ImageProcessingError(
                self._with_next_step(
                    "Scientific MTF capture readback mismatch: " + ", ".join(mismatches),
                    "restore the scientific raw capture settings and retry the measurement.",
                )
            )
        return capture_values, actual_pixel_format, mismatches

    @handle_service_errors()
    def measure_mtf_callback(self, request, response):
        """MTF measurement from current camera image."""
        self._node.get_logger().info("MTF measurement service called.")
        if self._param_bool("mtf.use_raw_capture", True):
            self._node.get_logger().info(
                "MTF capture: enabling scientific raw Bayer on the current stream."
            )
        restore_state = None

        try:
            # Step 1: acquire the current work image after the optional camera
            # switch into the scientific capture mode.
            cv_image, _image_ts_ns, image_encoding, restore_state = (
                self._acquire_measurement_frame()
            )

            # Step 2: collect request metadata and validate that the camera
            # really runs in the expected scientific raw mode.
            capture_state, capture_values, capture_available_keys = self._read_capture_state()
            capture_values = self._annotate_capture_geometry(capture_values, cv_image)
            pixel_size_um, measurement_metadata = self._prepare_measurement_metadata(request)
            capture_values, actual_pixel_format, capture_mismatches = (
                self._validate_capture_or_write_failure(
                    request=request,
                    measurement_metadata=measurement_metadata,
                    capture_state=capture_state,
                    capture_values=capture_values,
                    capture_available_keys=capture_available_keys,
                    image_encoding=image_encoding,
                )
            )
            capture_values = self._annotate_capture_geometry(capture_values, cv_image)

            # Step 3: resolve edge candidates and create one predictable run
            # folder before we start the per-edge analyzer loop.
            min_edge_angle = self._param_float("mtf_min_edge_angle", 2.0)
            max_edge_angle = self._param_float("mtf_max_edge_angle", 10.0)
            measurement_run = self._prepare_measurement_run(cv_image, request)

            # Step 4: measure every candidate edge through the shared analyzer
            # path so auto ROI and manual ROI stay directly comparable.
            edge_rows, measured_edges, selected_edge, last_error = self._measure_run_edges(
                measurement_run=measurement_run,
                request=request,
                measurement_metadata=measurement_metadata,
                pixel_size_um=pixel_size_um,
                min_edge_angle=min_edge_angle,
                max_edge_angle=max_edge_angle,
                capture_values=capture_values,
                actual_pixel_format=actual_pixel_format,
                image_encoding=image_encoding,
            )

            # Step 5: export the full run before deciding whether the service
            # should return success or surface the final failure.
            summary_csv, _context_csv = self._write_measurement_exports(
                measurement_run=measurement_run,
                source_image=cv_image,
                request=request,
                measurement_metadata=measurement_metadata,
                capture_values=capture_values,
                capture_available_keys=capture_available_keys,
                capture_mismatches=capture_mismatches,
                image_encoding=image_encoding,
                edge_rows=edge_rows,
                measured_edges=measured_edges,
                selected_edge=selected_edge,
                last_error=last_error,
            )

            # Step 6: return the selected edge response or fail with the same
            # preserved run folder that was already written above.
            return self._finalize_measurement_response(
                response=response,
                measurement_run=measurement_run,
                selected_edge=selected_edge,
                edge_rows=edge_rows,
                summary_csv=summary_csv,
                last_error=last_error,
            )

        finally:
            self._camera_format_controller.restore_after_mtf(restore_state)

        return response

    def _select_candidate_interactive(self, candidates):
        """Shows candidates side-by-side and lets user click to select."""
        images = []
        for candidate in candidates:
            if "image" in candidate:
                images.append(candidate["image"])
            elif "roi" in candidate and "source_image" in candidate:
                pass
            if "image" not in candidate:
                images.append(np.zeros((100, 100), dtype=np.uint8))

        vis_img, tile_w = RoiDetector.create_debug_visualization(images)
        selected_idx = [-1]
        window_name = "Select Target Candidate"

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and tile_w > 0:
                idx = x // tile_w
                if 0 <= idx < len(candidates):
                    selected_idx[0] = idx
                    self.logger.info(
                        f"Selected candidate {idx}: {candidates[idx]['name']}"
                    )
                    cv2.destroyWindow(window_name)

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback)
        cv2.imshow(window_name, vis_img)

        while selected_idx[0] == -1:
            key = cv2.waitKey(100)
            if key == 27:
                break
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()
        if selected_idx[0] != -1:
            return candidates[selected_idx[0]]
        return None
