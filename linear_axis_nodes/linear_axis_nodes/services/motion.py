"""Motion-oriented linear-axis service callbacks (move/home/stop/jog)."""

from __future__ import annotations

import threading

from promoc_core.error_handling import handle_service_errors

from ..config import LTS300NodeConfig
from ..models import OperationStateStore, OperationStatus
from .validation import LinearAxisValidator


class LinearMotionCallbacks:
    """Callbacks for motion-affecting linear-axis services."""

    def __init__(
        self,
        logger,
        *,
        driver,
        validator: LinearAxisValidator,
        state_store: OperationStateStore,
        config: LTS300NodeConfig,
    ):
        self.logger = logger
        self.driver = driver
        self.validator = validator
        self.state_store = state_store
        self.config = config

    def _start_async(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def _log_transition(self, phase: str, message: str) -> None:
        if phase in {"error", "timeout"}:
            self.logger.error(f"[{phase}] {message}")
        elif phase in {"start", "done"}:
            self.logger.info(f"[{phase}] {message}")
        else:
            self.logger.debug(f"[{phase}] {message}")

    def _async_move_operation(self, move_type: str, value_mm: float) -> None:
        try:
            if move_type == "absolute":
                self.driver.move_absolute(value_mm)
                done_message = f"absolute movement completed to {value_mm:.2f}mm"
            else:
                self.driver.move_relative(value_mm)
                done_message = f"relative movement completed by {value_mm:.2f}mm"

            try:
                final_pos = float(self.driver.get_position())
                status_message = (
                    f"Movement completed - final position: {final_pos:.2f}mm"
                )
            except Exception:
                status_message = "Movement completed"

            self.state_store.set(OperationStatus.IDLE, status_message)
            self._log_transition("done", done_message)
        except Exception as exc:
            msg = str(exc) or "unknown motion execution error"
            self.state_store.set(OperationStatus.ERROR, msg)
            self._log_transition("error", msg)

    def _async_home_operation(self) -> None:
        try:
            self.driver.home(timeout=float(self.config.homing_timeout))

            try:
                final_pos = float(self.driver.get_position())
                status_message = (
                    f"Homing completed successfully (position: {final_pos:.2f}mm)"
                )
            except Exception:
                status_message = "Homing completed successfully"

            self.state_store.set(OperationStatus.IDLE, status_message)
            self._log_transition("done", "homing completed")
        except Exception as exc:
            msg = str(exc) or "unknown homing execution error"
            self.state_store.set(OperationStatus.ERROR, msg)
            self._log_transition("error", msg)

    @handle_service_errors()
    def callback_move_absolute(self, request, response, other_axis_position: float):
        self.validator.validate_position(request.axis_position)
        self.validator.collision_check(
            other_axis_position,
            axis_position=float(request.axis_position),
        )

        started, current = self.state_store.try_set_if(
            allowed={OperationStatus.IDLE},
            new_status=OperationStatus.MOVING,
            message=f"starting absolute movement to {request.axis_position:.2f}mm",
        )
        if not started:
            response.success = False
            response.status_message = f"Operation already in progress: {current.value}"
            self.logger.warn(response.status_message)
            return response

        self._log_transition(
            "start",
            f"absolute movement requested to {request.axis_position:.2f}mm",
        )
        self._start_async(
            self._async_move_operation,
            "absolute",
            float(request.axis_position),
        )

        response.success = True
        response.status_message = (
            f"Absolute movement to {request.axis_position:.2f}mm started - "
            "check status with get_operation_status"
        )
        return response

    @handle_service_errors()
    def callback_move_relative(self, request, response, other_axis_position: float):
        self.validator.validate_distance(request.axis_position)

        current_mm = float(self.driver.get_position())
        self.validator.validate_target_position(current_mm, request.axis_position)
        self.validator.collision_check(
            other_axis_position,
            axis_position=float(current_mm + request.axis_position),
        )

        started, current = self.state_store.try_set_if(
            allowed={OperationStatus.IDLE},
            new_status=OperationStatus.MOVING,
            message=f"starting relative movement by {request.axis_position:.2f}mm",
        )
        if not started:
            response.success = False
            response.status_message = f"Operation already in progress: {current.value}"
            self.logger.warn(response.status_message)
            return response

        self._start_async(
            self._async_move_operation,
            "relative",
            float(request.axis_position),
        )

        response.success = True
        response.status_message = (
            f"Relative movement by {request.axis_position:.2f}mm started - "
            "check status with get_operation_status"
        )
        return response

    @handle_service_errors()
    def callback_home(self, request, response):
        allowed = {
            OperationStatus.IDLE,
            OperationStatus.EMERGENCY_STOP,
            OperationStatus.ERROR,
        }
        started, current = self.state_store.try_set_if(
            allowed=allowed,
            new_status=OperationStatus.HOMING,
            message="Homing in progress...",
        )
        if not started:
            response.success = False
            response.status_message = (
                f"Cannot home during {current.value}. Stop operation first."
            )
            self.logger.warn(response.status_message)
            return response

        if current in {OperationStatus.EMERGENCY_STOP, OperationStatus.ERROR}:
            response.status_message = (
                f"Resetting from {current.value} and homing started - "
                "check status with get_position service"
            )
        else:
            response.status_message = (
                "Homing started - check status with get_position service"
            )

        self._start_async(self._async_home_operation)

        response.success = True
        self._log_transition("start", "homing started")
        return response

    @handle_service_errors()
    def callback_emergency_stop(self, request, response):
        current_status, _ = self.state_store.get()
        was_moving = current_status in {OperationStatus.MOVING, OperationStatus.JOGGING}

        self.driver.stop()
        self.state_store.set(
            OperationStatus.EMERGENCY_STOP,
            f"Emergency stop triggered (was: {current_status.value})",
        )
        self._log_transition("error", "emergency stop executed")

        response.success = True
        response.was_moving = was_moving
        response.status_message = (
            f"Emergency stop executed - movement halted (was_moving: {was_moving})"
        )
        return response

    @handle_service_errors()
    def callback_stop(self, request, response):
        current_status, _ = self.state_store.get()
        was_moving = current_status in {OperationStatus.MOVING, OperationStatus.JOGGING}

        self.driver.stop()
        self.state_store.set(OperationStatus.IDLE, "Stopped by request")
        self._log_transition("done", "stop executed")

        response.success = True
        response.status_message = f"Stop executed (was_moving: {was_moving})"
        return response

    @handle_service_errors()
    def callback_jog_axis(self, request, response):
        status, _ = self.state_store.get()
        if status in {OperationStatus.HOMING, OperationStatus.EMERGENCY_STOP}:
            response.success = False
            response.final_position = -1.0
            response.status_message = f"Jogging not allowed during {status.value}"
            self.logger.warn(response.status_message)
            return response

        if status != OperationStatus.IDLE:
            response.success = False
            response.final_position = -1.0
            response.status_message = (
                f"Cannot jog: operation already in progress: {status.value}"
            )
            return response

        step_size = float(request.step_size)
        direction = "positive" if step_size >= 0 else "negative"
        started, _ = self.state_store.try_set_if(
            allowed={OperationStatus.IDLE},
            new_status=OperationStatus.JOGGING,
            message=f"Jogging {direction} by {abs(step_size):.2f}mm...",
        )
        if not started:
            response.success = False
            response.final_position = -1.0
            response.status_message = "Cannot jog: operation already in progress"
            return response

        try:
            if step_size >= 0:
                self.driver.jog_positive(abs(step_size))
            else:
                self.driver.jog_negative(abs(step_size))

            final_position = float(self.driver.get_position())
            self.state_store.set(
                OperationStatus.IDLE,
                f"Jog completed - position: {final_position:.2f}mm",
            )
            self._log_transition("done", f"jog {step_size:+.2f}mm")

            response.success = True
            response.final_position = final_position
            response.status_message = (
                f"Jog {step_size:+.2f}mm completed: {final_position:.2f}mm"
            )
            return response
        except Exception as exc:
            self.state_store.set(OperationStatus.ERROR, f"Jog failed: {exc}")
            self._log_transition("error", f"jog failed: {exc}")
            raise
