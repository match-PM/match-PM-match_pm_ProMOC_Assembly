from .lts300_interface import Lts300Interface
from .lts300_node_config import Lts300Config
import threading
import time
from enum import Enum


class OperationStatus(Enum):
    """Status enumeration for long-running operations."""
    IDLE = "idle"
    HOMING = "homing"
    MOVING = "moving"
    ERROR = "error"


class ServiceCallbacks:
    """
    Handles all ROS service callback logic for the LTS300 node, decoupled from the ROS node.
    This class contains the business logic for motion commands and other services.
    """

    def __init__(self, logger, interface: Lts300Interface, config: Lts300Config):
        """
        Initializes the callbacks with explicit dependencies.

        Args:
            logger: The ROS 2 logger instance.
            interface: The hardware interface for the LTS300 driver.
            config: The dataclass holding all node parameters.
        """
        self.logger = logger
        self.interface = interface
        self.config = config
        self.driver = self.interface.driver  # Direct access to the driver instance

        # Status tracking for long operations
        self.operation_status = OperationStatus.IDLE
        self.operation_lock = threading.Lock()
        self.last_operation_message = ""

    # --- Unit Conversion Methods ---

    def _device_units_to_mm_per_s(self, device_units: float) -> float:
        """Convert device velocity units to mm/s."""
        return device_units * self.config.velocity_conversion_factor

    def _mm_per_s_to_device_units(self, mm_per_s: float) -> float:
        """Convert mm/s to device velocity units."""
        return mm_per_s / self.config.velocity_conversion_factor

    # --- Safety and Validation Methods ---

    def _collision_check(self, other_axis_position: float) -> bool:
        """
        Checks for a potential collision using the current position of the other axis.

        Args:
            other_axis_position (float): The current position of the other axis, passed in by the node.
        """
        if (other_axis_position is not None and
                other_axis_position > self.config.collision_threshold):
            return True
        return False

    def _validate_position(self, position: float) -> tuple[bool, str]:
        """
        Validates if a position is within the configured safety limits.

        Args:
            position (float): The target position to validate in mm.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if position < self.config.min_position:
            return False, f"Position {position:.2f}mm below minimum limit {self.config.min_position:.2f}mm"
        if position > self.config.max_position:
            return False, f"Position {position:.2f}mm exceeds maximum limit {self.config.max_position:.2f}mm"
        return True, ""

    def _validate_distance(self, distance: float) -> tuple[bool, str]:
        """
        Validates if a relative movement distance is within the configured safety limits.

        Args:
            distance (float): The movement distance to validate in mm.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        abs_distance = abs(distance)
        if abs_distance > self.config.max_single_move:
            return False, f"Movement distance {abs_distance:.2f}mm exceeds maximum single move limit {self.config.max_single_move:.2f}mm"
        return True, ""

    def _validate_target_position(self, current_pos: float, distance: float) -> tuple[bool, str]:
        """
        Validates if a relative movement would result in a valid target position.

        Args:
            current_pos (float): Current position in mm.
            distance (float): Movement distance in mm.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        target_pos = current_pos + distance
        return self._validate_position(target_pos)

    def _async_move_operation(self, move_type: str, position: float):
        """
        Performs movement operation in a separate thread.
        Enhanced with stop-awareness.

        Args:
            move_type: "absolute" or "relative"
            position: Target position or movement distance
        """
        try:
            with self.operation_lock:
                # Check if we were stopped before starting
                if self.operation_status == OperationStatus.IDLE:
                    self.logger.info(
                        f"🛑 Movement cancelled before start (stopped)")
                    return

                self.operation_status = OperationStatus.MOVING
                self.last_operation_message = f"Moving {move_type} to {position:.2f}mm..."

            self.logger.info(
                f"🎯 Starting {move_type} movement to {position:.2f}mm...")

            if move_type == "absolute":
                self.driver.move_absolute(position)
            else:  # relative
                self.driver.move_relative(position)

            self.logger.info(
                f"🎯 Hardware {move_type} movement command completed")

            # Get final position for confirmation
            try:
                final_pos = self.driver.get_position()
                self.logger.info(
                    f"📍 Final position after {move_type} movement: {final_pos:.2f}mm")
            except Exception as pos_e:
                self.logger.warn(
                    f"⚠️ Could not read position after movement: {pos_e}")
                final_pos = "unknown"

            # Check if we were stopped during movement
            with self.operation_lock:
                if self.operation_status == OperationStatus.MOVING:  # Only update if still moving
                    self.operation_status = OperationStatus.IDLE
                    self.last_operation_message = f"✅ Movement completed - final position: {final_pos}mm"
                else:
                    self.logger.info(
                        f"🛑 Movement was stopped during execution")
                    return

            self.logger.info(
                f"✅ {move_type.capitalize()} movement completed successfully")

        except Exception as e:
            error_msg = str(e) if str(e).strip(
            ) else f"Unknown error during {move_type} movement"

            # Check if this was a stop-related exception
            if "stop" in error_msg.lower() or "abort" in error_msg.lower():
                self.logger.info(f"🛑 Movement stopped: {error_msg}")
                with self.operation_lock:
                    if self.operation_status == OperationStatus.MOVING:
                        self.operation_status = OperationStatus.IDLE
                        self.last_operation_message = "🛑 Movement stopped"
            else:
                with self.operation_lock:
                    self.operation_status = OperationStatus.ERROR
                    self.last_operation_message = f"❌ Movement failed: {error_msg}"

                self.logger.error(
                    f"❌ {move_type.capitalize()} movement failed: {error_msg}")

                # Additional debug information
                import traceback
                self.logger.error(
                    f"❌ Movement traceback: {traceback.format_exc()}")

    def _async_home_operation(self):
        """
        Performs homing operation in a separate thread.
        Enhanced with stop-awareness.
        """
        try:
            with self.operation_lock:
                # Check if we were stopped before starting
                if self.operation_status == OperationStatus.IDLE:
                    self.logger.info(
                        f"🛑 Homing cancelled before start (stopped)")
                    return

                self.operation_status = OperationStatus.HOMING
                self.last_operation_message = "Homing in progress..."

            self.logger.info("🏠 Starting homing operation...")

            # Call the actual homing operation
            self.driver.home(timeout=self.config.homing_timeout)
            self.logger.info("🏠 Hardware homing command completed")

            # Get final position for confirmation
            try:
                final_pos = self.driver.get_position()
                self.logger.info(f"📍 Post-homing position: {final_pos:.2f}mm")
            except Exception as pos_e:
                self.logger.warn(
                    f"⚠️ Could not read position after homing: {pos_e}")
                final_pos = "unknown"

            # Check if we were stopped during homing
            with self.operation_lock:
                if self.operation_status == OperationStatus.HOMING:  # Only update if still homing
                    self.operation_status = OperationStatus.IDLE
                    self.last_operation_message = f"✅ Homing completed successfully (position: {final_pos}mm)"
                else:
                    self.logger.info(f"🛑 Homing was stopped during execution")
                    return

            self.logger.info("✅ Homing operation completed successfully")

        except Exception as e:
            # Handle specific timeout errors and stop conditions
            if "ThorlabsTimeoutError" in str(type(e)) or "timeout" in str(e).lower():
                error_msg = "Homing timeout - operation may still be in progress on hardware"
                self.logger.warn(f"⏰ {error_msg}")
            elif "stop" in str(e).lower() or "abort" in str(e).lower():
                self.logger.info(f"🛑 Homing stopped: {str(e)}")
                with self.operation_lock:
                    if self.operation_status == OperationStatus.HOMING:
                        self.operation_status = OperationStatus.IDLE
                        self.last_operation_message = "🛑 Homing stopped"
                return
            else:
                error_msg = str(e) if str(e).strip(
                ) else "Unknown error during homing"
                self.logger.error(f"❌ Homing operation failed: {error_msg}")

            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"❌ Homing failed: {error_msg}"

            # Additional debug information for non-timeout errors
            if "timeout" not in str(e).lower():
                import traceback
                self.logger.error(
                    f"❌ Homing traceback: {traceback.format_exc()}")
        """
        Performs homing operation in a separate thread.
        Updates operation status and handles errors.
        """
        try:
            with self.operation_lock:
                self.operation_status = OperationStatus.HOMING
                self.last_operation_message = "Homing in progress..."

            self.logger.info("🏠 Starting homing operation...")

            # Call the actual homing operation (now with configurable timeout)
            self.driver.home(timeout=self.config.homing_timeout)
            self.logger.info("🏠 Hardware homing command completed")

            # Get final position for confirmation
            try:
                final_pos = self.driver.get_position()
                self.logger.info(f"📍 Post-homing position: {final_pos:.2f}mm")
            except Exception as pos_e:
                self.logger.warn(
                    f"⚠️ Could not read position after homing: {pos_e}")
                final_pos = "unknown"

            with self.operation_lock:
                self.operation_status = OperationStatus.IDLE
                self.last_operation_message = f"✅ Homing completed successfully (position: {final_pos}mm)"

            self.logger.info("✅ Homing operation completed successfully")

        except Exception as e:
            # Handle specific timeout errors
            if "ThorlabsTimeoutError" in str(type(e)) or "timeout" in str(e).lower():
                error_msg = "Homing timeout - operation may still be in progress on hardware"
                self.logger.warn(f"⏰ {error_msg}")
            else:
                error_msg = str(e) if str(e).strip(
                ) else "Unknown error during homing"
                self.logger.error(f"❌ Homing operation failed: {error_msg}")

            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"❌ Homing failed: {error_msg}"

            # Additional debug information for non-timeout errors
            if "timeout" not in error_msg.lower():
                import traceback
                self.logger.error(
                    f"❌ Homing traceback: {traceback.format_exc()}")

    def get_operation_status(self) -> tuple[OperationStatus, str]:
        """
        Returns the current operation status and message.

        Returns:
            tuple[OperationStatus, str]: (status, message)
        """
        with self.operation_lock:
            return self.operation_status, self.last_operation_message

    # --- Service Callback Implementations ---

    def callback_move_absolute(self, request, response, other_axis_position: float):
        """Handle absolute movement, receiving the other axis position as an argument."""
        # Check if another operation is already running
        with self.operation_lock:
            if self.operation_status != OperationStatus.IDLE:
                response.success = False
                response.status_message = f"⚠️ Operation already in progress: {self.operation_status.value}"
                self.logger.warn(response.status_message)
                return response

        # Safety validation for position limits
        is_valid_pos, pos_error = self._validate_position(
            request.axis_position)
        if not is_valid_pos:
            response.success = False
            response.status_message = f"🚫 Safety violation: {pos_error}"
            self.logger.warn(response.status_message)
            return response

        # Collision check
        if self._collision_check(other_axis_position):
            response.success = False
            response.status_message = f"⚠️ Collision risk! Other axis at {other_axis_position:.2f}mm > {self.config.collision_threshold}mm."
            self.logger.warn(response.status_message)
            return response

        try:
            # Start movement in background thread
            self.logger.info(
                f'Starting asynchronous absolute movement to: {request.axis_position} mm')
            move_thread = threading.Thread(
                target=self._async_move_operation,
                args=("absolute", request.axis_position),
                daemon=True
            )
            move_thread.start()

            response.success = True
            response.status_message = f"🎯 Absolute movement to {request.axis_position:.2f}mm started - check status with get_operation_status"
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error starting move_absolute: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_move_relative(self, request, response, other_axis_position: float):
        """Handle relative movement requests."""
        # Check if another operation is already running
        with self.operation_lock:
            if self.operation_status != OperationStatus.IDLE:
                response.success = False
                response.status_message = f"⚠️ Operation already in progress: {self.operation_status.value}"
                self.logger.warn(response.status_message)
                return response

        # Safety validation for movement distance
        is_valid_dist, dist_error = self._validate_distance(
            request.axis_position)
        if not is_valid_dist:
            response.success = False
            response.status_message = f"🚫 Safety violation: {dist_error}"
            self.logger.warn(response.status_message)
            return response

        # Safety validation for target position
        try:
            current_pos = self.driver.get_position()
            is_valid_target, target_error = self._validate_target_position(
                current_pos, request.axis_position)
            if not is_valid_target:
                response.success = False
                response.status_message = f"🚫 Safety violation: {target_error}"
                self.logger.warn(response.status_message)
                return response
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error getting current position for safety check: {str(e)}"
            self.logger.error(response.status_message)
            return response

        # Collision check
        if self._collision_check(other_axis_position):
            response.success = False
            response.status_message = f"⚠️ Collision risk! Other axis at {other_axis_position:.2f}mm > {self.config.collision_threshold}mm."
            self.logger.warn(response.status_message)
            return response

        try:
            # Start movement in background thread
            self.logger.info(
                f'Starting asynchronous relative movement by: {request.axis_position} mm')
            move_thread = threading.Thread(
                target=self._async_move_operation,
                args=("relative", request.axis_position),
                daemon=True
            )
            move_thread.start()

            response.success = True
            response.status_message = f"🎯 Relative movement by {request.axis_position:.2f}mm started - check status with get_operation_status"
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error starting move_relative: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_home(self, request, response):
        """Handle homing requests asynchronously."""
        # Check if another operation is already running
        with self.operation_lock:
            if self.operation_status != OperationStatus.IDLE:
                response.success = False
                response.status_message = f"⚠️ Operation already in progress: {self.operation_status.value}"
                self.logger.warn(response.status_message)
                return response

        try:
            # Start homing in background thread
            self.logger.info('Starting asynchronous homing operation...')
            homing_thread = threading.Thread(
                target=self._async_home_operation, daemon=True)
            homing_thread.start()

            # Return immediately with status
            response.success = True
            response.status_message = "🏠 Homing started - check status with get_position service"
            self.logger.info("✅ Homing operation initiated successfully")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error starting homing: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_get_position(self, request, response):
        """Handle get position requests with operation status."""
        try:
            response.axis_position = self.driver.get_position()
            response.success = True

            # Include operation status in the message
            status, status_msg = self.get_operation_status()
            if status != OperationStatus.IDLE:
                response.status_message = f"📍 Position: {response.axis_position:.2f}mm | Status: {status_msg}"
            else:
                response.status_message = "✅ Position retrieved"

        except Exception as e:
            response.axis_position = -1.0
            response.success = False
            response.status_message = f"❌ Error getting position: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_set_velocity_parameters(self, request, response):
        """Handle velocity parameter setting requests."""
        try:
            min_vel = None if request.min_velocity < 0 else request.min_velocity
            accel = None if request.acceleration < 0 else request.acceleration
            max_vel = None if request.max_velocity < 0 else request.max_velocity

            result = self.driver.set_velocity_parameters(
                min_vel, accel, max_vel)

            response.success = True
            response.status_message = "✅ Velocity parameters updated"
            response.actual_min_velocity, response.actual_acceleration, response.actual_max_velocity = result
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error setting velocity: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_get_velocity_parameters(self, request, response):
        """Handle velocity parameter query requests."""
        try:
            params = self.driver.get_velocity_parameters()
            response.success = True
            response.status_message = "✅ Velocity parameters retrieved"
            response.min_velocity, response.acceleration, response.max_velocity = params

            if params is not None:
                response.actual_min_velocity, response.actual_acceleration, response.actual_max_velocity = params
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error getting velocity: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_shutdown(self, request, response):
        """Handle shutdown requests by homing and disconnecting."""
        try:
            self.logger.info(
                "Shutdown requested. Homing device before disconnect...")
            self.driver.home()
            self.interface.disconnect()  # Use the interface to manage connection state
            response.success = True
            response.status_message = "✅ Device homed and disconnected successfully."
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error during shutdown: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_get_operation_status(self, request, response):
        """Handle operation status requests."""
        try:
            status, status_msg = self.get_operation_status()

            response.success = True
            response.operation_status = status.value
            response.status_message = status_msg
            response.is_busy = (status != OperationStatus.IDLE)

        except Exception as e:
            response.success = False
            response.operation_status = "error"
            response.status_message = f"❌ Error getting operation status: {str(e)}"
            response.is_busy = False
            self.logger.error(response.status_message)
        return response

    def callback_stop(self, request, response):
        """Handle stop request - can interrupt ongoing operations."""
        try:
            # Call the Hardware to stop motion immediately
            self.driver.stop()
            # Update operation status
            with self.operation_lock:
                self.operation_status = OperationStatus.IDLE
                self.last_operation_message = "⏹️ Motion stopped by user"
            response.success = True
            response.status_message = "⏹️ Motion stopped successfully"
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error stopping motion: {str(e)}"
            self.logger.error(response.status_message)

            # Even if stop fails, reset status to prevent deadlock
            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"❌ Stop failed: {str(e)}"
        return response

    def callback_jog_step(self, request, response, other_axis_position: float):
        """Handle single jog step requests."""
        # Check if another operation is already running
        with self.operation_lock:
            if self.operation_status != OperationStatus.IDLE:
                response.success = False
                response.status_message = f"⚠️ Operation already in progress: {self.operation_status.value}"
                self.logger.warn(response.status_message)
                return response

        try:
            # Normalize direction to ±1
            direction = 1 if request.direction >= 0 else -1

            # Get current position for validation
            current_pos = self.driver.get_position()

            # Calculate target position based on jog step
            jog_step = self.driver.get_jog_step_size() * direction  # Get configured step size
            target_pos = current_pos + jog_step

            # Safety validation for target position
            is_valid_target, target_error = self._validate_position(target_pos)
            if not is_valid_target:
                response.success = False
                response.status_message = f"🚫 Safety violation: {target_error}"
                self.logger.warn(response.status_message)
                return response

            # Collision check
            if self._collision_check(other_axis_position):
                response.success = False
                response.status_message = f"⚠️ Collision risk! Other axis at {other_axis_position:.2f}mm > {self.config.collision_threshold}mm."
                self.logger.warn(response.status_message)
                return response

            # Execute jog step
            self.logger.info(
                f"🎮 Executing jog step: direction={direction}, step={abs(jog_step):.3f}mm")

            # Option 1: If driver has dedicated jog_step method
            if hasattr(self.driver, 'jog_step'):
                self.driver.jog_step(direction)
            # Option 2: Use relative move with jog step size
            else:
                self.driver.move_relative(jog_step)

            # Get new position
            new_pos = self.driver.get_position()

            response.success = True
            response.status_message = f"🎮 Jog step completed: {current_pos:.3f}mm → {new_pos:.3f}mm"
            response.final_position = new_pos
            self.logger.info(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error during jog step: {str(e)}"
            response.final_position = -1.0
            self.logger.error(response.status_message)

        return response

    def callback_get_jog_parameters(self, request, response):
        """Handle jog parameter query requests."""
        try:
            step_size, speed = self.driver.get_jog_parameters()

            response.success = True
            response.status_message = "✅ Jog parameters retrieved"
            response.step_size = step_size
            response.speed = speed if speed is not None else -1.0

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error getting jog parameters: {str(e)}"
            response.step_size = -1.0
            response.speed = -1.0
            self.logger.error(response.status_message)
        return response

    def callback_set_jog_parameters(self, request, response):
        """Handle jog parameter setting requests."""
        try:
            # Validate jog step size
            step_size = abs(request.step_size)  # Ensure positive
            if hasattr(self.config, 'max_jog_step') and step_size > self.config.max_jog_step:
                response.success = False
                response.status_message = f"🚫 Jog step {step_size:.3f}mm exceeds maximum {self.config.max_jog_step:.3f}mm"
                self.logger.warn(response.status_message)
                return response

            # Validate jog speed
            jog_speed = request.speed if request.speed > 0 else None
            if jog_speed and hasattr(self.config, 'max_jog_speed') and jog_speed > self.config.max_jog_speed:
                response.success = False
                response.status_message = f"🚫 Jog speed {jog_speed:.2f}mm/s exceeds maximum {self.config.max_jog_speed:.2f}mm/s"
                self.logger.warn(response.status_message)
                return response

            # Set jog parameters in driver
            result = self.driver.set_jog_parameters(step_size, jog_speed)

            response.success = True
            response.status_message = f"✅ Jog parameters set: step={step_size:.3f}mm"
            if jog_speed:
                response.status_message += f", speed={jog_speed:.2f}mm/s"

            # Return actual values if driver provides them
            if isinstance(result, tuple):
                response.actual_step_size, response.actual_speed = result
            else:
                response.actual_step_size = step_size
                response.actual_speed = jog_speed or -1.0

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error setting jog parameters: {str(e)}"
            self.logger.error(response.status_message)
        return response
