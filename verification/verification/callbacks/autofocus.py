"""Autofocus verification callbacks."""

from datetime import datetime
import json
import time

from promoc_assembly_interfaces.srv import AutoFocus
from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import ConfigurationError, ServiceCallFailedError

try:
    from camera_nodes.algorithms import AUTOFOCUS_ALGORITHMS
    from camera_nodes.plotting import VerificationPlotter
except ImportError:
    import logging

    logging.warning("Could not import camera_nodes algorithms directly. Check PYTHONPATH.")
    raise


class AutofocusVerificationCallbacks:
    """Callbacks and helper methods for autofocus verification."""

    def _save_autofocus_results(
        self, run_dir, timestamp, results, measurement_points, metadata
    ):
        """Save autofocus verification output (CSV, JSON and plot)."""
        csv_path = run_dir / f"autofocus_verification_{timestamp}.csv"
        fieldnames = [
            "timestamp",
            "algorithm",
            "focus_position_mm",
            "focus_score",
            "duration_s",
            "measurements",
            "deviation_from_ref_mm",
            "repetition",
        ]
        self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)

        if measurement_points:
            measurements_path = run_dir / f"autofocus_measurements_{timestamp}.json"
            with open(measurements_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"metadata": metadata, "measurements": measurement_points}, f, indent=2
                )

            measurements_csv_path = run_dir / f"autofocus_measurements_{timestamp}.csv"
            measurement_fields = [
                "repetition",
                "algorithm",
                "index",
                "position_mm",
                "score",
            ]
            self._write_csv_with_metadata(
                measurements_csv_path, metadata, measurement_fields, measurement_points
            )

        try:
            plotter = VerificationPlotter(self.get_logger())
            plot_path = run_dir / f"autofocus_verification_{timestamp}.png"
            if plotter.plot_autofocus_verification(results, str(plot_path)):
                self.get_logger().info(f"Autofocus plot saved: {plot_path}")
        except Exception as e:
            self.get_logger().error(f"Plotting failed: {e}")

        return csv_path

    @handle_service_errors()
    def verify_autofocus_callback(self, request, response):
        """Verification service: compare all autofocus algorithms."""
        start_time = time.time()

        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        repetitions = max(1, request.repetitions) if request.repetitions > 0 else 1

        self.get_logger().info(
            f"Autofocus Verification: range {request.start_position}-{request.end_position}mm, "
            f"repetitions={repetitions}"
        )

        if not self.af_client.wait_for_service(timeout_sec=2.0):
            raise ServiceCallFailedError("Autofocus service not available")

        metadata = self._get_measurement_metadata()
        metadata.update(
            {
                "operator": request.operator_name or "unknown",
                "notes": request.notes or "",
                "measurement_type": "autofocus_verification",
                "start_position_mm": request.start_position,
                "end_position_mm": request.end_position,
                "repetitions": repetitions,
            }
        )

        output_dir = self._get_output_dir(
            "verification/autofocus_verification", operator_name=request.operator_name
        )
        timestamp = self._get_timestamp()
        run_dir = output_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        results = []
        measurement_points = []
        reference_position = None

        algorithms_to_test = list(AUTOFOCUS_ALGORITHMS)
        if repetitions < 10:
            exhaustive_runs = {0, max(0, repetitions - 1)}
        else:
            exhaustive_runs = {0, max(0, repetitions // 2), max(0, repetitions - 1)}

        try:
            for rep in range(repetitions):
                self.get_logger().info(f"--- Repetition {rep + 1}/{repetitions} ---")
                current_list = self._get_algo_execution_order(
                    algorithms_to_test, rep in exhaustive_runs
                )

                for mode, name, _ in current_list:
                    result, measurements = self._run_single_autofocus(
                        self.af_client,
                        request,
                        mode,
                        name,
                        rep + 1,
                        run_dir,
                        timestamp,
                        reference_position,
                    )

                    results.append(result)
                    measurement_points.extend(measurements)

                    if reference_position is None and result.get("focus_position_mm") != "N/A":
                        try:
                            pos = float(result["focus_position_mm"])
                            if pos > 0:
                                reference_position = pos
                        except ValueError:
                            pass
        finally:
            if results:
                self.get_logger().info(
                    f"Saving {len(results)} collected results (partial or complete)..."
                )
                csv_path = self._save_autofocus_results(
                    run_dir, timestamp, results, measurement_points, metadata
                )
                if "csv_path" not in locals():
                    pass
        return self._create_af_response(
            response, results, reference_position, start_time, csv_path
        )

    def _get_algo_execution_order(self, all_algos, include_exhaustive):
        if include_exhaustive:
            exhaustive = [a for a in all_algos if a[1] == "exhaustive"]
            others = [a for a in all_algos if a[1] != "exhaustive"]
            return exhaustive + others
        return [a for a in all_algos if a[1] != "exhaustive"]

    def _run_single_autofocus(
        self, client, request, mode, name, rep_num, run_dir, timestamp, ref_pos
    ):
        self.get_logger().info(f"Running {name.upper()}...")
        algo_start = time.time()

        af_req = AutoFocus.Request()
        af_req.start_position = float(request.start_position)
        af_req.end_position = float(request.end_position)
        af_req.focus_mode = int(mode)
        af_req.skip_flyover = True
        af_req.save_best_image = True

        af_resp = client.call(af_req)
        duration = time.time() - algo_start

        result = {
            "timestamp": datetime.now().isoformat(),
            "algorithm": name,
            "duration_s": f"{duration:.2f}",
            "repetition": rep_num,
        }
        measurements = []

        if not af_resp.success:
            self.get_logger().error(f"{name} failed: {af_resp.status_message}")
            result.update(
                {
                    "focus_position_mm": "N/A",
                    "focus_score": "N/A",
                    "measurements": 0,
                    "deviation_from_ref_mm": "N/A",
                }
            )
        else:
            best_pos = af_resp.best_focus_position
            best_score = af_resp.best_focus_value
            deviation = 0.0
            if ref_pos is not None and best_pos is not None:
                deviation = best_pos - ref_pos

            result.update(
                {
                    "focus_position_mm": f"{best_pos:.4f}",
                    "focus_score": f"{best_score:.0f}",
                    "measurements": af_resp.total_measurements_taken,
                    "deviation_from_ref_mm": f"{deviation:.4f}",
                }
            )

            try:
                positions = list(getattr(af_resp, "measurement_positions", []) or [])
                scores = list(getattr(af_resp, "measurement_scores", []) or [])
                for idx, (p, s) in enumerate(zip(positions, scores)):
                    measurements.append(
                        {
                            "repetition": rep_num,
                            "algorithm": name,
                            "index": idx,
                            "position_mm": float(p),
                            "score": float(s),
                        }
                    )
            except Exception:
                pass

        return result, measurements

    def _create_af_response(self, response, results, ref_pos, start_time, csv_path):
        max_deviation = 0.0
        total_measurements = 0
        for r in results:
            try:
                dev = abs(float(r["deviation_from_ref_mm"]))
                if dev > max_deviation:
                    max_deviation = dev
                total_measurements += int(r["measurements"])
            except (ValueError, TypeError):
                pass

        response.success = True
        response.status_message = f"Verification complete. CSV: {csv_path}"
        response.csv_path = str(csv_path)
        response.reference_position_mm = float(ref_pos or 0)
        response.max_deviation_mm = max_deviation
        response.total_duration_seconds = time.time() - start_time
        response.total_measurements = total_measurements
        return response
