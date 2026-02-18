"""Correlation verification callbacks."""

from datetime import datetime
import getpass
import time

import cv2
import numpy as np

from promoc_assembly_interfaces.srv import AutoFocus, GetOperationStatus, MoveAbsolute
from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
    ServiceCallFailedError,
)
from verification.algorithms.mtf_verification_stats import (
    annotate_correlation_mtf_quality,
    estimate_peak_position,
)

from camera_nodes.algorithms.focus_metrics import tenengrad as tenengrad_metric
from camera_nodes.algorithms.roi_detection import RoiDetector
from camera_nodes.plotting import VerificationPlotter


class CorrelationVerificationCallbacks:
    """Callbacks and helper methods for AF/MTF correlation scans."""

    @handle_service_errors()
    def verify_correlation_callback(self, request, response):
        """Scan a range and return correlation between AF and MTF peaks."""
        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        settle_time_s = request.settle_time if request.settle_time > 0 else 0.5
        requested_fpm = (
            int(request.frames_per_measurement)
            if hasattr(request, "frames_per_measurement")
            else 0
        )
        if requested_fpm > 0:
            frames_per_measurement = requested_fpm
            fpm_source = "request"
        else:
            frames_per_measurement = max(
                1,
                self._param_int("verify_correlation.frames_per_measurement", 5),
            )
            fpm_source = "parameter"
        frame_timeout_s = self._param_float("verify_correlation.frame_timeout_s", 2.0)
        use_autofocus_anchor = self._param_bool("verify_correlation.use_autofocus_anchor", True)
        scan_half_range_mm = self._param_float("verify_correlation.scan_half_range_mm", 1.5)
        autofocus_mode = self._param_int("verify_correlation.autofocus_focus_mode", 5)
        autofocus_skip_flyover = self._param_bool("verify_correlation.autofocus_skip_flyover", True)
        objective_magnification_x = self._param_float("verify_correlation.objective_magnification_x", 0.0)
        use_beamsplitter = self._param_bool("verify_correlation.use_beamsplitter", False)
        roi_size_px = self._param_int("verify_correlation.roi_size_px", 300)
        use_detected_square_roi = self._param_bool("verify_correlation.use_detected_square_roi", True)
        log_progress = self._param_bool("verify_correlation.log_progress", True)

        step_size = request.step_size if request.step_size > 0 else 0.5

        if not self.move_client.wait_for_service(timeout_sec=2.0) or not self.status_client.wait_for_service(
            timeout_sec=2.0
        ):
            raise ServiceCallFailedError("Axis services not available")
        if use_autofocus_anchor and not self.af_client.wait_for_service(timeout_sec=2.0):
            raise ServiceCallFailedError("Autofocus service not available")

        operator_name = ""
        if hasattr(request, "operator_name"):
            operator_name = str(request.operator_name or "").strip()
        if not operator_name:
            # Keep behavior consistent with other verification outputs:
            # always store under user subdirectory when no explicit operator is given.
            operator_name = str(getpass.getuser() or "").strip()

        output_dir = self._get_output_dir(
            "verification/correlation", operator_name=operator_name
        )
        timestamp = self._get_timestamp()
        run_dir = output_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        analyzer = self._create_mtf_analyzer()
        metadata = self._get_measurement_metadata()

        af_anchor_pos = None
        if use_autofocus_anchor:
            af_anchor_pos = self._run_correlation_anchor_autofocus(
                request=request,
                focus_mode=autofocus_mode,
                skip_flyover=autofocus_skip_flyover,
                objective_magnification_x=objective_magnification_x,
                use_beamsplitter=use_beamsplitter,
            )
            scan_start = float(af_anchor_pos - scan_half_range_mm)
            scan_end = float(af_anchor_pos + scan_half_range_mm)
        else:
            scan_start = float(request.start_position)
            scan_end = float(request.end_position)

        if scan_start >= scan_end:
            raise ConfigurationError(
                f"invalid scan range after anchor selection: start={scan_start:.4f} end={scan_end:.4f}"
            )

        positions = np.arange(scan_start, scan_end + step_size, step_size)
        self.get_logger().info(
            f"Correlation Verification: scan={scan_start:.3f}-{scan_end:.3f}mm "
            f"(step={step_size}mm, {len(positions)} points, "
            f"frames_per_measurement={frames_per_measurement} ({fpm_source}), "
            f"anchor={'on' if use_autofocus_anchor else 'off'})"
        )

        roi_anchor_pos = float(af_anchor_pos) if af_anchor_pos is not None else float((scan_start + scan_end) / 2.0)
        self._move_axis_and_wait(roi_anchor_pos)
        time.sleep(settle_time_s)
        anchor_frame, current_stamp = self._wait_for_fresh_cv_image(timeout_sec=frame_timeout_s)
        if anchor_frame is None:
            raise ImageProcessingError("No image available at ROI anchor position")
        edge_boxes, roi_source, roi_center = self._select_locked_correlation_edge_rois(
            anchor_frame,
            roi_size_px=max(32, roi_size_px),
            prefer_detected_square=use_detected_square_roi,
        )
        if not edge_boxes:
            raise ImageProcessingError("Failed to define locked edge ROIs")
        roi_x1, roi_y1, roi_x2, roi_y2 = self._edge_boxes_to_bounds(edge_boxes)
        csv_path = run_dir / f"correlation_{timestamp}.csv"
        summary_path = run_dir / f"correlation_summary_{timestamp}.csv"
        plot_path = run_dir / f"correlation_plot_{timestamp}.png"

        try:
            roi_debug = anchor_frame.copy()
            cv2.rectangle(roi_debug, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 255, 255), 2)
            for edge_name, x, y, w_box, h_box in edge_boxes:
                cv2.rectangle(
                    roi_debug,
                    (int(x), int(y)),
                    (int(x + w_box), int(y + h_box)),
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    roi_debug,
                    str(edge_name),
                    (int(x), int(max(0, y - 8))),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 0),
                    1,
                )
            cv2.circle(roi_debug, (int(roi_center[0]), int(roi_center[1])), 6, (0, 0, 255), -1)
            cv2.imwrite(str(run_dir / f"correlation_roi_anchor_{timestamp}.jpg"), roi_debug)
        except Exception:
            pass
        self.get_logger().info(
            f"Correlation locked ROI set at anchor={roi_anchor_pos:.4f}mm "
            f"(source={roi_source}, edge_rois={len(edge_boxes)})."
        )
        self.get_logger().info(
            f"Correlation exhaustive scan: start={scan_start:.4f}mm "
            f"(anchor-{scan_half_range_mm:.3f}), end={scan_end:.4f}mm "
            f"(anchor+{scan_half_range_mm:.3f}), step={step_size:.3f}mm."
        )

        metadata.update(
            {
                "type": "correlation_scan",
                "operator": operator_name or "unknown",
                "requested_start": request.start_position,
                "requested_end": request.end_position,
                "scan_start": scan_start,
                "scan_end": scan_end,
                "step": step_size,
                "settle_time_s": settle_time_s,
                "frames_per_measurement": frames_per_measurement,
                "frames_per_measurement_source": fpm_source,
                "frame_timeout_s": frame_timeout_s,
                "log_progress": log_progress,
                "use_autofocus_anchor": use_autofocus_anchor,
                "scan_half_range_mm": scan_half_range_mm,
                "autofocus_mode": autofocus_mode,
                "autofocus_skip_flyover": autofocus_skip_flyover,
                "objective_magnification_x": objective_magnification_x,
                "use_beamsplitter": use_beamsplitter,
                "autofocus_anchor_pos_mm": af_anchor_pos if af_anchor_pos is not None else "",
                "roi_source": roi_source,
                "roi_anchor_pos_mm": roi_anchor_pos,
                "roi_size_px": roi_size_px,
                "roi_layout": "fixed_four_edge_rois",
                "edge_rois_count": len(edge_boxes),
                "edge_roi_long_px": 300,
                "edge_roi_short_px": 50,
                "roi_x1": roi_x1,
                "roi_y1": roi_y1,
                "roi_x2": roi_x2,
                "roi_y2": roi_y2,
            }
        )

        results = []
        quality_summary = {
            "points_valid": 0,
            "points_suspicious": 0,
            "suspicious_ratio": 0.0,
            "reference_mtf50_median_lpmm": 0.0,
            "reference_mtf50_upper_lpmm": 0.0,
        }

        try:
            for idx, pos in enumerate(positions, start=1):
                if idx == 1 or idx == len(positions) or (idx % 100 == 0):
                    self.get_logger().info(
                        f"Correlation move {idx}/{len(positions)}: target={float(pos):.4f}mm"
                    )
                self._move_axis_and_wait(pos)
                time.sleep(settle_time_s)

                axis_position_mm = (
                    self._read_axis_position_mm()
                    if hasattr(self, "_read_axis_position_mm")
                    else None
                )
                effective_pos = (
                    float(axis_position_mm)
                    if axis_position_mm is not None
                    else float(pos)
                )

                first_frame, current_stamp = self._wait_for_fresh_cv_image(
                    previous_stamp=current_stamp, timeout_sec=frame_timeout_s
                )
                if first_frame is None:
                    self.get_logger().warn(f"No image at Z={pos:.2f}")
                    continue

                frame_batch, current_stamp = self._collect_correlation_frame_batch(
                    first_frame=first_frame,
                    first_stamp=current_stamp,
                    frames_per_measurement=frames_per_measurement,
                    timeout_sec=frame_timeout_s,
                )
                if len(frame_batch) < frames_per_measurement:
                    self.get_logger().warn(
                        f"Correlation Z={effective_pos:.3f}: only "
                        f"{len(frame_batch)}/{frames_per_measurement} frames collected."
                    )

                tenengrad_values = []
                valid_mtf_values = []
                warning_msgs = []
                for frame_idx, cv_image in enumerate(frame_batch, start=1):
                    if cv_image is None:
                        continue
                    h_img, w_img = cv_image.shape[:2]
                    x1 = max(0, min(int(roi_x1), w_img - 1))
                    y1 = max(0, min(int(roi_y1), h_img - 1))
                    x2 = max(x1 + 1, min(int(roi_x2), w_img))
                    y2 = max(y1 + 1, min(int(roi_y2), h_img))
                    focus_roi = cv_image[y1:y2, x1:x2]
                    ten_target = focus_roi if focus_roi.size > 0 else cv_image
                    tenengrad_values.append(float(tenengrad_metric(ten_target)))
                    for edge_name, x, y, w_box, h_box in edge_boxes:
                        if x < 0 or y < 0 or x + w_box > w_img or y + h_box > h_img:
                            continue
                        edge_img = cv_image[y : y + h_box, x : x + w_box]
                        if edge_img.size == 0:
                            continue
                        mtf_res = analyzer.compute_mtf(
                            edge_img,
                            debug_label=(
                                f"correlation_{edge_name}_p{idx:03d}_f{frame_idx:02d}"
                            ),
                        )
                        if mtf_res.warning_msg:
                            warning_msgs.append(str(mtf_res.warning_msg))
                        if mtf_res.valid:
                            valid_mtf_values.append(float(mtf_res.mtf50))

                if not tenengrad_values:
                    self.get_logger().warn(
                        f"No valid tenengrad samples at Z={effective_pos:.3f}"
                    )
                    continue

                tenengrad = float(np.mean(tenengrad_values))
                mtf_valid = len(valid_mtf_values) > 0
                mtf_val = float(np.mean(valid_mtf_values)) if mtf_valid else 0.0
                unique_warnings = list(dict.fromkeys(warning_msgs))
                if mtf_valid and unique_warnings:
                    self.get_logger().warn(
                        "MTF warning (correlation): "
                        + "; ".join(unique_warnings[:2])
                    )

                if log_progress or idx == 1 or idx == len(positions) or (idx % 100 == 0):
                    axis_txt = (
                        f"{axis_position_mm:.4f}mm"
                        if axis_position_mm is not None
                        else "n/a"
                    )
                    self.get_logger().info(
                        f"Correlation point {idx}/{len(positions)}: "
                        f"cmd={float(pos):.4f}mm axis={axis_txt} "
                        f"ten={tenengrad:.1f} mtf50={mtf_val:.3f} "
                        f"valid_edge_samples={len(valid_mtf_values)}/"
                        f"{len(frame_batch) * len(edge_boxes)}"
                    )

                results.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "index": int(idx),
                        "position_mm": float(effective_pos),
                        "command_position_mm": float(pos),
                        "axis_position_mm": (
                            float(axis_position_mm)
                            if axis_position_mm is not None
                            else ""
                        ),
                        "tenengrad": float(tenengrad),
                        "mtf50_lpmm": float(mtf_val),
                        "valid": bool(mtf_valid),
                        "frames_requested": int(frames_per_measurement),
                        "frames_collected": int(len(frame_batch)),
                        # Legacy alias for compatibility with existing tooling.
                        "frames_used_mtf": int(len(valid_mtf_values)),
                        "mtf_edge_samples_used": int(len(valid_mtf_values)),
                        "edge_rois_count": int(len(edge_boxes)),
                        "edge_samples_requested": int(len(frame_batch) * len(edge_boxes)),
                        "edge_samples_used": int(len(valid_mtf_values)),
                        "warning_count": int(len(unique_warnings)),
                        "roi_x1": int(roi_x1),
                        "roi_y1": int(roi_y1),
                        "roi_x2": int(roi_x2),
                        "roi_y2": int(roi_y2),
                        "roi_source": roi_source,
                        "roi_anchor_pos_mm": float(roi_anchor_pos),
                        "autofocus_anchor_pos_mm": (
                            float(af_anchor_pos) if af_anchor_pos is not None else ""
                        ),
                    }
                )
        finally:
            if results:
                quality_summary = annotate_correlation_mtf_quality(results)
                metadata.update(
                    {
                        "mtf_quality_points_valid": quality_summary["points_valid"],
                        "mtf_quality_points_suspicious": quality_summary[
                            "points_suspicious"
                        ],
                        "mtf_quality_suspicious_ratio": quality_summary[
                            "suspicious_ratio"
                        ],
                        "mtf_quality_reference_median_lpmm": quality_summary[
                            "reference_mtf50_median_lpmm"
                        ],
                        "mtf_quality_reference_upper_lpmm": quality_summary[
                            "reference_mtf50_upper_lpmm"
                        ],
                    }
                )
                self.get_logger().info(
                    f"Saving {len(results)} correlation results (partial or complete)..."
                )
                self._write_csv_with_metadata(
                    csv_path,
                    metadata,
                    [
                        "timestamp",
                        "index",
                        "position_mm",
                        "command_position_mm",
                        "axis_position_mm",
                        "tenengrad",
                        "mtf50_lpmm",
                        "valid",
                        "frames_requested",
                        "frames_collected",
                        "mtf_edge_samples_used",
                        "frames_used_mtf",
                        "edge_rois_count",
                        "edge_samples_requested",
                        "edge_samples_used",
                        "warning_count",
                        "mtf_quality_class",
                        "mtf_is_suspicious",
                        "mtf_suspicion_score",
                        "mtf_suspicion_reasons",
                        "mtf50_robust_z",
                        "mtf50_neighbor_median_lpmm",
                        "tenengrad_norm",
                        "mtf50_norm",
                        "roi_x1",
                        "roi_y1",
                        "roi_x2",
                        "roi_y2",
                        "roi_source",
                        "roi_anchor_pos_mm",
                        "autofocus_anchor_pos_mm",
                    ],
                    results,
                )
                self.get_logger().info(f"Correlation results saved: {csv_path.name}")

        if not results:
            raise ImageProcessingError("No valid data collected during scan")

        valid_mtf_rows = [
            row for row in results if row.get("valid") and row.get("mtf50_lpmm", 0.0) > 0.0
        ]
        if not valid_mtf_rows:
            raise ImageProcessingError("No valid MTF data collected during scan")

        filtered_mtf_rows = [
            row for row in valid_mtf_rows if not bool(row.get("mtf_is_suspicious", False))
        ]
        mtf_peak_rows = filtered_mtf_rows if filtered_mtf_rows else valid_mtf_rows
        mtf_peak_basis = (
            "filtered_valid_mtf" if filtered_mtf_rows else "raw_valid_mtf_fallback"
        )

        af_peak = estimate_peak_position(
            results, position_key="position_mm", value_key="tenengrad"
        )
        mtf_peak = estimate_peak_position(
            mtf_peak_rows, position_key="position_mm", value_key="mtf50_lpmm"
        )

        if af_peak is None:
            af_peak = max(results, key=lambda x: x["tenengrad"])["position_mm"]
        if mtf_peak is None:
            mtf_peak = max(mtf_peak_rows, key=lambda x: x["mtf50_lpmm"])["position_mm"]

        peak_shift = float(af_peak) - float(mtf_peak)

        suspicious_rows = [
            row for row in valid_mtf_rows if bool(row.get("mtf_is_suspicious", False))
        ]
        suspicious_examples = "; ".join(
            str(row.get("mtf_suspicion_reasons", "")).strip()
            for row in suspicious_rows[:3]
            if str(row.get("mtf_suspicion_reasons", "")).strip()
        )

        summary_row = {
            "timestamp": datetime.now().isoformat(),
            "points_total": int(len(results)),
            "points_valid_mtf": int(len(mtf_peak_rows)),
            "points_valid_mtf_raw": int(len(valid_mtf_rows)),
            "points_suspicious_mtf": int(len(suspicious_rows)),
            "suspicious_ratio": float(quality_summary["suspicious_ratio"]),
            "scan_start_mm": float(scan_start),
            "scan_end_mm": float(scan_end),
            "step_mm": float(step_size),
            "autofocus_anchor_pos_mm": (
                float(af_anchor_pos) if af_anchor_pos is not None else ""
            ),
            "roi_anchor_pos_mm": float(roi_anchor_pos),
            "roi_source": str(roi_source),
            "edge_rois_count": int(len(edge_boxes)),
            "frames_per_measurement": int(frames_per_measurement),
            "mtf_peak_basis": mtf_peak_basis,
            "mtf_reference_median_lpmm": float(
                quality_summary["reference_mtf50_median_lpmm"]
            ),
            "mtf_reference_upper_lpmm": float(
                quality_summary["reference_mtf50_upper_lpmm"]
            ),
            "suspicion_examples": suspicious_examples,
            "af_peak_mm": float(af_peak),
            "mtf_peak_mm": float(mtf_peak),
            "peak_shift_mm": float(peak_shift),
        }
        self._write_csv_with_metadata(
            summary_path,
            metadata,
            [
                "timestamp",
                "points_total",
                "points_valid_mtf",
                "points_valid_mtf_raw",
                "points_suspicious_mtf",
                "suspicious_ratio",
                "scan_start_mm",
                "scan_end_mm",
                "step_mm",
                "autofocus_anchor_pos_mm",
                "roi_anchor_pos_mm",
                "roi_source",
                "edge_rois_count",
                "frames_per_measurement",
                "mtf_peak_basis",
                "mtf_reference_median_lpmm",
                "mtf_reference_upper_lpmm",
                "suspicion_examples",
                "af_peak_mm",
                "mtf_peak_mm",
                "peak_shift_mm",
            ],
            [summary_row],
        )
        self.get_logger().info(f"Correlation summary saved: {summary_path.name}")

        try:
            plotter = VerificationPlotter(self.get_logger())
            plotter.plot_correlation_verification(
                {
                    "data": results,
                    "peak_shift": peak_shift,
                    "max_af_pos": float(af_peak),
                    "max_mtf_pos": float(mtf_peak),
                },
                str(plot_path),
            )
            self.get_logger().info(f"Correlation plot saved: {plot_path.name}")
        except Exception:
            pass

        response.success = True
        if af_anchor_pos is not None:
            response.status_message = (
                f"Correlation done. Shift: {peak_shift:.4f}mm "
                f"(anchor={float(af_anchor_pos):.4f}mm, csv={csv_path.name})"
            )
        else:
            response.status_message = (
                f"Correlation done. Shift: {peak_shift:.4f}mm (csv={csv_path.name})"
            )
        response.peak_shift = peak_shift
        response.max_af_pos = float(af_peak)
        response.max_mtf_pos = float(mtf_peak)

        return response

    def _run_correlation_anchor_autofocus(
        self,
        request,
        focus_mode: int,
        skip_flyover: bool,
        objective_magnification_x: float,
        use_beamsplitter: bool,
    ) -> float:
        """Run autofocus once to anchor ROI and scan window."""
        af_req = AutoFocus.Request()
        af_req.start_position = float(request.start_position)
        af_req.end_position = float(request.end_position)
        af_req.focus_mode = int(focus_mode)
        af_req.skip_flyover = bool(skip_flyover)
        af_req.save_best_image = False
        af_req.objective_magnification_x = float(objective_magnification_x)
        af_req.use_beamsplitter = bool(use_beamsplitter)
        af_req.notes = "verify_correlation_anchor"

        self.get_logger().info(
            f"Correlation anchor AF: range={af_req.start_position:.3f}-{af_req.end_position:.3f}mm "
            f"mode={af_req.focus_mode} skip_flyover={af_req.skip_flyover}"
        )
        af_resp = self.af_client.call(af_req)
        if not af_resp or not af_resp.success:
            msg = af_resp.status_message if af_resp else "no response"
            raise ServiceCallFailedError(f"Anchor autofocus failed: {msg}")

        anchor_pos = float(af_resp.best_focus_position)
        self.get_logger().info(
            f"Correlation anchor AF complete: pos={anchor_pos:.4f}mm score={af_resp.best_focus_value:.0f}"
        )
        return anchor_pos

    def _collect_correlation_frame_batch(
        self,
        first_frame,
        first_stamp,
        frames_per_measurement: int,
        timeout_sec: float,
    ):
        """Collect fresh frames for temporal averaging at a single scan point."""
        frames = [first_frame]
        stamp = first_stamp
        for _ in range(max(0, int(frames_per_measurement) - 1)):
            next_frame, stamp = self._wait_for_fresh_cv_image(
                previous_stamp=stamp, timeout_sec=timeout_sec
            )
            if next_frame is None:
                break
            frames.append(next_frame)
        return frames, stamp

    def _select_locked_correlation_edge_rois(
        self,
        image,
        roi_size_px: int,
        prefer_detected_square: bool = True,
    ):
        """Select locked edge ROIs once and keep fixed for full correlation scan."""
        _, w = image.shape[:2]
        h = image.shape[0]
        center_x, center_y = int(w // 2), int(h // 2)
        roi_source = "image_center"
        chosen_square = None

        if prefer_detected_square:
            try:
                _, _, squares = RoiDetector.detect_targets(image)
            except Exception:
                squares = []
            if squares:
                if hasattr(self, "_find_nearest_square"):
                    try:
                        chosen_square = self._find_nearest_square(
                            squares, center_x, center_y, image.shape
                        )
                    except Exception:
                        chosen_square = None
                if chosen_square is None:
                    chosen_square = min(
                        squares,
                        key=lambda rect: (
                            (float(rect[0][0]) - center_x) ** 2
                            + (float(rect[0][1]) - center_y) ** 2
                        ),
                    )
                if chosen_square is not None:
                    center_x = int(round(chosen_square[0][0]))
                    center_y = int(round(chosen_square[0][1]))
                    roi_source = "detected_square"

        # Same ROI schema as verify_mtf: fixed edge crops with (long, short) = (300, 50).
        fixed_roi_dims = (300, 50)
        if chosen_square is None:
            synthetic_side = max(16, int(roi_size_px))
            chosen_square = ((float(center_x), float(center_y)), (float(synthetic_side), float(synthetic_side)), 0.0)
            roi_source = "synthetic_center_square"

        edges_with_boxes = RoiDetector.split_square_into_edges_with_boxes(
            image, chosen_square, fixed_size=fixed_roi_dims
        )
        edge_boxes = [
            (str(edge_name), int(x), int(y), int(w_box), int(h_box))
            for _, (x, y, w_box, h_box), edge_name in edges_with_boxes
        ]
        return edge_boxes, roi_source, (center_x, center_y)

    @staticmethod
    def _edge_boxes_to_bounds(edge_boxes):
        if not edge_boxes:
            return (0, 0, 1, 1)
        x1 = min(int(x) for _, x, _, _, _ in edge_boxes)
        y1 = min(int(y) for _, _, y, _, _ in edge_boxes)
        x2 = max(int(x + w) for _, x, _, w, _ in edge_boxes)
        y2 = max(int(y + h) for _, _, y, _, h in edge_boxes)
        if x2 <= x1:
            x2 = x1 + 1
        if y2 <= y1:
            y2 = y1 + 1
        return (x1, y1, x2, y2)

    def _move_axis_and_wait(self, pos_mm):
        req = MoveAbsolute.Request()
        req.axis_position = float(pos_mm)
        res = self.move_client.call(req)
        if not res or not res.success:
            raise ServiceCallFailedError(f"Move to {pos_mm} failed")

        start_idle = time.time()
        while time.time() - start_idle < 30.0:
            stat = self.status_client.call(GetOperationStatus.Request())
            if stat and stat.operation_status == "idle":
                return
            if stat and stat.operation_status in ["error", "emergency_stop"]:
                raise ServiceCallFailedError(
                    f"Axis reported status='{stat.operation_status}' while moving to {pos_mm}"
                )
            time.sleep(0.05)

        raise ServiceCallFailedError("Timeout waiting for axis idle")
