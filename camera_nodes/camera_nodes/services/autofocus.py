"""Autofocus handler with fly-over detection and execution support."""

from __future__ import annotations

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
from ..preview import is_bayer_encoding, raw_array_to_bgr8_preview
from .base import CallbackBase
from .fly_over import FlyOverDetector

_ALGO_LOOKUP = {mode: (name, cls) for mode, name, cls in AUTOFOCUS_ALGORITHMS}
AXIS_PREFIX = "/promoc/linear_axis/lts300_x_axis"

COARSE_STEP_MM = 0.5
FOURSTEP_APPROACH_OFFSET_MM = 0.5
FOURSTEP_SETTLE_S = 0.3
AUTOFOCUS_MAX_STEPS_DEFAULT = 500
AUTOFOCUS_NEW_IMAGE_TIMEOUT_S = 2.0
AUTOFOCUS_FRESH_FRAME_WAIT_S = 0.4
AUTOFOCUS_AXIS_POSITION_TOLERANCE_MM = 0.05
AUTOFOCUS_AXIS_WAIT_TIMEOUT_S = 60.0
AUTOFOCUS_MOVE_RESPONSE_TIMEOUT_S = 2.0
AUTOFOCUS_AXIS_POSITION_SERVICE_TIMEOUT_S = 0.25


@dataclass(frozen=True)
class _SingleModeRunPlan:
    """Resolved mode-specific inputs for one autofocus run."""

    mode_name: str
    algorithm: object
    settle_s: float
    save_best_image: bool
    analysis_roi_rect: tuple[int, int, int, int] | None = None


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


@dataclass(frozen=True)
class _AutofocusFrame:
    """One fresh autofocus frame prepared from the live camera stream."""

    source_image: object
    analysis_image: object
    timestamp_ns: int
    encoding: str = ""


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
        client_kwargs = {}
        callback_group = getattr(node, "cb_group", None)
        if callback_group is not None:
            client_kwargs["callback_group"] = callback_group

        clients = {
            "move": node.create_client(
                MoveAbsolute,
                f"{AXIS_PREFIX}/move_absolute",
                **client_kwargs,
            ),
            "jog": node.create_client(
                JogAxis,
                f"{AXIS_PREFIX}/jog_axis",
                **client_kwargs,
            ),
            "status": node.create_client(
                GetOperationStatus,
                f"{AXIS_PREFIX}/get_operation_status",
                **client_kwargs,
            ),
            "position": node.create_client(
                GetPosition,
                f"{AXIS_PREFIX}/get_position",
                **client_kwargs,
            ),
            "stop": node.create_client(
                Stop,
                f"{AXIS_PREFIX}/stop",
                **client_kwargs,
            ),
            "get_vel": node.create_client(
                GetVelocityParameters,
                f"{AXIS_PREFIX}/get_velocity_parameters",
                **client_kwargs,
            ),
            "set_vel": node.create_client(
                SetVelocityParameters,
                f"{AXIS_PREFIX}/set_velocity_parameters",
                **client_kwargs,
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

    def _call_service_with_timeout(
        self,
        client,
        request,
        *,
        timeout_s: float,
    ):
        """Call a ROS service with a bounded wait to avoid callback-thread deadlocks."""
        call_async = getattr(client, "call_async", None)
        if not callable(call_async):
            try:
                return client.call(request)
            except Exception:
                return None
        try:
            future = call_async(request)
        except Exception:
            return None

        deadline = time.time() + max(0.01, float(timeout_s))
        while time.time() < deadline:
            if future.done():
                try:
                    return future.result()
                except Exception:
                    return None
            time.sleep(0.01)
        return None

    def wait_for_axis_target(
        self,
        clients: dict[str, object],
        target_pos_mm: float,
        *,
        tolerance_mm: float = AUTOFOCUS_AXIS_POSITION_TOLERANCE_MM,
        timeout_s: float = AUTOFOCUS_AXIS_WAIT_TIMEOUT_S,
    ) -> float:
        """Wait until the published/service position reaches the requested target."""
        deadline = time.time() + max(0.5, float(timeout_s))
        stable_hits = 0
        last_pos = None
        target_pos_mm = float(target_pos_mm)
        tolerance_mm = max(0.001, float(tolerance_mm))
        status_client = clients.get("status")

        while time.time() < deadline:
            current_pos = self.get_position(clients, prefer_cached=False)
            status_response = None
            if status_client is not None:
                status_response = self._call_service_with_timeout(
                    status_client,
                    GetOperationStatus.Request(),
                    timeout_s=AUTOFOCUS_AXIS_POSITION_SERVICE_TIMEOUT_S,
                )
                if status_response and status_response.operation_status in [
                    "error",
                    "emergency_stop",
                ]:
                    raise ServiceError(f"Axis error: {status_response.status_message}")

            position_in_tolerance = False
            if current_pos >= 0:
                last_pos = float(current_pos)
                position_in_tolerance = abs(last_pos - target_pos_mm) <= tolerance_mm
                if position_in_tolerance:
                    if status_response and status_response.operation_status != "idle":
                        stable_hits = 0
                    else:
                        stable_hits += 1
                    if stable_hits >= 3:
                        return last_pos
                else:
                    stable_hits = 0

            if status_response and status_response.operation_status == "idle":
                if last_pos is None:
                    return target_pos_mm
                if not position_in_tolerance:
                    if last_pos is None or abs(last_pos - target_pos_mm) > tolerance_mm:
                        self._handler._node.get_logger().warn(
                            "AF axis wait: axis reported idle before exact target "
                            "confirmation; continuing with idle-status fallback."
                        )
                    return float(last_pos) if last_pos is not None else target_pos_mm
            time.sleep(0.05)

        raise ServiceError(
            f"Axis did not reach target {target_pos_mm:.3f}mm within {timeout_s:.1f}s "
            f"(last_position={float(last_pos) if last_pos is not None else -1.0:.3f}mm)"
        )

    def get_position(
        self,
        clients: dict[str, object],
        *,
        prefer_cached: bool = True,
    ) -> float:
        """Read axis position, optionally bypassing the local topic cache."""
        node = self._handler._node
        cached_position = None
        if hasattr(node, "current_axis_position") and node.current_axis_position >= 0:
            cached_position = float(node.current_axis_position)
            if prefer_cached:
                return cached_position

        response = self._call_service_with_timeout(
            clients["position"],
            GetPosition.Request(),
            timeout_s=AUTOFOCUS_AXIS_POSITION_SERVICE_TIMEOUT_S,
        )
        if response and response.success:
            return float(response.axis_position)
        if cached_position is not None:
            return cached_position
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
    # Keep the response compact so students see only the final focus result,
    # while the detailed scan trace still remains available in the arrays below.
    status_parts = [
        "Autofocus complete",
        f"best_pos={float(best_position or 0.0):.3f}mm",
        f"score={float(best_score):.0f}",
        f"measurements={int(measurements)}",
    ]
    if best_image_path:
        status_parts.append(f"image={best_image_path}")
    response.status_message = ", ".join(status_parts)
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
        analysis_roi_rect: tuple[int, int, int, int] | None = None,
    ):
        """Run a single autofocus mode and populate the ROS response."""
        self._handler._node.get_logger().info(
            f"AF refine: mode={self._format_mode_name(mode)} "
            f"window={float(peak_start):.3f}-{float(peak_end):.3f}mm"
        )

        # The run plan freezes the selected algorithm, scan window, and timing
        # before any motion starts so the later execution path stays simple.
        run_plan = self._build_single_mode_run_plan(
            mode=mode,
            peak_start=peak_start,
            peak_end=peak_end,
            request=request,
            focus_profile=focus_profile,
            analysis_roi_rect=analysis_roi_rect,
        )
        best_position, best_score, measurements, best_image = self._execute_single_mode(
            run_plan, clients
        )
        self._log_fourstep_peak_fit(
            run_plan.mode_name, run_plan.algorithm, best_position
        )

        if best_position is not None:
            target_candidate = self._resolve_final_measurement_target(
                run_plan.mode_name,
                run_plan.algorithm,
                best_position,
                request,
            )
            target_pos = self._move_to_measurement_position(
                run_plan.mode_name,
                target_candidate,
                request,
                clients,
            )
            best_position, best_score, best_image = self._confirm_measurement_position(
                run_plan.mode_name,
                run_plan.algorithm,
                target_pos,
                best_position,
                best_score,
                best_image,
                request,
                clients,
                run_plan.save_best_image,
                run_plan.settle_s,
                run_plan.analysis_roi_rect,
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
        analysis_roi_rect: tuple[int, int, int, int] | None = None,
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
            analysis_roi_rect=analysis_roi_rect,
        )

    def _resolve_algorithm(self, mode: int) -> tuple[str, object]:
        """Map the wire-level mode id to the configured algorithm class."""
        return _ALGO_LOOKUP.get(mode, _ALGO_LOOKUP[0])

    def _format_mode_name(self, mode: int) -> str:
        """Return one short public mode label for logging."""
        return str(self._resolve_algorithm(mode)[0])

    def _resolve_scan_window(
        self,
        mode_name: str,
        peak_start: float,
        peak_end: float,
        request,
    ) -> tuple[float, float]:
        """Choose full-range or fly-over peak window based on the algorithm."""
        # Exhaustive-style modes intentionally ignore the fly-over peak and use
        # the complete requested range as their deterministic search window.
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
                    analysis_roi_rect=run_plan.analysis_roi_rect,
                )
            )
            return best_position, best_score, measurements, best_image

        best_position, best_score, measurements = self.run_autofocus_loop(
            run_plan.algorithm,
            clients,
            settle_s=run_plan.settle_s,
            analysis_roi_rect=run_plan.analysis_roi_rect,
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
            f'AF fourstep fit: peak={peak_mm:.6f}mm '
            f'final={float(best_position or 0.0):.6f}mm '
            f'points={len(fit_points)}'
        )

    def _resolve_final_measurement_target(
        self,
        mode_name: str,
        algorithm,
        best_position: float,
        request,
    ) -> float:
        """Choose the final candidate to physically test after the scan."""
        target_pos = float(best_position)
        if mode_name == 'fourstep':
            peak_pos = getattr(algorithm, 'parabolic_peak_mm', None)
            if peak_pos is not None:
                target_pos = float(peak_pos)
        return self._clamp_request_range(target_pos, request)

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
        settle_s: float,
        analysis_roi_rect: tuple[int, int, int, int] | None,
    ) -> tuple[float, float, object | None]:
        """Optionally re-measure the final point after the algorithm has completed."""
        if mode_name != 'fourstep':
            return float(best_position), float(best_score), best_image

        time.sleep(max(float(settle_s), FOURSTEP_SETTLE_S))
        last_timestamp = self._handler._get_latest_image_timestamp_ns()
        try:
            frame = self._wait_for_next_autofocus_frame(
                last_timestamp,
                analysis_roi_rect=analysis_roi_rect,
            )
        except ImageProcessingError:
            return float(best_position), float(best_score), best_image

        try:
            final_position = float(best_position)
            prior_best_score = float(best_score)
            final_score = float(algorithm.score_image(frame.analysis_image))
            if final_score >= prior_best_score:
                best_score = final_score
                final_position = float(target_pos)
                if save_best_image:
                    best_image = frame.analysis_image.copy()
                action = "accepted_peak"
            else:
                if abs(float(target_pos) - float(best_position)) > 1e-6:
                    self._move_to_measurement_position(
                        mode_name,
                        best_position,
                        request,
                        clients,
                    )
                action = "returned_to_scan_best"

            self._handler._node.get_logger().info(
                f'AF fourstep confirm: pos={target_pos:.3f}mm '
                f'score={final_score:.0f} best={float(best_score):.0f} '
                f'final={final_position:.3f}mm action={action}'
            )
            return final_position, float(best_score), best_image
        except Exception:
            pass

        return float(best_position), float(best_score), best_image

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
        logger = self._handler._node.get_logger()
        request = MoveAbsolute.Request(axis_position=float(target_pos))
        response = None
        axis_client_manager = getattr(self._handler, "_axis_clients", None)
        if (
            axis_client_manager is not None
            and hasattr(axis_client_manager, "_call_service_with_timeout")
        ):
            logger.info(
                f"AF move: target={float(target_pos):.3f}mm"
            )
            response = axis_client_manager._call_service_with_timeout(
                clients["move"],
                request,
                timeout_s=AUTOFOCUS_MOVE_RESPONSE_TIMEOUT_S,
            )
            if response is None:
                logger.warn(
                    "AF move: response timeout; waiting on status/position."
                )
            elif not getattr(response, "success", True):
                raise ServiceError(
                    getattr(response, "status_message", "move_absolute failed")
                )
        else:
            response = clients["move"].call(request)
            if response is not None and not getattr(response, "success", True):
                raise ServiceError(
                    getattr(response, "status_message", "move_absolute failed")
                )
        wait_for_target = getattr(self._handler, "_wait_for_axis_target", None)
        if callable(wait_for_target):
            reached_pos = float(wait_for_target(clients, float(target_pos)))
            logger.info(
                f"AF move: reached={reached_pos:.3f}mm target={float(target_pos):.3f}mm"
            )
            return
        self._handler._wait_for_axis_idle(clients)

    def run_autofocus_loop(
        self,
        algorithm,
        clients,
        return_best_image: bool = False,
        settle_s: float = 0.1,
        analysis_roi_rect: tuple[int, int, int, int] | None = None,
    ) -> tuple:
        """Run autofocus state machine until completion or timeout."""
        state = self._start_autofocus_loop(algorithm, clients, settle_s)
        max_steps = self._calculate_max_steps(algorithm)

        for step_index in range(max_steps):
            frame = self._wait_for_next_autofocus_frame(
                state.last_timestamp,
                analysis_roi_rect=analysis_roi_rect,
            )
            state.last_timestamp = frame.timestamp_ns
            result = algorithm.process_image(state.current_pos, frame.analysis_image)
            self._record_autofocus_result(
                state,
                result,
                frame.analysis_image,
                return_best_image=return_best_image,
            )
            self._log_autofocus_result(
                step_index + 1,
                state.current_pos,
                result,
                state.best_score,
                frame,
            )

            if result.finished:
                state.best_position = result.best_position_mm
                self._log_autofocus_completion(state)
                break

            if result.next_position_mm is None:
                break

            state.current_pos, state.last_timestamp = self._advance_autofocus_position(
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
        self._handler._node.get_logger().info(
            f'AF start: pos={current_pos:.3f}mm settle={float(settle_s):.2f}s'
        )
        self._move_axis(clients, current_pos)
        time.sleep(max(0.0, float(settle_s)))
        last_ts = self._handler._get_latest_image_timestamp_ns()
        return _AutofocusLoopState(
            current_pos=current_pos,
            last_timestamp=last_ts,
        )

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
        *,
        analysis_roi_rect: tuple[int, int, int, int] | None = None,
    ) -> _AutofocusFrame:
        """Wait for a fresh frame, but tolerate non-advancing timestamps when the image stream is alive."""
        wait_timeout = min(
            AUTOFOCUS_NEW_IMAGE_TIMEOUT_S,
            max(0.05, AUTOFOCUS_FRESH_FRAME_WAIT_S),
        )
        raw_image, ts, encoding = self._handler._wait_for_new_passthrough_image(
            last_timestamp,
            timeout=wait_timeout,
        )
        if raw_image is None:
            raw_image, ts = self._handler._wait_for_new_image(
                last_timestamp,
                timeout=wait_timeout,
            )
            encoding = ""

        if raw_image is None:
            raw_image, ts, encoding = self._handler._get_latest_passthrough_image()
        if raw_image is None:
            raw_image, ts = self._handler._get_latest_cv_image()
            encoding = encoding or ""
        if raw_image is None:
            self._handler._node.get_logger().error(
                'Timeout waiting for autofocus frame - no usable image available.'
            )
            raise ImageProcessingError(
                'Autofocus failed: no usable camera frame available. '
                f'Next step: check {self._handler._camera_image_topic()} in '
                'rqt_image_view and retry.'
            )

        if ts is None or int(ts) <= int(last_timestamp):
            self._handler._node.get_logger().warn(
                'AF frame: reusing cached image because timestamps did not advance.'
            )
        next_timestamp = last_timestamp if ts is None else int(ts)
        analysis_image = self._handler._prepare_autofocus_analysis_image(
            raw_image,
            roi_rect=analysis_roi_rect,
            encoding=encoding,
        )
        return _AutofocusFrame(
            source_image=raw_image,
            analysis_image=analysis_image,
            timestamp_ns=next_timestamp,
            encoding=str(encoding or ""),
        )

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
        step_index: int,
        current_pos: float,
        result,
        best_score: float,
        frame: _AutofocusFrame,
    ) -> None:
        """Emit one progress log line for the autofocus loop."""
        phase = getattr(result, 'phase', None)
        phase_name = phase.name if phase is not None else 'UNKNOWN'
        frame_h, frame_w = frame.analysis_image.shape[:2]
        next_position = getattr(result, "next_position_mm", None)
        next_desc = "done" if getattr(result, "finished", False) else (
            f"next={float(next_position):.3f}mm"
            if next_position is not None
            else "next=n/a"
        )
        self._handler._node.get_logger().info(
            f'AF step {int(step_index):02d} {phase_name}: '
            f'pos={current_pos:.3f}mm '
            f'score={float(result.current_score):.0f} '
            f'best={float(best_score):.0f} '
            f'frame={frame_w}x{frame_h} '
            f'enc={frame.encoding or "preview"} '
            f'{next_desc}'
        )

    def _log_autofocus_completion(self, state: _AutofocusLoopState) -> None:
        """Emit the final summary line when the loop reports completion."""
        self._handler._node.get_logger().info(
            f'AF complete: best={float(state.best_position or 0.0):.3f}mm '
            f'score={float(state.best_score):.0f} '
            f'measurements={state.measurements}'
        )

    def _advance_autofocus_position(
        self,
        clients,
        next_position_mm: float,
        settle_s: float,
    ) -> tuple[float, int]:
        """Move to the next requested autofocus position and dwell before capture."""
        next_pos = float(next_position_mm)
        self._move_axis(clients, next_pos)
        time.sleep(max(0.0, float(settle_s)))
        return next_pos, self._handler._get_latest_image_timestamp_ns()

class AutofocusHandler(CallbackBase):
    """Handler for autofocus with fly-over detection."""

    def __init__(self, node, camera_driver):
        super().__init__(node, camera_driver)
        self._axis_clients = AxisClientManager(self)
        self._runner = AutofocusRunner(self)
        self._analysis_config_logged = False
        self._analysis_effective_logged = False

    def _reset_analysis_logging(self) -> None:
        """Reset per-run analysis logging guards."""
        self._analysis_config_logged = False
        self._analysis_effective_logged = False

    def _get_reference_image_size(self) -> tuple[int, int] | None:
        """Return the best available current image size for ROI validation."""
        msg = getattr(self._node, "latest_image_msg", None)
        if msg is not None:
            width = int(getattr(msg, "width", 0) or 0)
            height = int(getattr(msg, "height", 0) or 0)
            if width > 0 and height > 0:
                return width, height

        width = self._param_int("camera.expected_width", 0)
        height = self._param_int("camera.expected_height", 0)
        if width > 0 and height > 0:
            return width, height
        return None

    def _select_roi_interactive(self, cv_image):
        """Open one temporary selection window and return the chosen ROI."""
        if cv_image is None:
            return None, None

        display_image = cv_image.copy()
        image_height, image_width = display_image.shape[:2]
        max_height = 800
        scale_factor = 1.0

        if image_height > max_height:
            scale_factor = max_height / float(image_height)
            display_image = cv2.resize(
                display_image,
                (int(image_width * scale_factor), int(image_height * scale_factor)),
            )

        window_name = "Select Autofocus ROI"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, display_image.shape[1], display_image.shape[0])
        roi = cv2.selectROI(
            window_name,
            display_image,
            fromCenter=False,
            showCrosshair=True,
        )
        cv2.destroyWindow(window_name)
        cv2.waitKey(1)

        if roi == (0, 0, 0, 0):
            return None, None

        x_scaled, y_scaled, width_scaled, height_scaled = roi
        x = int(x_scaled / scale_factor)
        y = int(y_scaled / scale_factor)
        width = int(width_scaled / scale_factor)
        height = int(height_scaled / scale_factor)

        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        width = max(1, min(width, image_width - x))
        height = max(1, min(height, image_height - y))

        roi_rect = (x, y, width, height)
        roi_image = cv_image[y : y + height, x : x + width]
        return roi_rect, roi_image

    def _resolve_roi_request_rect(
        self,
        request,
    ) -> tuple[int, int, int, int]:
        """Validate and normalize an autofocus ROI request rectangle."""
        roi_x = int(getattr(request, "roi_x", 0))
        roi_y = int(getattr(request, "roi_y", 0))
        roi_width = int(getattr(request, "roi_width", 0))
        roi_height = int(getattr(request, "roi_height", 0))

        if roi_width <= 0 or roi_height <= 0:
            raise ConfigurationError(
                "ROI width and height must be positive",
                details={
                    "roi_x": roi_x,
                    "roi_y": roi_y,
                    "roi_width": roi_width,
                    "roi_height": roi_height,
                },
            )

        reference_size = self._get_reference_image_size()
        if reference_size is not None:
            image_width, image_height = reference_size
            if (
                roi_x >= image_width
                or roi_y >= image_height
                or roi_x + roi_width <= 0
                or roi_y + roi_height <= 0
            ):
                raise ConfigurationError(
                    "Requested ROI lies outside the current image",
                    details={
                        "roi_x": roi_x,
                        "roi_y": roi_y,
                        "roi_width": roi_width,
                        "roi_height": roi_height,
                        "image_width": image_width,
                        "image_height": image_height,
                    },
                )

        return roi_x, roi_y, roi_width, roi_height

    def _resolve_or_select_roi_rect(
        self,
        request,
    ) -> tuple[int, int, int, int]:
        """Use an explicit ROI request when present, otherwise ask the operator."""
        roi_x = int(getattr(request, "roi_x", 0) or 0)
        roi_y = int(getattr(request, "roi_y", 0) or 0)
        roi_width = int(getattr(request, "roi_width", 0) or 0)
        roi_height = int(getattr(request, "roi_height", 0) or 0)

        if roi_width > 0 and roi_height > 0:
            return self._resolve_roi_request_rect(request)

        if any(value != 0 for value in (roi_x, roi_y, roi_width, roi_height)):
            return self._resolve_roi_request_rect(request)

        cv_image, _timestamp_ns = self._get_latest_cv_image()
        if cv_image is None:
            raise ImageProcessingError(
                "Autofocus ROI selection needs one live camera frame. "
                f"Next step: check {self._camera_image_topic()} in rqt_image_view and retry."
            )

        roi_rect, _roi_image = self._select_roi_interactive(cv_image)
        if roi_rect is None:
            raise ImageProcessingError(
                "Autofocus ROI selection was cancelled. "
                "Next step: draw one ROI around the target area and retry autofocus."
            )

        self._node.get_logger().info(
            f"AF ROI selected: x={roi_rect[0]} y={roi_rect[1]} "
            f"w={roi_rect[2]} h={roi_rect[3]}"
        )
        return roi_rect

    def _log_analysis_plan(
        self,
        roi_rect: tuple[int, int, int, int] | None = None,
    ) -> None:
        """Emit the configured AF analysis strategy once per service call."""
        if self._analysis_config_logged:
            return

        downsample_max = self._param_int(
            "autofocus.analysis_downsample_max_dim_px",
            2048,
        )
        if roi_rect is not None:
            roi_desc = (
                f"requested_roi=({roi_rect[0]},{roi_rect[1]},{roi_rect[2]},{roi_rect[3]})"
            )
            mode_desc = "requested-roi"
        elif self._param_bool("autofocus.analysis_use_center_roi", True):
            configured_x = self._param_int("autofocus.analysis_roi_x_px", -1)
            configured_y = self._param_int("autofocus.analysis_roi_y_px", -1)
            configured_roi = configured_x >= 0 and configured_y >= 0
            roi_width = self._param_int("autofocus.analysis_roi_width_px", 2048)
            roi_height = self._param_int("autofocus.analysis_roi_height_px", 2048)
            if configured_roi:
                roi_desc = (
                    f"configured_roi=({configured_x},{configured_y},"
                    f"{roi_width},{roi_height})"
                )
                mode_desc = "configured-roi"
            else:
                roi_desc = f"center_roi={roi_width}x{roi_height}"
                mode_desc = "center-roi"
        else:
            roi_desc = "full_frame"
            mode_desc = "full-frame"

        self._node.get_logger().info(
            f"AF analysis: mode={mode_desc} {roi_desc} downsample={downsample_max}px"
        )
        self._analysis_config_logged = True

    def _prepare_autofocus_analysis_image(
        self,
        image,
        roi_rect: tuple[int, int, int, int] | None = None,
        encoding: str = "",
    ):
        """Crop and downsample a frame before deriving the smaller AF analysis image."""
        if image is None:
            return None

        image_height, image_width = image.shape[:2]
        requested_roi = roi_rect
        if requested_roi is None and self._param_bool(
            "autofocus.analysis_use_center_roi",
            True,
        ):
            requested_width = max(
                1,
                self._param_int("autofocus.analysis_roi_width_px", 2048),
            )
            requested_height = max(
                1,
                self._param_int("autofocus.analysis_roi_height_px", 2048),
            )
            configured_x = self._param_int("autofocus.analysis_roi_x_px", -1)
            configured_y = self._param_int("autofocus.analysis_roi_y_px", -1)
            if configured_x >= 0 and configured_y >= 0:
                requested_x = configured_x
                requested_y = configured_y
            else:
                requested_x = int((image_width - requested_width) / 2)
                requested_y = int((image_height - requested_height) / 2)
            requested_roi = (
                requested_x,
                requested_y,
                requested_width,
                requested_height,
            )

        effective_roi = None
        analysis_image = image
        if requested_roi is not None:
            effective_roi = self._clamp_roi_rect(
                image_width,
                image_height,
                requested_roi[0],
                requested_roi[1],
                requested_roi[2],
                requested_roi[3],
            )
            if effective_roi is None:
                raise ImageProcessingError(
                    "Autofocus analysis ROI lies outside the current image",
                    details={
                        "roi_x": requested_roi[0],
                        "roi_y": requested_roi[1],
                        "roi_width": requested_roi[2],
                        "roi_height": requested_roi[3],
                        "image_width": image_width,
                        "image_height": image_height,
                    },
                )
            analysis_image = self._crop_to_roi(image, effective_roi)

        downsample_max = self._param_int(
            "autofocus.analysis_downsample_max_dim_px",
            2048,
        )
        processed_image = self._downsample_image(analysis_image, downsample_max)
        if is_bayer_encoding(encoding) and getattr(processed_image, "ndim", 0) == 2:
            processed_image = raw_array_to_bgr8_preview(processed_image, encoding)

        if (
            self._param_bool("autofocus.analysis_log_effective_roi", True)
            and not self._analysis_effective_logged
        ):
            processed_height, processed_width = processed_image.shape[:2]
            message_parts = [
                f"AF analysis effective: source={image_width}x{image_height}",
            ]
            if requested_roi is not None:
                message_parts.append(
                    "requested_roi="
                    f"({requested_roi[0]},{requested_roi[1]},{requested_roi[2]},{requested_roi[3]})"
                )
            if effective_roi is not None:
                message_parts.append(
                    "effective_roi="
                    f"({effective_roi[0]},{effective_roi[1]},{effective_roi[2]},{effective_roi[3]})"
                )
            message_parts.append(
                f"analysis_image={processed_width}x{processed_height}"
            )
            self._node.get_logger().info(", ".join(message_parts))
            self._analysis_effective_logged = True

        return processed_image

    def _build_focus_profile(self, request) -> dict:
        """Build objective-aware autofocus profile for fly-over and refinement."""
        focus_profile = FocusProfileBuilder(self._node).build(request).as_dict()
        base_settle_s = float(focus_profile.get("settle_s", 0.1) or 0.1)
        exposure_guard_s = self._param_float("autofocus.exposure_guard_s", 0.02)
        exposure_time_us = self._current_exposure_us()
        focus_profile["base_settle_s"] = base_settle_s
        focus_profile["exposure_time_us"] = exposure_time_us
        focus_profile["exposure_guard_s"] = exposure_guard_s
        focus_profile["settle_s"] = max(
            base_settle_s,
            (float(exposure_time_us) / 1_000_000.0) + float(exposure_guard_s),
        )
        return focus_profile

    @handle_service_errors()
    def autofocus_callback(self, request, response):
        """Run autofocus: optional fly-over plus selected refinement mode."""
        return self._run_autofocus_request(
            request,
            response,
            analysis_roi_rect=None,
        )

    @handle_service_errors()
    def autofocus_roi_callback(self, request, response):
        """Run autofocus on a requested image ROI."""
        return self._run_autofocus_request(
            request,
            response,
            analysis_roi_rect=self._resolve_or_select_roi_rect(request),
        )

    @handle_service_errors()
    def measure_tenengrad_roi_callback(self, request, response):
        """Measure the autofocus Tenengrad score in one ROI without axis motion."""
        self._reset_analysis_logging()
        requested_roi = self._resolve_or_select_roi_rect(request)

        image, timestamp_ns, encoding = self._get_latest_passthrough_image()
        if image is None:
            image, timestamp_ns = self._get_latest_cv_image()
            encoding = ""
        if image is None:
            raise ImageProcessingError(
                "Tenengrad measurement needs one live camera frame. "
                f"Next step: check {self._camera_image_topic()} in "
                "rqt_image_view and retry."
            )

        image_height, image_width = image.shape[:2]
        effective_roi = self._clamp_roi_rect(
            image_width,
            image_height,
            requested_roi[0],
            requested_roi[1],
            requested_roi[2],
            requested_roi[3],
        )
        if effective_roi is None:
            raise ImageProcessingError(
                "Tenengrad ROI lies outside the current camera image"
            )

        analysis_image = self._prepare_autofocus_analysis_image(
            image,
            roi_rect=effective_roi,
            encoding=str(encoding or ""),
        )
        if analysis_image is None or analysis_image.size == 0:
            raise ImageProcessingError("Tenengrad analysis produced an empty ROI")

        score = float(self._calculate_sharpness(analysis_image))
        analysis_height, analysis_width = analysis_image.shape[:2]
        roi_x, roi_y, roi_width, roi_height = effective_roi

        response.success = True
        response.status_message = (
            f"Tenengrad measured: value={score:.0f}, "
            f"roi=({roi_x},{roi_y},{roi_width},{roi_height}), "
            f"analysis={analysis_width}x{analysis_height}"
        )
        response.tenengrad_value = score
        response.roi_x = roi_x
        response.roi_y = roi_y
        response.roi_width = roi_width
        response.roi_height = roi_height
        response.analysis_width = analysis_width
        response.analysis_height = analysis_height
        response.image_timestamp_ns = max(0, int(timestamp_ns or 0))
        response.image_encoding = str(encoding or "")

        self._node.get_logger().info(
            "Tenengrad ROI: "
            f"value={score:.0f} roi=({roi_x},{roi_y},{roi_width},{roi_height}) "
            f"analysis={analysis_width}x{analysis_height} "
            f"encoding={str(encoding or 'converted')}"
        )
        return response

    def _run_autofocus_request(
        self,
        request,
        response,
        analysis_roi_rect: tuple[int, int, int, int] | None,
    ):
        """Shared implementation for central and ROI autofocus services."""
        self._reset_analysis_logging()
        mode = getattr(request, "focus_mode", getattr(request, "refinement_mode", 0))
        mode_name = str(_ALGO_LOOKUP.get(mode, _ALGO_LOOKUP[0])[0])
        start_time = time.time()
        focus_profile = self._build_focus_profile(request)

        self._node.get_logger().info(
            f"AF request: range={float(request.start_position):.3f}-{float(request.end_position):.3f}mm "
            f"mode={mode_name} skip_flyover={bool(getattr(request, 'skip_flyover', False))}"
        )
        self._log_analysis_plan(analysis_roi_rect)
        mag_label = (
            f'{focus_profile["magnification_x"]:.2f}x'
            if focus_profile["magnification_x"] is not None
            else "unknown"
        )
        self._node.get_logger().info(
            f'AF profile: objective="{focus_profile["objective"]}" '
            f"mag={mag_label} beamsplitter={focus_profile['beamsplitter']} "
            f"profile={focus_profile['profile_source']} "
            f"scan_speed={focus_profile['scan_speed_mm_s']:.2f}mm/s "
            f"axis_scale={focus_profile['axis_speed_scale']:.3f} "
            f"max_sample_step={focus_profile['max_sample_step_mm']:.3f}mm "
            f"coarse_step={focus_profile['coarse_step_mm']:.3f}mm "
            f"min_step={focus_profile['min_step_mm']:.3f}mm "
            f"settle={focus_profile['settle_s']:.2f}s "
            f"(base={focus_profile['base_settle_s']:.2f}s, "
            f"exp={focus_profile['exposure_time_us'] / 1000.0:.3f}ms, "
            f"guard={focus_profile['exposure_guard_s']:.3f}s)"
        )

        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        clients = self._get_all_axis_clients()
        skip_flyover = getattr(request, "skip_flyover", False)
        if skip_flyover:
            self._node.get_logger().info(
                f"AF flyover: skipped, window={float(request.start_position):.3f}-{float(request.end_position):.3f}mm"
            )
            peak_start = float(request.start_position)
            peak_end = float(request.end_position)
        else:
            self._node.get_logger().info("AF flyover: start")
            peak_start, peak_end, max_stddev = self._fly_over_detection(
                request.start_position,
                request.end_position,
                clients,
                focus_profile,
            )
            if peak_start is None or peak_end is None:
                raise ImageProcessingError(
                    "Autofocus fly-over found no target. Next step: center the "
                    "target, check exposure/contrast, and retry autofocus."
                )
            self._node.get_logger().info(
                f"AF flyover: window={peak_start:.3f}-{peak_end:.3f}mm "
                f"peak_stddev={max_stddev:.1f}"
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
            analysis_roi_rect,
        )

    def _get_all_axis_clients(self):
        return self._axis_clients.get_all_axis_clients()

    def _wait_for_axis_idle(self, clients):
        self._axis_clients.wait_for_axis_idle(clients)

    def _wait_for_axis_target(self, clients, target_pos: float) -> float:
        return self._axis_clients.wait_for_axis_target(clients, target_pos)

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
            get_position=lambda clients: self._axis_clients.get_position(
                clients,
                prefer_cached=False,
            ),
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
        analysis_roi_rect: tuple[int, int, int, int] | None = None,
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
            analysis_roi_rect,
        )

    def _run_autofocus_loop(
        self,
        af,
        clients,
        return_best_image: bool = False,
        settle_s: float = 0.1,
        analysis_roi_rect: tuple[int, int, int, int] | None = None,
    ) -> tuple:
        return self._runner.run_autofocus_loop(
            af,
            clients,
            return_best_image=return_best_image,
            settle_s=settle_s,
            analysis_roi_rect=analysis_roi_rect,
        )
