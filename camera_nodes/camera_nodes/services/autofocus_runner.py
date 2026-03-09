"""Autofocus execution runner (algorithm loop + response orchestration)."""

from __future__ import annotations

import csv
from datetime import datetime
import time

import cv2

from promoc_assembly_interfaces.srv import MoveAbsolute
from promoc_core.promoc_exceptions import ImageProcessingError

from ..algorithms import AutofocusConfig, AUTOFOCUS_ALGORITHMS
from .autofocus_response import fill_single_mode_response

_ALGO_LOOKUP = {mode: (name, cls) for mode, name, cls in AUTOFOCUS_ALGORITHMS}

COARSE_STEP_MM = 0.5
FOURSTEP_APPROACH_OFFSET_MM = 0.5
FOURSTEP_SETTLE_S = 0.3
AUTOFOCUS_MAX_STEPS_DEFAULT = 500
AUTOFOCUS_NEW_IMAGE_TIMEOUT_S = 2.0


class AutofocusRunner:
    """Execute autofocus algorithms and map outputs to service responses."""

    def __init__(self, autofocus_handler):
        self._handler = autofocus_handler

    def run_single_mode(
        self,
        mode: int,
        peak_start: float,
        peak_end: float,
        request,
        response,
        clients,
        start_time: float,
        focus_profile: dict | None = None,
    ):
        """Run a single autofocus mode and populate the ROS response."""
        self._handler._node.get_logger().info(
            f"Phase 2: Coarse + Fine in {peak_start:.1f}-{peak_end:.1f}mm, mode={mode}"
        )

        mode_name, algo_class = _ALGO_LOOKUP.get(mode, _ALGO_LOOKUP[0])
        if mode_name in ["exhaustive", "twostage"]:
            range_start = float(request.start_position)
            range_end = float(request.end_position)
        else:
            range_start = float(peak_start)
            range_end = float(peak_end)

        refinement_samples = self._handler._param_int(
            "autofocus.refinement_samples", 51
        )
        refinement_shrink_factor = self._handler._param_float(
            "autofocus.refinement_shrink_factor", 0.35
        )
        coarse_step = float((focus_profile or {}).get("coarse_step_mm", COARSE_STEP_MM))
        min_step = float(
            (focus_profile or {}).get(
                "min_step_mm", self._handler._param_float("autofocus.min_step_mm", 0.01)
            )
        )

        config = AutofocusConfig(
            start_mm=range_start,
            end_mm=range_end,
            step_mm=coarse_step,
            refinement_samples=refinement_samples,
            min_step_mm=min_step,
            shrink_factor=refinement_shrink_factor,
            use_sift_weighting=bool(
                self._handler._param_bool(
                    "autofocus.fly_over.use_sift_weighting", False
                )
            ),
        )
        algorithm = algo_class(config)

        save_best_image = bool(getattr(request, "save_best_image", False))
        settle_s = float((focus_profile or {}).get("settle_s", 0.1))
        if save_best_image:
            best_position, best_score, measurements, best_image = (
                self.run_autofocus_loop(
                    algorithm, clients, return_best_image=True, settle_s=settle_s
                )
            )
        else:
            best_position, best_score, measurements = self.run_autofocus_loop(
                algorithm, clients, settle_s=settle_s
            )
            best_image = None

        if mode_name == "fourstep" and hasattr(algorithm, "parabolic_peak_mm"):
            peak_mm = getattr(algorithm, "parabolic_peak_mm", None)
            fit_points = getattr(algorithm, "parabolic_fit_points", [])
            if peak_mm is not None:
                self._handler._node.get_logger().info(
                    f"FOURSTEP Parabolic Peak: {peak_mm:.6f}mm (fit_points={len(fit_points)}) "
                    f"final_best={float(best_position or 0.0):.6f}mm"
                )

        if best_position is not None:
            target_pos = float(best_position)
            if mode_name == "fourstep":
                pre_pos = float(best_position) - FOURSTEP_APPROACH_OFFSET_MM
                pre_pos = max(
                    float(request.start_position),
                    min(float(request.end_position), pre_pos),
                )
                target_pos = max(
                    float(request.start_position),
                    min(float(request.end_position), target_pos),
                )
                clients["move"].call(MoveAbsolute.Request(axis_position=pre_pos))
                self._handler._wait_for_axis_idle(clients)
            clients["move"].call(MoveAbsolute.Request(axis_position=target_pos))
            self._handler._wait_for_axis_idle(clients)

            if mode_name == "fourstep":
                time.sleep(FOURSTEP_SETTLE_S)
                cv_image, _ = self._handler._get_latest_cv_image()
                if cv_image is not None:
                    try:
                        prior_best_score = float(best_score)
                        final_score = float(algorithm.score_image(cv_image))
                        if final_score >= prior_best_score:
                            best_score = final_score
                            if save_best_image:
                                best_image = cv_image
                        else:
                            pre_pos = float(best_position) - FOURSTEP_APPROACH_OFFSET_MM
                            pre_pos = max(
                                float(request.start_position),
                                min(float(request.end_position), pre_pos),
                            )
                            clients["move"].call(
                                MoveAbsolute.Request(axis_position=pre_pos)
                            )
                            self._handler._wait_for_axis_idle(clients)
                            clients["move"].call(
                                MoveAbsolute.Request(axis_position=target_pos)
                            )
                            self._handler._wait_for_axis_idle(clients)

                        self._handler._node.get_logger().info(
                            f"FOURSTEP peak measurement: pos={target_pos:.3f}mm score={final_score:.0f} "
                            f"(kept_best={float(best_score):.0f})"
                        )
                    except Exception:
                        pass

        best_image_path = ""
        if save_best_image and best_image is not None:
            output_prefix = (
                f'autofocus_best_{mode_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            )
            output_dir = self._handler._get_output_dir("autofocus_results")
            output_dir.mkdir(parents=True, exist_ok=True)
            image_path = output_dir / f"{output_prefix}.jpg"
            cv2.imwrite(str(image_path), best_image)
            best_image_path = str(image_path)
            self._handler._node.get_logger().info(f"Saved best image: {image_path}")

        measurement_positions, measurement_scores = algorithm.get_measurement_series()
        duration_s = time.time() - start_time
        return fill_single_mode_response(
            response,
            mode_name=mode_name,
            best_position=best_position,
            best_score=float(best_score),
            measurements=int(measurements),
            duration_s=duration_s,
            best_image_path=best_image_path,
            measurement_positions=measurement_positions,
            measurement_scores=measurement_scores,
        )

    def run_autofocus_loop(
        self, algorithm, clients, return_best_image: bool = False, settle_s: float = 0.1
    ) -> tuple:
        """Run autofocus state machine until completion or timeout."""
        current_pos = float(algorithm.start())
        clients["move"].call(MoveAbsolute.Request(axis_position=current_pos))
        self._handler._wait_for_axis_idle(clients)
        time.sleep(max(0.0, float(settle_s)))

        best_position = None
        best_score = 0.0
        best_image = None
        best_current_score = -1.0
        measurements = 0

        max_steps = AUTOFOCUS_MAX_STEPS_DEFAULT
        try:
            step_size = algorithm.get_scan_step_mm()
            if step_size and algorithm.config.end_mm > algorithm.config.start_mm:
                max_steps = max(
                    max_steps,
                    int(
                        (algorithm.config.end_mm - algorithm.config.start_mm)
                        / step_size
                    )
                    + 5,
                )
        except Exception:
            pass

        last_timestamp = 0
        for _ in range(max_steps):
            cv_image, ts = self._handler._wait_for_new_image(
                last_timestamp, timeout=AUTOFOCUS_NEW_IMAGE_TIMEOUT_S
            )
            if cv_image is None:
                self._handler._node.get_logger().error(
                    "Timeout waiting for new image in AF loop - Stream stalled?"
                )
                raise ImageProcessingError(
                    "Autofocus failed: Camera stream stalled (no new images)"
                )
            if ts is not None:
                last_timestamp = ts

            result = algorithm.process_image(current_pos, cv_image)
            best_score = float(result.best_score)
            measurements += 1

            if return_best_image and result.current_score is not None:
                if result.current_score > best_current_score:
                    best_current_score = float(result.current_score)
                    best_image = cv_image.copy()

            phase = getattr(result, "phase", None)
            phase_name = phase.name if phase is not None else "UNKNOWN"
            self._handler._node.get_logger().info(
                f"AF {phase_name}: pos={current_pos:.3f}mm score={float(result.current_score):.0f} "
                f"best={best_score:.0f}"
            )

            if result.finished:
                best_position = result.best_position_mm
                self._handler._node.get_logger().info(
                    f"AF complete: best_pos={float(best_position or 0.0):.3f}mm "
                    f"best_score={best_score:.0f} measurements={measurements}"
                )
                break

            if result.next_position_mm is None:
                break

            next_pos = float(result.next_position_mm)
            clients["move"].call(MoveAbsolute.Request(axis_position=next_pos))
            self._handler._wait_for_axis_idle(clients)
            time.sleep(max(0.0, float(settle_s)))
            current_pos = next_pos

        if best_position is None:
            fallback_pos, fallback_score = algorithm.get_best_result()
            if fallback_pos is not None:
                best_position = fallback_pos
                best_score = fallback_score

        if return_best_image:
            return best_position, best_score, measurements, best_image
        return best_position, best_score, measurements

    def run_comparison(
        self,
        peak_start: float,
        peak_end: float,
        request,
        response,
        clients,
        start_time: float,
        focus_profile: dict | None = None,
    ):
        """Run all autofocus algorithms and persist comparison CSV."""
        self._handler._node.get_logger().info("Comparison Test: Running all 5 modes...")
        results: dict[str, dict[str, float | int]] = {}

        refinement_samples = self._handler._param_int(
            "autofocus.refinement_samples", 51
        )
        refinement_shrink_factor = self._handler._param_float(
            "autofocus.refinement_shrink_factor", 0.35
        )
        coarse_step = float((focus_profile or {}).get("coarse_step_mm", COARSE_STEP_MM))
        min_step = float(
            (focus_profile or {}).get(
                "min_step_mm", self._handler._param_float("autofocus.min_step_mm", 0.01)
            )
        )
        settle_s = float((focus_profile or {}).get("settle_s", 0.1))

        for mode, name, algo_class in AUTOFOCUS_ALGORITHMS:
            self._handler._node.get_logger().info(
                f"--- Running {name.upper()} (mode {mode}) ---"
            )
            config = AutofocusConfig(
                start_mm=float(peak_start),
                end_mm=float(peak_end),
                step_mm=coarse_step,
                refinement_samples=refinement_samples,
                min_step_mm=min_step,
                shrink_factor=refinement_shrink_factor,
                use_sift_weighting=bool(
                    self._handler._param_bool(
                        "autofocus.fly_over.use_sift_weighting", False
                    )
                ),
            )
            algorithm = algo_class(config)
            mode_start = time.time()
            best_pos, best_score, measurements = self.run_autofocus_loop(
                algorithm, clients, settle_s=settle_s
            )
            mode_duration = time.time() - mode_start
            results[name] = {
                "position": float(best_pos or 0.0),
                "score": float(best_score),
                "duration": float(mode_duration),
                "measurements": int(measurements),
            }
            self._handler._node.get_logger().info(
                f"{name}: pos={float(best_pos or 0.0):.3f}mm, score={float(best_score):.0f}, "
                f"time={mode_duration:.1f}s"
            )

        output_dir = self._handler._get_output_dir("autofocus_comparison")
        csv_path = output_dir / f"comparison_{self._handler._get_timestamp()}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["# Autofocus Comparison Test"])
            writer.writerow(
                [f"# Range: {peak_start:.1f}-{peak_end:.1f}mm (after fly-over)"]
            )
            writer.writerow([])
            writer.writerow(
                ["algorithm", "position_mm", "score", "duration_s", "measurements"]
            )
            for algo_name, data in results.items():
                writer.writerow(
                    [
                        algo_name,
                        f"{float(data['position']):.4f}",
                        f"{float(data['score']):.0f}",
                        f"{float(data['duration']):.2f}",
                        int(data["measurements"]),
                    ]
                )

        best_algo = max(results.keys(), key=lambda key: float(results[key]["score"]))
        best = results[best_algo]
        if float(best["position"]) > 0:
            clients["move"].call(
                MoveAbsolute.Request(axis_position=float(best["position"]))
            )
            self._handler._wait_for_axis_idle(clients)

        response.success = True
        response.status_message = (
            f"Comparison: Best={best_algo} at {float(best['position']):.3f}mm "
            f"(score={float(best['score']):.0f}). CSV: {csv_path}"
        )
        response.best_focus_position = float(best["position"])
        response.best_focus_value = float(best["score"])
        response.total_measurements_taken = int(
            sum(int(item["measurements"]) for item in results.values())
        )
        response.duration_seconds = time.time() - start_time

        self._handler._node.get_logger().info(f"Comparison results saved to {csv_path}")
        return response

