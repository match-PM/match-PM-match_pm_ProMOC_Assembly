"""Service callbacks for the LTS300 linear axis."""

# Detailed module documentation was moved into comments to keep ament_pep257
# happy (it enforces strict rules for multi-line module docstrings).
#
# This module contains the ServiceCallbacks class implementing all ROS2 service
# handlers for the linear axis node. The business logic lives here.

from enum import Enum
import threading

from promoc_core.promoc_exceptions import (
    CollisionDetectedError,
    SoftLimitViolationError,
)
from promoc_core.validation import check_collision_risk, is_in_range
from promoc_core.logging import TaggedLogger, LogTags
from promoc_core.error_handling import handle_service_errors

from ..config import LTS300NodeConfig
from ..helpers.lts300_interface import Lts300Interface


class OperationStatus(Enum):
    """Define the status of long-running operations."""

    IDLE = "idle"
    HOMING = "homing"
    MOVING = "moving"
    JOGGING = "jogging"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


class ServiceCallbacks:
    """Implement the business logic for all LTS300 node services."""

    def __init__(
        self,
        logger,
        interface: Lts300Interface,
        config: LTS300NodeConfig,
    ):
        """Initialize the callbacks with their dependencies."""
        self.logger = TaggedLogger(logger, LogTags.LTS_MOVE)
        self.interface = interface
        self.config = config
        self.driver = self.interface.driver

        # Status-Tracking für asynchrone Operationen
        self.operation_status = OperationStatus.IDLE
        self.operation_lock = threading.Lock()
        self.last_operation_message = ""

    def _start_async(self, target, *args):
        """Start a daemon thread for a background operation."""
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    # ══════════════════════════════════════════════════════════════════════════
    # UNIT CONVERSION
    # ══════════════════════════════════════════════════════════════════════════

    def _device_units_to_mm_per_s(self, device_units: float) -> float:
        """Converts device-specific velocity units to mm/s."""
        return device_units * self.config.velocity_conversion_factor

    def _mm_per_s_to_device_units(self, mm_per_s: float) -> float:
        """Converts mm/s to device-specific velocity units."""
        return mm_per_s / self.config.velocity_conversion_factor

    # ══════════════════════════════════════════════════════════════════════════
    # VALIDATION
    # ══════════════════════════════════════════════════════════════════════════

    def _collision_check(
        self,
        other_axis_position: float,
        axis_position: float = 0.0,
    ):
        """
        Check the collision risk with the other axis.

        Args
        ----
        other_axis_position:
            Current position of the other axis (mm).

        Raises
        ------
        CollisionDetectedError
            If a collision risk is detected.

        """
        is_safe, warning_msg = check_collision_risk(
            axis_position=axis_position,
            other_axis_position=other_axis_position,
            collision_threshold=self.config.collision_threshold,
        )

        if warning_msg:
            self.logger.warn(warning_msg)

        if not is_safe:
            raise CollisionDetectedError(
                f"Collision risk detected! Other axis at {other_axis_position:.2f}mm exceeds "
                f"threshold {self.config.collision_threshold}mm",
                details={
                    "other_axis_position": other_axis_position,
                    "collision_threshold": self.config.collision_threshold,
                    "axis_name": getattr(self.logger, "name", "lts300"),
                },
            )

    def _validate_position(self, position: float):
        """
        Validate that a position is within the soft limits.

        Args
        ----
        position:
            Target position in mm.

        Raises
        ------
        SoftLimitViolationError
            If the position is outside the limits.

        """
        min_position = self.config.min_position
        max_position = self.config.max_position

        if not is_in_range(position, min_position, max_position):
            if position < min_position:
                violation_type = "min_limit"
                msg = f"Position {position:.2f}mm below minimum limit {min_position:.2f}mm"
            else:
                violation_type = "max_limit"
                msg = f"Position {position:.2f}mm exceeds maximum limit {max_position:.2f}mm"

            raise SoftLimitViolationError(
                msg,
                details={
                    "requested_position": position,
                    "min_position": min_position,
                    "max_position": max_position,
                    "violation_type": violation_type,
                },
            )

    def _validate_distance(self, distance: float):
        """
        Validate that a movement distance is allowed.

        Args
        ----
        distance:
            Movement distance in mm.

        Raises
        ------
        SoftLimitViolationError
            If the distance exceeds the maximum.

        """
        max_single_move = self.config.max_single_move
        abs_distance = abs(distance)
        if abs_distance > max_single_move:
            raise SoftLimitViolationError(
                f"Movement distance {abs_distance:.2f}mm exceeds maximum single move "
                f"limit {max_single_move:.2f}mm",
                details={
                    "requested_distance": distance,
                    "abs_distance": abs_distance,
                    "max_single_move": max_single_move,
                    "violation_type": "max_distance",
                },
            )

    def _validate_target_position(self, current_pos: float, distance: float):
        """
        Validate that a relative move leads to a valid target position.

        Args
        ----
        current_pos:
            Current position in mm.
        distance:
            Movement distance in mm.

        Raises
        ------
        SoftLimitViolationError
            If the target position is outside the limits.

        """
        target_pos = current_pos + distance
        self._validate_position(target_pos)

    # ══════════════════════════════════════════════════════════════════════════
    # ASYNCHRONOUS OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _async_move_operation(self, move_type: str, position: float):
        """Run a movement operation in a separate thread."""
        try:
            with self.operation_lock:
                self.operation_status = OperationStatus.MOVING
                self.last_operation_message = (
                    f"Moving {move_type} to {position:.2f}mm..."
                )

            self.logger.debug(f"Starting {move_type} movement to {position:.2f}mm...")

            if move_type == "absolute":
                self.driver.move_absolute(position)
            else:
                self.driver.move_relative(position)

            self.logger.debug(f"Hardware {move_type} movement command completed")

            # Get final position for confirmation
            try:
                final_pos = self.driver.get_position()
                self.logger.debug(
                    f"Final position after {move_type} movement: {final_pos:.2f}mm"
                )
            except Exception as pos_e:
                self.logger.warn(f"Could not read position after movement: {pos_e}")
                final_pos = "unknown"

            with self.operation_lock:
                self.operation_status = OperationStatus.IDLE
                self.last_operation_message = (
                    f"Movement completed - final position: {final_pos}mm"
                )

            self.logger.debug(
                f"{move_type.capitalize()} movement completed successfully"
            )

        except Exception as e:
            error_msg = (
                str(e)
                if str(e).strip()
                else f"Unknown error during {move_type} movement"
            )
            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"Movement failed: {error_msg}"

            self.logger.error(f"{move_type.capitalize()} movement failed: {error_msg}")

    def _async_home_operation(self):
        """Perform a homing operation in a separate thread."""
        try:
            with self.operation_lock:
                self.operation_status = OperationStatus.HOMING
                self.last_operation_message = "Homing in progress..."

            self.logger.info("Starting homing operation...")

            # Call the actual homing operation (now with configurable timeout)
            self.driver.home(timeout=self.config.homing_timeout)
            self.logger.info("Hardware homing command completed")

            # Get final position for confirmation
            try:
                final_pos = self.driver.get_position()
                self.logger.info(f"Post-homing position: {final_pos:.2f}mm")
            except Exception as pos_e:
                self.logger.warn(f"Could not read position after homing: {pos_e}")
                final_pos = "unknown"

            with self.operation_lock:
                self.operation_status = OperationStatus.IDLE
                self.last_operation_message = (
                    f"Homing completed successfully (position: {final_pos}mm)"
                )

            self.logger.info("Homing operation completed successfully")

        except Exception as e:
            # Handle specific timeout errors and keep state machine consistent.
            if "ThorlabsTimeoutError" in str(type(e)) or "timeout" in str(e).lower():
                error_msg = (
                    "Homing timeout - operation may still be in progress on hardware"
                )
                self.logger.warn(f"{error_msg}")
            else:
                error_msg = str(e) if str(e).strip() else "Unknown error during homing"
                self.logger.error(f"Homing operation failed: {error_msg}")

            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"Homing failed: {error_msg}"

    def get_operation_status(self) -> tuple[OperationStatus, str]:
        """
        Return the current operation status and message.

        Returns
        -------
        tuple[OperationStatus, str]
            (status, message)

        """
        with self.operation_lock:
            return self.operation_status, self.last_operation_message

    # --- Service Callback Implementations ---

    @handle_service_errors()
    def callback_move_absolute(self, request, response, other_axis_position: float):
        """
        Handle absolute movement service request.

        Uses custom exceptions for precise error handling.
        """
        # Safety validation - will raise SoftLimitViolationError if invalid
        self._validate_position(request.axis_position)

        # Collision check - will raise CollisionDetectedError if detected
        self._collision_check(
            other_axis_position,
            axis_position=float(request.axis_position),
        )

        # Reserve operation state before starting async thread to avoid races.
        with self.operation_lock:
            if self.operation_status != OperationStatus.IDLE:
                response.success = False
                response.status_message = (
                    f"Operation already in progress: {self.operation_status.value}"
                )
                self.logger.warn(response.status_message)
                return response
            self.operation_status = OperationStatus.MOVING
            self.last_operation_message = (
                f"Starting absolute movement to {request.axis_position:.2f}mm..."
            )

        # Start movement in background thread
        self.logger.debug(
            f"Starting asynchronous absolute movement to: {request.axis_position} mm"
        )
        self._start_async(self._async_move_operation, "absolute", request.axis_position)

        response.success = True
        response.status_message = (
            f"Absolute movement to {request.axis_position:.2f}mm started - "
            "check status with get_operation_status"
        )

        return response

    @handle_service_errors()
    def callback_move_relative(self, request, response, other_axis_position: float):
        """
        Handle relative movement service request.

        Uses custom exceptions for precise error handling.
        """
        # Safety validation for movement distance - will raise if invalid
        self._validate_distance(request.axis_position)

        # Safety validation for target position
        current_pos = self.driver.get_position()
        self._validate_target_position(current_pos, request.axis_position)

        # Collision check - will raise CollisionDetectedError if detected
        self._collision_check(
            other_axis_position,
            axis_position=float(current_pos + request.axis_position),
        )

        # Reserve operation state before starting async thread to avoid races.
        with self.operation_lock:
            if self.operation_status != OperationStatus.IDLE:
                response.success = False
                response.status_message = (
                    f"Operation already in progress: {self.operation_status.value}"
                )
                self.logger.warn(response.status_message)
                return response
            self.operation_status = OperationStatus.MOVING
            self.last_operation_message = (
                f"Starting relative movement by {request.axis_position:.2f}mm..."
            )

        # Start movement in background thread
        self.logger.debug(
            f"Starting asynchronous relative movement by: {request.axis_position} mm"
        )
        self._start_async(self._async_move_operation, "relative", request.axis_position)

        response.success = True
        response.status_message = (
            f"Relative movement by {request.axis_position:.2f}mm started - "
            "check status with get_operation_status"
        )

        return response

    @handle_service_errors()
    def callback_home(self, request, response):
        """Handle homing requests - automatically resets from emergency/error states."""
        # Check current status and allow homing from recoverable states
        with self.operation_lock:
            current_status = self.operation_status

            # Allow homing from IDLE, EMERGENCY_STOP, and ERROR states
            allowed = [
                OperationStatus.IDLE,
                OperationStatus.EMERGENCY_STOP,
                OperationStatus.ERROR,
            ]
            if current_status not in allowed:
                response.success = False
                response.status_message = (
                    f"Cannot home during {current_status.value}. Stop operation first."
                )
                self.logger.warn(response.status_message)
                return response

            # If coming from emergency/error state, log the reset
            if current_status in [
                OperationStatus.EMERGENCY_STOP,
                OperationStatus.ERROR,
            ]:
                self.logger.info(
                    f"Resetting from {current_status.value} state and homing..."
                )
                response.status_message = (
                    f"Resetting from {current_status.value} and homing started - "
                    "check status with get_position service"
                )
            else:
                response.status_message = (
                    "Homing started - check status with get_position service"
                )

            # Reserve operation state before starting async thread to avoid races.
            self.operation_status = OperationStatus.HOMING
            self.last_operation_message = "Homing in progress..."

        # Start homing in background thread (this will handle the reset automatically)
        self.logger.info("Starting asynchronous homing operation...")
        self._start_async(self._async_home_operation)

        # Return immediately with status
        response.success = True
        self.logger.info("Homing operation initiated successfully")

        return response

    @handle_service_errors()
    def callback_get_position(self, request, response):
        """Handle get position requests with operation status."""
        response.axis_position = self.driver.get_position()
        response.success = True

        # Include operation status in the message
        status, status_msg = self.get_operation_status()
        if status != OperationStatus.IDLE:
            response.status_message = (
                f"Position: {response.axis_position:.2f}mm | Status: {status_msg}"
            )
        else:
            response.status_message = "Position retrieved"

        return response

    @handle_service_errors()
    def callback_set_velocity_parameters(self, request, response):
        """Handle velocity parameter setting requests."""
        # Convert from mm/s to device units
        min_vel = (
            None
            if request.min_velocity < 0
            else self._mm_per_s_to_device_units(request.min_velocity)
        )
        accel = (
            None
            if request.acceleration < 0
            else self._mm_per_s_to_device_units(request.acceleration)
        )
        max_vel = (
            None
            if request.max_velocity < 0
            else self._mm_per_s_to_device_units(request.max_velocity)
        )

        self.logger.debug(
            f"Setting velocity parameters: min={min_vel}, accel={accel}, "
            f"max={max_vel} (device units)"
        )
        self.logger.debug(
            f"Converted from mm/s: min={request.min_velocity}, "
            f"accel={request.acceleration}, max={request.max_velocity}"
        )

        result = self.driver.set_velocity_parameters(min_vel, accel, max_vel)

        response.success = True
        response.status_message = "Velocity parameters updated"

        # Convert back to mm/s for response
        if result:
            response.actual_min_velocity = self._device_units_to_mm_per_s(result[0])
            response.actual_acceleration = self._device_units_to_mm_per_s(result[1])
            response.actual_max_velocity = self._device_units_to_mm_per_s(result[2])

            self.logger.debug(
                f"Actual velocity parameters set: "
                f"min={response.actual_min_velocity:.2f}mm/s, "
                f"accel={response.actual_acceleration:.2f}mm/s², "
                f"max={response.actual_max_velocity:.2f}mm/s"
            )

        return response

    @handle_service_errors()
    def callback_get_velocity_parameters(self, request, response):
        """Handle velocity parameter query requests."""
        params = self.driver.get_velocity_parameters()
        response.success = True
        response.status_message = "Velocity parameters retrieved"

        if params is not None:
            # Convert from device units to mm/s
            response.min_velocity = self._device_units_to_mm_per_s(params[0])
            response.acceleration = self._device_units_to_mm_per_s(params[1])
            response.max_velocity = self._device_units_to_mm_per_s(params[2])

            self.logger.debug(
                f"Retrieved velocity parameters: "
                f"min={response.min_velocity:.2f}mm/s, "
                f"accel={response.acceleration:.2f}mm/s², "
                f"max={response.max_velocity:.2f}mm/s"
            )

        return response

    @handle_service_errors()
    def callback_shutdown(self, request, response):
        """Handle shutdown requests by homing and disconnecting."""
        self.logger.info("Shutdown requested. Homing device before disconnect...")
        self.driver.home()
        self.interface.disconnect()  # Use the interface to manage connection state
        response.success = True
        response.status_message = "Device homed and disconnected successfully."
        return response

    @handle_service_errors()
    def callback_get_operation_status(self, request, response):
        """Handle operation status requests."""
        status, status_msg = self.get_operation_status()

        response.success = True
        response.operation_status = status.value
        response.status_message = status_msg
        return response

    @handle_service_errors()
    def callback_emergency_stop(self, request, response):
        """Handle emergency stop requests."""
        # Check if the axis was moving before stopping
        was_moving = False
        try:
            was_moving = self.driver.is_moving()
        except Exception:
            # If we can't check, assume not moving.
            pass

        # Force stop any hardware movement immediately
        self.driver.stop()
        self.logger.warn("EMERGENCY STOP: Hardware movement halted immediately")

        # Update operation status to emergency stop
        with self.operation_lock:
            previous_status = self.operation_status
            self.operation_status = OperationStatus.EMERGENCY_STOP
            self.last_operation_message = (
                f"Emergency stop triggered (was: {previous_status.value})"
            )

        response.success = True
        response.was_moving = was_moving
        response.status_message = (
            f"Emergency stop executed - movement halted (was_moving: {was_moving})"
        )

        self.logger.warn(
            f"Emergency stop completed. Previous state: {previous_status.value}"
        )

        return response

    @handle_service_errors()
    def callback_stop(self, request, response):
        """Handle stop requests (non-emergency)."""
        was_moving = False
        try:
            was_moving = self.driver.is_moving()
        except Exception:
            pass

        self.driver.stop()
        self.logger.info("Stop requested - movement halted")

        with self.operation_lock:
            self.operation_status = OperationStatus.IDLE
            self.last_operation_message = "Stopped by request"

        response.success = True
        response.status_message = f"Stop executed (was_moving: {was_moving})"

        return response

    @handle_service_errors()
    def callback_jog_axis(self, request, response):
        """Handle axis jogging requests with simplified step-based movement."""
        # Safety check: only allow jogging if not in critical operations
        with self.operation_lock:
            critical_statuses = [
                OperationStatus.HOMING,
                OperationStatus.EMERGENCY_STOP,
            ]
            if self.operation_status in critical_statuses:
                response.success = False
                response.final_position = -1.0
                response.status_message = (
                    f"Jogging not allowed during {self.operation_status.value}"
                )
                self.logger.warn(response.status_message)
                return response

            if self.operation_status != OperationStatus.IDLE:
                response.success = False
                response.final_position = -1.0
                response.status_message = (
                    "Cannot jog: operation already in progress: "
                    f"{self.operation_status.value}"
                )
                return response

            self.operation_status = OperationStatus.JOGGING
            direction_str = "positive" if request.step_size >= 0 else "negative"
            self.last_operation_message = (
                f"Jogging {direction_str} by {abs(request.step_size):.2f}mm..."
            )

        step_size = request.step_size
        direction_str = "positive" if step_size >= 0 else "negative"
        self.logger.debug(f"Jog step: {step_size:+.2f}mm ({direction_str} direction)")

        try:
            # Use the simplified driver method
            if step_size >= 0:
                self.driver.jog_positive(abs(step_size))
            else:
                self.driver.jog_negative(abs(step_size))

            # Get final position
            final_pos = self.driver.get_position()

            with self.operation_lock:
                self.operation_status = OperationStatus.IDLE
                self.last_operation_message = (
                    f"Jog completed - position: {final_pos:.2f}mm"
                )

            response.success = True
            response.final_position = final_pos
            response.status_message = (
                f"Jog {step_size:+.2f}mm completed: {final_pos:.2f}mm"
            )
            return response
        except Exception as e:
            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"Jog failed: {e}"
            raise
