"""Correlation verification callbacks."""

import time

import numpy as np

from promoc_assembly_interfaces.srv import GetOperationStatus, MoveAbsolute
from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
    ServiceCallFailedError,
)
from verification.algorithms.mtf_verification_stats import estimate_peak_position

from camera_nodes.algorithms.focus_metrics import tenengrad as tenengrad_metric
from camera_nodes.plotting import VerificationPlotter


class CorrelationVerificationCallbacks:
    """Callbacks and helper methods for AF/MTF correlation scans."""

    @handle_service_errors()
    def verify_correlation_callback(self, request, response):
        """Scan a range and return correlation between AF and MTF peaks."""
        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        step_size = request.step_size if request.step_size > 0 else 0.5
        positions = np.arange(request.start_position, request.end_position + step_size, step_size)

        self.get_logger().info(
            f"Correlation Verification: {request.start_position}-{request.end_position}mm "
            f"(step={step_size}mm, {len(positions)} points)"
        )

        if not self.move_client.wait_for_service(timeout_sec=2.0) or not self.status_client.wait_for_service(
            timeout_sec=2.0
        ):
            raise ServiceCallFailedError("Axis services not available")

        output_dir = self._get_output_dir("verification/correlation")
        timestamp = self._get_timestamp()
        run_dir = output_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        analyzer = self._create_mtf_analyzer()
        metadata = self._get_measurement_metadata()
        metadata.update(
            {
                "type": "correlation_scan",
                "start": request.start_position,
                "end": request.end_position,
                "step": step_size,
            }
        )

        results = []

        try:
            for pos in positions:
                self._move_axis_and_wait(pos)
                time.sleep(request.settle_time if request.settle_time > 0 else 0.5)

                cv_image = self._get_latest_cv_image()
                if cv_image is None:
                    self.get_logger().warn(f"No image at Z={pos:.2f}")
                    continue

                tenengrad = tenengrad_metric(cv_image)

                h, w = cv_image.shape[:2]
                cx, cy = w // 2, h // 2
                cw, ch = 300, 300
                roi_rect = (
                    max(0, cx - cw // 2),
                    max(0, cy - ch // 2),
                    min(w, cx + cw // 2),
                    min(h, cy + ch // 2),
                )

                mtf_res = analyzer.compute_mtf(
                    cv_image, roi=roi_rect, debug_label="correlation_center"
                )

                mtf_val = mtf_res.mtf50 if mtf_res.valid else 0.0
                if mtf_res.valid and mtf_res.warning_msg:
                    self.get_logger().warn(f"MTF warning (correlation): {mtf_res.warning_msg}")

                self.get_logger().info(f"Z={pos:.2f}: Ten={tenengrad:.1f}, MTF50={mtf_val:.3f}")

                results.append(
                    {
                        "position_mm": float(pos),
                        "tenengrad": float(tenengrad),
                        "mtf50_lpmm": float(mtf_val),
                        "valid": mtf_res.valid,
                    }
                )
        finally:
            if results:
                csv_path = run_dir / f"correlation_{timestamp}.csv"
                self._write_csv_with_metadata(
                    csv_path,
                    metadata,
                    ["position_mm", "tenengrad", "mtf50_lpmm", "valid"],
                    results,
                )

        if not results:
            raise ImageProcessingError("No valid data collected during scan")

        valid_mtf_rows = [
            row for row in results if row.get("valid") and row.get("mtf50_lpmm", 0.0) > 0.0
        ]
        if not valid_mtf_rows:
            raise ImageProcessingError("No valid MTF data collected during scan")

        af_peak = estimate_peak_position(
            results, position_key="position_mm", value_key="tenengrad"
        )
        mtf_peak = estimate_peak_position(
            valid_mtf_rows, position_key="position_mm", value_key="mtf50_lpmm"
        )

        if af_peak is None:
            af_peak = max(results, key=lambda x: x["tenengrad"])["position_mm"]
        if mtf_peak is None:
            mtf_peak = max(valid_mtf_rows, key=lambda x: x["mtf50_lpmm"])["position_mm"]

        peak_shift = float(af_peak) - float(mtf_peak)

        try:
            plotter = VerificationPlotter(self.get_logger())
            plot_path = run_dir / f"correlation_plot_{timestamp}.png"
            plotter.plot_correlation_verification(
                {
                    "data": results,
                    "peak_shift": peak_shift,
                    "max_af_pos": float(af_peak),
                    "max_mtf_pos": float(mtf_peak),
                },
                str(plot_path),
            )
        except Exception:
            pass

        response.success = True
        response.status_message = f"Correlation done. Shift: {peak_shift:.4f}mm"
        response.peak_shift = peak_shift
        response.max_af_pos = float(af_peak)
        response.max_mtf_pos = float(mtf_peak)

        return response

    def _move_axis_and_wait(self, pos_mm):
        req = MoveAbsolute.Request()
        req.axis_position = float(pos_mm)
        future = self.move_client.call_async(req)

        start = time.time()
        while not future.done():
            if time.time() - start > 10.0:
                raise ServiceCallFailedError("Move service timeout")
            time.sleep(0.05)

        res = future.result()
        if not res or not res.success:
            raise ServiceCallFailedError(f"Move to {pos_mm} failed")

        start_idle = time.time()
        while time.time() - start_idle < 30.0:
            stat_future = self.status_client.call_async(GetOperationStatus.Request())
            while not stat_future.done():
                time.sleep(0.01)
            stat = stat_future.result()
            if stat and stat.operation_status == "idle":
                return
            time.sleep(0.05)

        raise ServiceCallFailedError("Timeout waiting for axis idle")
