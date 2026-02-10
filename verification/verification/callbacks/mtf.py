"""MTF verification callbacks and helper methods."""

import csv
from datetime import datetime
from pathlib import Path

import cv2

from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import ImageProcessingError
from verification.algorithms.mtf_verification_stats import (
    extract_metric_values,
    summarize_mtf_by_direction,
    summarize_mtf_by_group,
    summarize_numeric_values,
)

try:
    from camera_nodes.algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
    from camera_nodes.algorithms.roi_detection import RoiDetector
    from camera_nodes.plotting import VerificationPlotter
except ImportError:
    import logging

    logging.warning("Could not import camera_nodes algorithms directly. Check PYTHONPATH.")
    raise


class MTFVerificationCallbacks:
    """Callbacks and helper methods for MTF verification."""

    @handle_service_errors()
    def verify_mtf_callback(self, request, response):
        """Verification service: MTF field test with comprehensive output."""
        repetitions = (
            max(1, request.repetitions)
            if hasattr(request, "repetitions") and request.repetitions > 0
            else 1
        )

        self.get_logger().info(
            f"MTF Verification: field_test={request.field_test}, reps={repetitions}"
        )

        metadata = self._get_measurement_metadata()
        metadata.update(
            {
                "operator": request.operator_name or "unknown",
                "config_name": request.config_name or "default",
                "notes": request.notes or "",
                "measurement_type": "mtf_verification",
                "field_test": request.field_test,
                "repetitions": repetitions,
            }
        )

        output_dir = self._get_output_dir(
            "verification/mtf_verification", operator_name=request.operator_name
        )
        timestamp = self._get_timestamp()
        run_dir = output_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        csv_path = run_dir / f"mtf_verification_{timestamp}.csv"

        analyzer = self._create_mtf_analyzer(debug_dir=str(run_dir), force_debug=True)
        first_image, image_stamp = self._wait_for_fresh_cv_image(timeout_sec=2.0)
        if first_image is None:
            raise ImageProcessingError("No image available")

        vis_img, bars, squares = RoiDetector.detect_targets(first_image)
        if not squares and not bars:
            raise ImageProcessingError("No MTF targets detected")

        positions = self._define_measurement_positions(first_image, request.field_test)
        self._annotate_targets(vis_img, positions)
        cv2.imwrite(str(run_dir / f"mtf_targets_{timestamp}.jpg"), vis_img)

        results = []
        mtf_curves_plot = []
        mtf_curves_full = []
        edges_failed = 0
        edges_tile_path = None

        try:
            baseline_squares = squares
            current_stamp = image_stamp
            for rep in range(repetitions):
                cv_image, current_stamp = self._wait_for_fresh_cv_image(
                    previous_stamp=current_stamp, timeout_sec=2.0
                )
                if cv_image is None:
                    self.get_logger().warn(f"No image for repetition {rep + 1}")
                    continue

                rep_vis, _, rep_squares = RoiDetector.detect_targets(cv_image)
                if rep_vis is None or rep_vis.size == 0:
                    if len(cv_image.shape) == 2:
                        rep_vis = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)
                    else:
                        rep_vis = cv_image.copy()

                rep_positions = self._define_measurement_positions(
                    cv_image, request.field_test
                )
                self._annotate_targets(rep_vis, rep_positions)
                cv2.imwrite(
                    str(run_dir / f"mtf_targets_rep{rep + 1}_{timestamp}.jpg"), rep_vis
                )

                active_squares = rep_squares if rep_squares else baseline_squares
                if not active_squares:
                    for pos_name, target_x, target_y in rep_positions:
                        self._record_missing_target(
                            results,
                            metadata,
                            rep + 1,
                            pos_name,
                            target_x,
                            target_y,
                            error="no_detected_squares",
                        )
                    edges_failed += 4 * len(rep_positions)
                    continue

                for pos_name, target_x, target_y in rep_positions:
                    chosen_square = self._find_nearest_square(
                        active_squares, target_x, target_y, cv_image.shape
                    )
                    if not chosen_square:
                        self._record_missing_target(
                            results, metadata, rep + 1, pos_name, target_x, target_y
                        )
                        edges_failed += 4
                        continue

                    (square_cx, square_cy), _, _ = chosen_square
                    fixed_roi_dims = (300, 50)
                    edges_with_boxes = RoiDetector.split_square_into_edges_with_boxes(
                        cv_image, chosen_square, fixed_size=fixed_roi_dims
                    )

                    if edges_tile_path is None:
                        edges = [roi for roi, _, _ in edges_with_boxes]
                        if edges:
                            try:
                                vis_edges, _ = RoiDetector.create_debug_visualization(edges)
                                edges_tile_path = run_dir / f"mtf_edges_overview_{timestamp}.jpg"
                                cv2.imwrite(str(edges_tile_path), vis_edges)
                            except Exception:
                                pass

                    for roi_img, (x, y, w_box, h_box), edge_name in edges_with_boxes:
                        self._draw_edge_debug(
                            rep_vis,
                            run_dir,
                            cv_image,
                            x,
                            y,
                            w_box,
                            h_box,
                            pos_name,
                            edge_name,
                            f"{timestamp}_rep{rep + 1}",
                        )

                        contrast = RoiDetector.calculate_michelson_contrast(roi_img)
                        debug_label = f"{pos_name}_{edge_name}"
                        mtf_res = analyzer.compute_mtf(roi_img, debug_label=debug_label)

                        row = {
                            "timestamp": datetime.now().isoformat(),
                            "config": request.config_name or "default",
                            "repetition": int(rep + 1),
                            "position": pos_name,
                            "edge": edge_name,
                            "roi_x": int(x),
                            "roi_y": int(y),
                            "roi_w": int(w_box),
                            "roi_h": int(h_box),
                            "square_cx": int(square_cx),
                            "square_cy": int(square_cy),
                            "contrast": f"{contrast:.3f}",
                        }

                        if mtf_res.valid:
                            if mtf_res.warning_msg:
                                self.get_logger().warn(
                                    f"MTF warning ({pos_name}/{edge_name}): {mtf_res.warning_msg}"
                                )
                            row.update(
                                {
                                    "mtf50_lpmm": f"{mtf_res.mtf50:.2f}",
                                    "mtf20_lpmm": f"{mtf_res.mtf20:.2f}",
                                    "mtf10_lpmm": f"{mtf_res.mtf10:.2f}",
                                    "edge_angle_deg": f"{mtf_res.edge_angle:.2f}",
                                    "nyquist_lpmm": f"{mtf_res.nyquist_frequency:.2f}",
                                    "valid": "true",
                                    "error": "",
                                }
                            )
                            if mtf_res.frequencies.size > 0:
                                curve = {
                                    "label": f"{pos_name}-{edge_name}",
                                    "repetition": int(rep + 1),
                                    "frequencies": mtf_res.frequencies,
                                    "mtf_values": mtf_res.mtf_values,
                                    "mtf_ideal": mtf_res.mtf_ideal,
                                    "nyquist_lpmm": mtf_res.nyquist_frequency,
                                }
                                mtf_curves_full.append(curve)
                                if len(mtf_curves_plot) < 8:
                                    mtf_curves_plot.append(curve)
                        else:
                            edges_failed += 1
                            row.update(
                                {
                                    "mtf50_lpmm": "0",
                                    "mtf20_lpmm": "0",
                                    "mtf10_lpmm": "0",
                                    "edge_angle_deg": "0",
                                    "nyquist_lpmm": "0",
                                    "valid": "false",
                                    "error": mtf_res.error_msg,
                                }
                            )
                        results.append(row)
        finally:
            if results:
                self.get_logger().info(
                    f"Saving {len(results)} MTF results (partial or complete)..."
                )
                fieldnames = [
                    "timestamp",
                    "config",
                    "repetition",
                    "position",
                    "edge",
                    "roi_x",
                    "roi_y",
                    "roi_w",
                    "roi_h",
                    "square_cx",
                    "square_cy",
                    "mtf50_lpmm",
                    "mtf20_lpmm",
                    "mtf10_lpmm",
                    "edge_angle_deg",
                    "contrast",
                    "nyquist_lpmm",
                    "valid",
                    "error",
                ]
                self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)

        stats_csv_path = self._save_mtf_statistics(run_dir, timestamp, results, metadata)
        dir_stats_path = self._save_mtf_directional_stats(
            run_dir, timestamp, results, metadata
        )
        self._save_mtf_curves(run_dir, timestamp, mtf_curves_full)

        try:
            plotter = VerificationPlotter(self.get_logger())
            plot_path = run_dir / f"mtf_results_{timestamp}.png"
            plotter.plot_mtf_verification(results, str(plot_path), curves=mtf_curves_plot)
        except Exception as e:
            self.get_logger().error(f"Plotting failed: {e}")

        response.success = True
        response.status_message = f"MTF done. CSV: {csv_path.name}"
        response.csv_path = str(csv_path)
        valid_mtf50 = extract_metric_values(results, "mtf50_lpmm")
        valid_mtf20 = extract_metric_values(results, "mtf20_lpmm")
        valid_mtf10 = extract_metric_values(results, "mtf10_lpmm")
        mtf50_summary = summarize_numeric_values(valid_mtf50)
        response.mtf50_mean = mtf50_summary["mean"]
        response.mtf50_std = mtf50_summary["std"]
        response.mtf20_mean = summarize_numeric_values(valid_mtf20)["mean"]
        response.mtf10_mean = summarize_numeric_values(valid_mtf10)["mean"]
        response.edges_measured = len(valid_mtf50)
        response.edges_failed = edges_failed

        if stats_csv_path:
            self.get_logger().info(f"MTF group stats saved: {stats_csv_path.name}")
        if dir_stats_path:
            self.get_logger().info(f"Directional MTF stats saved: {dir_stats_path.name}")

        return response

    def _create_mtf_analyzer(
        self, debug_dir: str | None = None, force_debug: bool = False
    ) -> MTFAnalyzer:
        pixel_size = self.get_parameter("pixel_size_um").value
        config = MTFConfig(pixel_size_um=pixel_size, min_edge_angle=2.0)
        self._apply_mtf_param_overrides(
            config, debug_dir=debug_dir, force_debug=force_debug
        )
        self._apply_mtf_profile(config)
        return MTFAnalyzer(config)

    def _apply_mtf_param_overrides(
        self, config: MTFConfig, debug_dir: str | None, force_debug: bool
    ) -> None:
        """Apply parameter overrides to an MTFConfig instance."""

        def _param(name: str):
            return self.get_parameter(name).value

        if debug_dir is None:
            debug_dir = str(_param("mtf.debug_export_dir") or "")
            if debug_dir:
                config.debug_export_dir = debug_dir
                prefix = _param("mtf.debug_export_prefix")
                if prefix:
                    config.debug_export_prefix = str(prefix)
                config.debug_export_csv = bool(_param("mtf.debug_export_csv"))
                config.debug_export_png = bool(_param("mtf.debug_export_png"))
        else:
            config.debug_export_dir = str(debug_dir)
            prefix = _param("mtf.debug_export_prefix")
            if prefix:
                config.debug_export_prefix = str(prefix)
            if force_debug:
                config.debug_export_csv = True
                config.debug_export_png = True
            else:
                config.debug_export_csv = bool(_param("mtf.debug_export_csv"))
                config.debug_export_png = bool(_param("mtf.debug_export_png"))

        config.lsf_window_mode = str(_param("mtf.lsf_window_mode") or config.lsf_window_mode)
        try:
            config.lsf_peak_window_size = int(_param("mtf.lsf_peak_window_size") or 0)
        except Exception:
            pass
        try:
            config.derivative_mode = str(_param("mtf.derivative_mode") or config.derivative_mode)
        except Exception:
            pass
        try:
            config.apply_derivative_correction = bool(_param("mtf.apply_derivative_correction"))
        except Exception:
            pass
        try:
            config.derivative_correction_max = float(
                _param("mtf.derivative_correction_max") or 0.0
            )
        except Exception:
            pass
        try:
            config.apply_angle_correction = bool(_param("mtf.apply_angle_correction"))
        except Exception:
            pass
        try:
            config.esf_smooth_mode = str(_param("mtf.esf_smooth_mode") or config.esf_smooth_mode)
        except Exception:
            pass
        try:
            config.esf_sg_window = int(_param("mtf.esf_sg_window") or config.esf_sg_window)
        except Exception:
            pass
        try:
            config.esf_sg_poly = int(_param("mtf.esf_sg_poly") or config.esf_sg_poly)
        except Exception:
            pass
        try:
            config.edge_validation_mode = str(
                _param("mtf.edge_validation_mode") or config.edge_validation_mode
            )
        except Exception:
            pass
        try:
            config.edge_validation_percentile = float(
                _param("mtf.edge_validation_percentile") or config.edge_validation_percentile
            )
        except Exception:
            pass
        try:
            config.edge_validation_min_points = int(
                _param("mtf.edge_validation_min_points") or config.edge_validation_min_points
            )
        except Exception:
            pass
        try:
            config.clip_to_nyquist = bool(_param("mtf.clip_to_nyquist"))
        except Exception:
            pass
        try:
            config.export_dual_curves = bool(_param("mtf.export_dual_curves"))
        except Exception:
            pass
        try:
            config.mtf_clip_max = float(_param("mtf.clip_max") or 0.0)
        except Exception:
            pass
        try:
            config.mtf_warn_threshold = float(
                _param("mtf.warn_threshold") or config.mtf_warn_threshold
            )
        except Exception:
            pass

    def _apply_mtf_profile(self, config: MTFConfig) -> None:
        """Apply profile presets for ease-of-use."""
        try:
            profile = str(self.get_parameter("mtf.profile").value or "default").strip().lower()
        except Exception:
            profile = "default"
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
                config.debug_export_dir = str(
                    Path(self.get_parameter("results_dir").value) / "mtf_debug"
                )
            config.debug_export_csv = True
            config.debug_export_png = True
            if config.esf_smooth_mode == "none":
                config.esf_smooth_mode = "sg"
            config.export_dual_curves = True
        if profile not in ("default", "scientific", "debug", ""):
            self.get_logger().warn(
                f"Unknown mtf.profile='{profile}', using current configuration."
            )

    def _define_measurement_positions(self, image, field_test: bool):
        h, w = image.shape[:2]
        positions = [("center", w // 2, h // 2)]
        if field_test:
            margin = min(w, h) // 4
            positions.extend(
                [
                    ("top_left", margin, margin),
                    ("top_right", w - margin, margin),
                    ("bottom_left", margin, h - margin),
                    ("bottom_right", w - margin, h - margin),
                ]
            )
        return positions

    def _annotate_targets(self, img, positions):
        for name, x, y in positions:
            cv2.circle(img, (int(x), int(y)), 8, (0, 255, 255), 2)
            cv2.putText(
                img,
                name,
                (int(x) + 10, int(y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

    def _find_nearest_square(self, squares, target_x, target_y, img_shape):
        if not squares:
            return None
        closest_dist = None
        chosen_square = None
        for rect in squares:
            (cx, cy), _, _ = rect
            dist = ((cx - target_x) ** 2 + (cy - target_y) ** 2) ** 0.5
            if closest_dist is None or dist < closest_dist:
                closest_dist = dist
                chosen_square = rect
        h, w = img_shape[:2]
        max_dist = min(w, h) * 0.35
        if closest_dist is None or closest_dist > max_dist:
            self.get_logger().warn(
                f"Target too far from {target_x},{target_y} (dist={closest_dist:.1f})"
            )
            return None
        return chosen_square

    def _record_missing_target(
        self, results, metadata, rep, pos_name, tx, ty, error: str = "no_nearby_target"
    ):
        results.append(
            {
                "timestamp": datetime.now().isoformat(),
                "config": metadata.get("config_name", "default"),
                "repetition": rep,
                "position": pos_name,
                "edge": "n/a",
                "roi_x": tx,
                "roi_y": ty,
                "roi_w": 0,
                "roi_h": 0,
                "square_cx": 0,
                "square_cy": 0,
                "mtf50_lpmm": "0",
                "mtf20_lpmm": "0",
                "mtf10_lpmm": "0",
                "edge_angle_deg": "0",
                "contrast": "0",
                "nyquist_lpmm": "0",
                "valid": "false",
                "error": error,
            }
        )

    def _draw_edge_debug(
        self, vis_img, run_dir, cv_image, x, y, w, h, pos_name, edge_name, ts
    ):
        cv2.rectangle(vis_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(
            vis_img,
            f"{edge_name}",
            (x, max(0, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
        )
        pad = 50
        full_h, full_w = cv_image.shape[:2]
        cx, cy = x + w // 2, y + h // 2
        ctx_x = max(0, cx - (w + 2 * pad) // 2)
        ctx_y = max(0, cy - (h + 2 * pad) // 2)
        ctx_w = min(w + 2 * pad, full_w - ctx_x)
        ctx_h = min(h + 2 * pad, full_h - ctx_y)
        if ctx_w > 0 and ctx_h > 0:
            context_img = cv_image[ctx_y : ctx_y + ctx_h, ctx_x : ctx_x + ctx_w].copy()
            if len(context_img.shape) == 2:
                context_img = cv2.cvtColor(context_img, cv2.COLOR_GRAY2BGR)
            rel_x, rel_y = x - ctx_x, y - ctx_y
            cv2.rectangle(context_img, (rel_x, rel_y), (rel_x + w, rel_y + h), (0, 255, 0), 1)
            p = run_dir / f"roi_{pos_name}_{edge_name}_{ts}.jpg"
            cv2.imwrite(str(p), context_img)

    def _save_mtf_statistics(self, run_dir, timestamp, results, metadata):
        stats_rows = summarize_mtf_by_group(results)
        if stats_rows:
            path = run_dir / f"mtf_verification_summary_{timestamp}.csv"
            fields = [
                "position",
                "edge",
                "count",
                "mtf50_mean",
                "mtf50_std",
                "mtf50_ci_lower",
                "mtf50_ci_upper",
                "mtf20_mean",
                "mtf20_std",
                "mtf20_ci_lower",
                "mtf20_ci_upper",
                "mtf10_mean",
                "mtf10_std",
                "mtf10_ci_lower",
                "mtf10_ci_upper",
                "angle_mean",
                "angle_std",
                "angle_ci_lower",
                "angle_ci_upper",
                "contrast_mean",
                "contrast_std",
                "contrast_ci_lower",
                "contrast_ci_upper",
            ]
            self._write_csv_with_metadata(path, metadata, fields, stats_rows)
            return path
        return None

    def _save_mtf_directional_stats(self, run_dir, timestamp, results, metadata):
        """Save aggregated MTF stats by edge direction."""
        rows = summarize_mtf_by_direction(results)
        if rows:
            path = run_dir / f"mtf_verification_directional_{timestamp}.csv"
            fields = [
                "direction",
                "count",
                "mtf50_mean",
                "mtf50_std",
                "mtf50_ci_lower",
                "mtf50_ci_upper",
                "mtf20_mean",
                "mtf20_std",
                "mtf20_ci_lower",
                "mtf20_ci_upper",
                "mtf10_mean",
                "mtf10_std",
                "mtf10_ci_lower",
                "mtf10_ci_upper",
            ]
            self._write_csv_with_metadata(path, metadata, fields, rows)
            return path
        return None

    def _save_mtf_curves(self, run_dir, timestamp, curves):
        rows = []
        for curve in curves:
            parts = curve["label"].split("-")
            pos, edge = parts[0], parts[1] if len(parts) > 1 else "unknown"
            nyq = curve["nyquist_lpmm"]
            ideals = curve.get("mtf_ideal", [0.0] * len(curve["frequencies"]))
            for f, v, ideal in zip(curve["frequencies"], curve["mtf_values"], ideals):
                if 0 <= f <= nyq * 1.5:
                    rows.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "repetition": int(curve.get("repetition", 1)),
                            "position": pos,
                            "edge": edge,
                            "frequency_lpmm": f"{f:.4f}",
                            "mtf_value": f"{v:.6f}",
                            "mtf_ideal_value": f"{ideal:.6f}",
                            "nyquist_limit": f"{nyq:.2f}",
                        }
                    )
        if rows:
            path = run_dir / f"mtf_full_curves_{timestamp}.csv"
            fields = [
                "timestamp",
                "repetition",
                "position",
                "edge",
                "frequency_lpmm",
                "mtf_value",
                "mtf_ideal_value",
                "nyquist_limit",
            ]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
