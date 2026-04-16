"""Autofocus handler with fly-over detection and execution support."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import time

import cv2

from promoc_assembly_interfaces.srv import (
    GetOperationStatus,
    GetPosition,
    GetVelocityParameters,
    JogAxis,
    MoveAbsolute,
    SetVelocityParameters,
    Stop,
)
from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
    ServiceError,
)

from ..algorithms import AUTOFOCUS_ALGORITHMS, AutofocusConfig
from ..models import FocusProfileBuilder
from .base import CallbackBase
from .fly_over import FlyOverDetector

_ALGO_LOOKUP = {mode: (name, cls) for mode, name, cls in AUTOFOCUS_ALGORITHMS}
AXIS_PREFIX = "/promoc/linear_axis/lts300_x_axis"

COARSE_STEP_MM = 0.5
FOURSTEP_APPROACH_OFFSET_MM = 0.5
FOURSTEP_SETTLE_S = 0.3
AUTOFOCUS_MAX_STEPS_DEFAULT = 500
AUTOFOCUS_NEW_IMAGE_TIMEOUT_S = 2.0


@dataclass(frozen=True)
class _SingleModeRunPlan:
    """Resolved mode-specific inputs for one autofocus run."""

    mode_name: str
    algorithm: object
    settle_s: float
    save_best_image: bool


@dataclass
class _AutofocusLoopState:
    """Mutable execution state for one autofocus loop."""

    current_pos: float
    last_timestamp: int = 0
    best_position: float | None = None
    best_score: float = 0.0
    best_image: object | None = None
    best_current_score: float = -1.0
    measurements: int = 0


class AxisClientManager:
    """Build and cache linear-axis service clients for autofocus workflows."""

    def __init__(self, callback_handler):
        self._handler = callback_handler
        self._cached_axis_clients: dict[str, object] = {}

    def get_all_axis_clients(self) -> dict[str, object]:
        """Create or return cached service clients for the configured linear axis."""
        if self._cached_axis_clients:
            return self._cached_axis_clients

        node = self._handler._node

        clients = {
            "move": node.create_client(MoveAbsolute, f"{AXIS_PREFIX}/move_absolute"),
            "jog": node.create_client(JogAxis, f"{AXIS_PREFIX}/jog_axis"),
            "status": node.create_client(
                GetOperationStatus, f"{AXIS_PREFIX}/get_operation_status"
            ),
            "position": node.create_client(GetPosition, f"{AXIS_PREFIX}/get_position"),
            "stop": node.create_client(Stop, f"{AXIS_PREFIX}/stop"),
            "get_vel": node.create_client(
                GetVelocityParameters, f"{AXIS_PREFIX}/get_velocity_parameters"
            ),
            "set_vel": node.create_client(
                SetVelocityParameters, f"{AXIS_PREFIX}/set_velocity_parameters"
            ),
        }

        for name, client in clients.items():
            if not client.wait_for_service(timeout_sec=2.0):
                raise ServiceError(f"Linear axis {name} service not available")

        self._cached_axis_clients = clients
        return clients

    def wait_for_axis_idle(self, clients: dict[str, object]) -> None:
        """Block until axis reports idle or raise on error states."""
        while True:
            response = clients["status"].call(GetOperationStatus.Request())
            if response and response.operation_status == "idle":
                return
            if response and response.operation_status in ["error", "emergency_stop"]:
                raise ServiceError(f"Axis error: {response.status_message}")
            time.sleep(0.05)

    def get_position(self, clients: dict[str, object]) -> float:
        """Read axis position from topic cache first, service as fallback."""
        node = self._handler._node
        if hasattr(node, "current_axis_position") and node.current_axis_position >= 0:
            return float(node.current_axis_position)

        response = clients["position"].call(GetPosition.Request())
        if response and response.success:
            return float(response.axis_position)
        return -1.0


def fill_single_mode_response(
    response,
    *,
    mode_name: str,
    best_position: float | None,
    best_score: float,
    measurements: int,
    duration_s: float,
    measurement_positions: list[float],
    measurement_scores: list[float],
    best_image_path: str = "",
):
    """Populate AutoFocus response fields for a single autofocus run."""
    response.success = best_position is not None
    response.status_message = (
        f"{mode_name}: pos={float(best_position or 0.0):.3f}mm, "
        f"score={float(best_score):.0f}"
    )
    response.best_focus_position = float(best_position or 0.0)
    response.best_focus_value = float(best_score)
    response.total_measurements_taken = int(measurements)
    response.duration_seconds = float(duration_s)
    response.best_image_path = str(best_image_path or "")
    response.measurement_positions = [float(value) for value in measurement_positions]
    response.measurement_scores = [float(value) for value in measurement_scores]
    return response


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

        run_plan = self._build_single_mode_run_plan(
            mode=mode,
            peak_start=peak_start,
            peak_end=peak_end,
            request=request,
            focus_profile=focus_profile,
        )
        best_position, best_score, measurements, best_image = self._execute_single_mode(
            run_plan, clients
        )
        self._log_fourstep_peak_fit(
            run_plan.mode_name, run_plan.algorithm, best_position
        )

        if best_position is not None:
            target_pos = self._move_to_measurement_position(
                run_plan.mode_name,
                best_position,
                request,
                clients,
            )
            best_score, best_image = self._confirm_measurement_position(
                run_plan.mode_name,
                run_plan.algorithm,
                target_pos,
                best_position,
                best_score,
                best_image,
                request,
                clients,
                run_plan.save_best_image,
            )

        best_image_path = self._save_best_image(
            run_plan.mode_name,
            best_image,
            run_plan.save_best_image,
        )

        measurement_positions, measurement_scores = (
            run_plan.algorithm.get_measurement_series()
        )
        duration_s = time.time() - start_time
        return fill_single_mode_response(
            response,
            mode_name=run_plan.mode_name,
            best_position=best_position,
            best_score=float(best_score),
            measurements=int(measurements),
            duration_s=duration_s,
            best_image_path=best_image_path,
            measurement_positions=measurement_positions,
            measurement_scores=measurement_scores,
        )

    def _build_single_mode_run_plan(
        self,
        *,
        mode: int,
        peak_start: float,
        peak_end: float,
        request,
        focus_profile: dict | None,
    ) -> _SingleModeRunPlan:
        """Resolve mode-specific range, config, and runtime options."""
        mode_name, algo_class = self._resolve_algorithm(mode)
        range_start, range_end = self._resolve_scan_window(
            mode_name, peak_start, peak_end, request
        )
        config = self._build_algorithm_config(
            range_start=range_start,
            range_end=range_end,
            focus_profile=focus_profile,
        )
        return _SingleModeRunPlan(
            mode_name=mode_name,
            algorithm=algo_class(config),
            settle_s=self._resolve_settle_time(focus_profile),
            save_best_image=bool(getattr(request, 'save_best_image', False)),
        )

    def _resolve_algorithm(self, mode: int) -> tuple[str, object]:
        """Map the wire-level mode id to the configured algorithm class."""
        return _ALGO_LOOKUP.get(mode, _ALGO_LOOKUP[0])

    def _resolve_scan_window(
        self,
        mode_name: str,
        peak_start: float,
        peak_end: float,
        request,
    ) -> tuple[float, float]:
        """Choose full-range or fly-over peak window based on the algorithm."""
        if mode_name in {'exhaustive', 'twostage'}:
            return float(request.start_position), float(request.end_position)
        return float(peak_start), float(peak_end)

    def _build_algorithm_config(
        self,
        *,
        range_start: float,
        range_end: float,
        focus_profile: dict | None,
    ) -> AutofocusConfig:
        """Build shared algorithm config from profile and ROS parameters."""
        refinement_samples = self._handler._param_int(
            'autofocus.refinement_samples', 51
        )
        refinement_shrink_factor = self._handler._param_float(
            'autofocus.refinement_shrink_factor', 0.35
        )
        coarse_step = float((focus_profile or {}).get('coarse_step_mm', COARSE_STEP_MM))
        min_step = float(
            (focus_profile or {}).get(
                'min_step_mm', self._handler._param_float('autofocus.min_step_mm', 0.01)
            )
        )
        return AutofocusConfig(
            start_mm=float(range_start),
            end_mm=float(range_end),
            step_mm=coarse_step,
            refinement_samples=refinement_samples,
            min_step_mm=min_step,
            shrink_factor=refinement_shrink_factor,
            use_sift_weighting=bool(
                self._handler._param_bool('autofocus.fly_over.use_sift_weighting', False)
            ),
        )

    def _resolve_settle_time(self, focus_profile: dict | None) -> float:
        """Resolve the dwell time between axis moves and frame acquisition."""
        return float((focus_profile or {}).get('settle_s', 0.1))

    def _execute_single_mode(
        self,
        run_plan: _SingleModeRunPlan,
        clients,
    ) -> tuple[float | None, float, int, object | None]:
        """Run the selected autofocus algorithm, optionally tracking the best image."""
        if run_plan.save_best_image:
            best_position, best_score, measurements, best_image = (
                self.run_autofocus_loop(
                    run_plan.algorithm,
                    clients,
                    return_best_image=True,
                    settle_s=run_plan.settle_s,
                )
            )
            return best_position, best_score, measurements, best_image

        best_position, best_score, measurements = self.run_autofocus_loop(
            run_plan.algorithm,
            clients,
            settle_s=run_plan.settle_s,
        )
        return best_position, best_score, measurements, None

    def _log_fourstep_peak_fit(
        self,
        mode_name: str,
        algorithm,
        best_position: float | None,
    ) -> None:
        """Emit the final parabolic fit summary from the four-step strategy."""
        if mode_name != 'fourstep' or not hasattr(algorithm, 'parabolic_peak_mm'):
            return

        peak_mm = getattr(algorithm, 'parabolic_peak_mm', None)
        fit_points = getattr(algorithm, 'parabolic_fit_points', [])
        if peak_mm is None:
            return

        self._handler._node.get_logger().info(
            f'FOURSTEP Parabolic Peak: {peak_mm:.6f}mm (fit_points={len(fit_points)}) '
            f'final_best={float(best_position or 0.0):.6f}mm'
        )

    def _move_to_measurement_position(
        self,
        mode_name: str,
        best_position: float,
        request,
        clients,
    ) -> float:
        """Move the axis to the final measurement point, preserving four-step approach."""
        target_pos = self._clamp_request_range(float(best_position), request)
        if mode_name == 'fourstep':
            pre_pos = self._clamp_request_range(
                float(best_position) - FOURSTEP_APPROACH_OFFSET_MM,
                request,
            )
            self._move_axis(clients, pre_pos)
        self._move_axis(clients, target_pos)
        return target_pos

    def _confirm_measurement_position(
        self,
        mode_name: str,
        algorithm,
        target_pos: float,
        best_position: float,
        best_score: float,
        best_image,
        request,
        clients,
        save_best_image: bool,
    ) -> tuple[float, object | None]:
        """Optionally re-measure the final point after the algorithm has completed."""
        if mode_name != 'fourstep':
            return float(best_score), best_image

        time.sleep(FOURSTEP_SETTLE_S)
        cv_image, _ = self._handler._get_latest_cv_image()
        if cv_image is None:
            return float(best_score), best_image

        try:
            prior_best_score = float(best_score)
            final_score = float(algorithm.score_image(cv_image))
            if final_score >= prior_best_score:
                best_score = final_score
                if save_best_image:
                    best_image = cv_image
            else:
                pre_pos = self._clamp_request_range(
                    float(best_position) - FOURSTEP_APPROACH_OFFSET_MM,
                    request,
                )
                self._move_axis(clients, pre_pos)
                self._move_axis(clients, target_pos)

            self._handler._node.get_logger().info(
                f'FOURSTEP peak measurement: pos={target_pos:.3f}mm '
                f'score={final_score:.0f} (kept_best={float(best_score):.0f})'
            )
        except Exception:
            pass

        return float(best_score), best_image

    def _save_best_image(
        self,
        mode_name: str,
        best_image,
        save_best_image: bool,
    ) -> str:
        """Persist the best image when the caller requested a capture artifact."""
        if not save_best_image or best_image is None:
            return ''

        output_prefix = (
            f'autofocus_best_{mode_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        )
        output_dir = self._handler._get_output_dir('autofocus_results')
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = output_dir / f'{output_prefix}.jpg'
        cv2.imwrite(str(image_path), best_image)
        self._handler._node.get_logger().info(f'Saved best image: {image_path}')
        return str(image_path)

    def _clamp_request_range(self, position_mm: float, request) -> float:
        """Clamp a candidate axis position to the request travel bounds."""
        return max(
            float(request.start_position),
            min(float(request.end_position), float(position_mm)),
        )

    def _move_axis(self, clients, target_pos: float) -> None:
        """Move the axis and wait for the motion controller to go idle."""
        clients['move'].call(MoveAbsolute.Request(axis_position=float(target_pos)))
        self._handler._wait_for_axis_idle(clients)

    def run_autofocus_loop(
        self, algorithm, clients, return_best_image: bool = False, settle_s: float = 0.1
    ) -> tuple:
        """Run autofocus state machine until completion or timeout."""
        state = self._start_autofocus_loop(algorithm, clients, settle_s)
        max_steps = self._calculate_max_steps(algorithm)

        for _ in range(max_steps):
            cv_image, state.last_timestamp = self._wait_for_next_autofocus_frame(
                state.last_timestamp
            )
            result = algorithm.process_image(state.current_pos, cv_image)
            self._record_autofocus_result(
                state,
                result,
                cv_image,
                return_best_image=return_best_image,
            )
            self._log_autofocus_result(state.current_pos, result, state.best_score)

            if result.finished:
                state.best_position = result.best_position_mm
                self._log_autofocus_completion(state)
                break

            if result.next_position_mm is None:
                break

            state.current_pos = self._advance_autofocus_position(
                clients,
                result.next_position_mm,
                settle_s,
            )

        if state.best_position is None:
            fallback_pos, fallback_score = algorithm.get_best_result()
            if fallback_pos is not None:
                state.best_position = fallback_pos
                state.best_score = fallback_score

        if return_best_image:
            return (
                state.best_position,
                state.best_score,
                state.measurements,
                state.best_image,
            )
        return state.best_position, state.best_score, state.measurements

    def _start_autofocus_loop(
        self,
        algorithm,
        clients,
        settle_s: float,
    ) -> _AutofocusLoopState:
        """Move to the algorithm start position and initialize loop bookkeeping."""
        current_pos = float(algorithm.start())
        self._move_axis(clients, current_pos)
        time.sleep(max(0.0, float(settle_s)))
        return _AutofocusLoopState(current_pos=current_pos)

    def _calculate_max_steps(self, algorithm) -> int:
        """Estimate an upper bound for the autofocus iteration count."""
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
        return max_steps

    def _wait_for_next_autofocus_frame(
        self,
        last_timestamp: int,
    ) -> tuple[object, int]:
        """Wait for the next camera frame and fail loudly on stream stalls."""
        cv_image, ts = self._handler._wait_for_new_image(
            last_timestamp, timeout=AUTOFOCUS_NEW_IMAGE_TIMEOUT_S
        )
        if cv_image is None:
            self._handler._node.get_logger().error(
                'Timeout waiting for new image in AF loop - Stream stalled?'
            )
            raise ImageProcessingError(
                'Autofocus failed: Camera stream stalled (no new images)'
            )
        next_timestamp = last_timestamp if ts is None else int(ts)
        return cv_image, next_timestamp

    def _record_autofocus_result(
        self,
        state: _AutofocusLoopState,
        result,
        cv_image,
        *,
        return_best_image: bool,
    ) -> None:
        """Update loop state from one autofocus algorithm result."""
        state.best_score = float(result.best_score)
        state.measurements += 1

        if not return_best_image or result.current_score is None:
            return

        current_score = float(result.current_score)
        if current_score > state.best_current_score:
            state.best_current_score = current_score
            state.best_image = cv_image.copy()

    def _log_autofocus_result(
        self,
        current_pos: float,
        result,
        best_score: float,
    ) -> None:
        """Emit one progress log line for the autofocus loop."""
        phase = getattr(result, 'phase', None)
        phase_name = phase.name if phase is not None else 'UNKNOWN'
        self._handler._node.get_logger().info(
            f'AF {phase_name}: pos={current_pos:.3f}mm '
            f'score={float(result.current_score):.0f} best={float(best_score):.0f}'
        )

    def _log_autofocus_completion(self, state: _AutofocusLoopState) -> None:
        """Emit the final summary line when the loop reports completion."""
        self._handler._node.get_logger().info(
            f'AF complete: best_pos={float(state.best_position or 0.0):.3f}mm '
            f'best_score={float(state.best_score):.0f} measurements={state.measurements}'
        )

    def _advance_autofocus_position(
        self,
        clients,
        next_position_mm: float,
        settle_s: float,
    ) -> float:
        """Move to the next requested autofocus position and dwell before capture."""
        next_pos = float(next_position_mm)
        self._move_axis(clients, next_pos)
        time.sleep(max(0.0, float(settle_s)))
        return next_pos

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
        self._handler._node.get_logger().info('Comparison Test: Running all 5 modes...')
        results: dict[str, dict[str, float | int]] = {}

        settle_s = self._resolve_settle_time(focus_profile)

        for mode, name, algo_class in AUTOFOCUS_ALGORITHMS:
            self._handler._node.get_logger().info(
                f'--- Running {name.upper()} (mode {mode}) ---'
            )
            config = self._build_algorithm_config(
                range_start=float(peak_start),
                range_end=float(peak_end),
                focus_profile=focus_profile,
            )
            algorithm = algo_class(config)
            mode_start = time.time()
            best_pos, best_score, measurements = self.run_autofocus_loop(
                algorithm, clients, settle_s=settle_s
            )
            mode_duration = time.time() - mode_start
            results[name] = {
                'position': float(best_pos or 0.0),
                'score': float(best_score),
                'duration': float(mode_duration),
                'measurements': int(measurements),
            }
            self._handler._node.get_logger().info(
                f'{name}: pos={float(best_pos or 0.0):.3f}mm, '
                f'score={float(best_score):.0f}, time={mode_duration:.1f}s'
            )

        output_dir = self._handler._get_output_dir('autofocus_comparison')
        csv_path = output_dir / f'comparison_{self._handler._get_timestamp()}.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['# Autofocus Comparison Test'])
            writer.writerow(
                [f'# Range: {peak_start:.1f}-{peak_end:.1f}mm (after fly-over)']
            )
            writer.writerow([])
            writer.writerow(
                ['algorithm', 'position_mm', 'score', 'duration_s', 'measurements']
            )
            for algo_name, data in results.items():
                writer.writerow(
                    [
                        algo_name,
                        f"{float(data['position']):.4f}",
                        f"{float(data['score']):.0f}",
                        f"{float(data['duration']):.2f}",
                        int(data['measurements']),
                    ]
                )

        best_algo = max(results.keys(), key=lambda key: float(results[key]['score']))
        best = results[best_algo]
        if float(best['position']) > 0:
            clients['move'].call(
                MoveAbsolute.Request(axis_position=float(best['position']))
            )
            self._handler._wait_for_axis_idle(clients)

        response.success = True
        response.status_message = (
            f"Comparison: Best={best_algo} at {float(best['position']):.3f}mm "
            f"(score={float(best['score']):.0f}). CSV: {csv_path}"
        )
        response.best_focus_position = float(best['position'])
        response.best_focus_value = float(best['score'])
        response.total_measurements_taken = int(
            sum(int(item['measurements']) for item in results.values())
        )
        response.duration_seconds = time.time() - start_time

        self._handler._node.get_logger().info(f'Comparison results saved to {csv_path}')
        return response


class AutofocusHandler(CallbackBase):
    """Handler for autofocus with fly-over detection."""

    def __init__(self, node, camera_driver):
        super().__init__(node, camera_driver)
        self._axis_clients = AxisClientManager(self)
        self._runner = AutofocusRunner(self)

    def _build_focus_profile(self, request) -> dict:
        """Build objective-aware autofocus profile for fly-over and refinement."""
        return FocusProfileBuilder(self._node).build(request).as_dict()

    @handle_service_errors()
    def autofocus_callback(self, request, response):
        """Run autofocus: optional fly-over plus selected refinement mode."""
        mode = getattr(request, "focus_mode", getattr(request, "refinement_mode", 0))
        start_time = time.time()
        focus_profile = self._build_focus_profile(request)

        self._node.get_logger().info(
            f"Autofocus: range {request.start_position}-{request.end_position}mm, mode={mode}"
        )
        mag_label = (
            f'{focus_profile["magnification_x"]:.2f}x'
            if focus_profile["magnification_x"] is not None
            else "unknown"
        )
        self._node.get_logger().info(
            f'Objective profile: objective="{focus_profile["objective"]}" '
            f"mag={mag_label} beamsplitter={focus_profile['beamsplitter']} "
            f"profile={focus_profile['profile_source']} "
            f"scan_speed={focus_profile['scan_speed_mm_s']:.2f}mm/s "
            f"axis_scale={focus_profile['axis_speed_scale']:.3f} "
            f"max_sample_step={focus_profile['max_sample_step_mm']:.3f}mm "
            f"coarse_step={focus_profile['coarse_step_mm']:.3f}mm "
            f"min_step={focus_profile['min_step_mm']:.3f}mm "
            f"settle={focus_profile['settle_s']:.2f}s"
        )

        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        clients = self._get_all_axis_clients()
        skip_flyover = getattr(request, "skip_flyover", False)
        if skip_flyover:
            self._node.get_logger().info("Skipping fly-over, using full range.")
            peak_start = float(request.start_position)
            peak_end = float(request.end_position)
        else:
            self._node.get_logger().info("Phase 1: Fly-Over Detection...")
            peak_start, peak_end, max_stddev = self._fly_over_detection(
                request.start_position,
                request.end_position,
                clients,
                focus_profile,
            )
            if peak_start is None or peak_end is None:
                raise ImageProcessingError("No target detected during fly-over")
            self._node.get_logger().info(
                f"Peak detected: {peak_start:.1f}-{peak_end:.1f}mm "
                f"(max_stddev={max_stddev:.1f})"
            )

        return self._run_single_mode(
            mode,
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )

    def _get_all_axis_clients(self):
        return self._axis_clients.get_all_axis_clients()

    def _wait_for_axis_idle(self, clients):
        self._axis_clients.wait_for_axis_idle(clients)

    def _get_position(self, clients) -> float:
        return self._axis_clients.get_position(clients)

    def _fly_over_detection(
        self,
        start_pos: float,
        end_pos: float,
        clients,
        focus_profile: dict | None = None,
    ) -> tuple:
        """Fast fly-over scan for target detection."""
        detector = FlyOverDetector(
            node=self._node,
            get_latest_cv_image=self._get_latest_cv_image,
            get_center_roi=self._get_center_roi,
            wait_for_axis_idle=self._wait_for_axis_idle,
            get_position=self._get_position,
        )
        result = detector.detect(
            start_pos=float(start_pos),
            end_pos=float(end_pos),
            clients=clients,
            focus_profile=focus_profile,
        )
        return result.peak_start, result.peak_end, result.max_stddev

    def _run_single_mode(
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
        return self._runner.run_single_mode(
            mode,
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )

    def _run_autofocus_loop(
        self, af, clients, return_best_image: bool = False, settle_s: float = 0.1
    ) -> tuple:
        return self._runner.run_autofocus_loop(
            af,
            clients,
            return_best_image=return_best_image,
            settle_s=settle_s,
        )

    def _run_comparison(
        self,
        peak_start: float,
        peak_end: float,
        request,
        response,
        clients,
        start_time: float,
        focus_profile: dict | None = None,
    ):
        return self._runner.run_comparison(
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )

    @handle_service_errors()
    def autofocus_comparison_callback(self, request, response):
        """Run all autofocus modes sequentially and export a comparison CSV."""
        start_time = time.time()

        self._node.get_logger().info(
            f"Comparison Test: range {request.start_position}-{request.end_position}mm"
        )

        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        clients = self._get_all_axis_clients()
        focus_profile = self._build_focus_profile(request)

        self._node.get_logger().info("Phase 1: Fly-Over Detection...")
        peak_start, peak_end, max_stddev = self._fly_over_detection(
            request.start_position,
            request.end_position,
            clients,
            focus_profile,
        )
        if peak_start is None or peak_end is None:
            raise ImageProcessingError("No target detected during fly-over")

        self._node.get_logger().info(
            f"Peak: {peak_start:.1f}-{peak_end:.1f}mm (max_stddev={max_stddev:.1f})"
        )

        return self._run_comparison(
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )
