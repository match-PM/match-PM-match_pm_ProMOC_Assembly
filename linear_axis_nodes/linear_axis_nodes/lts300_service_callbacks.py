from .lts300_interface import Lts300Interface
from .lts300_node_config import Lts300Config
import threading
import time
from enum import Enum
import sys
import os

# Add promoc_assembly_interfaces to path for exception imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../promoc_assembly_interfaces'))

try:
    from promoc_assembly_interfaces.promoc_exceptions import (
        PositionOutOfBoundsError,
        MovementTimeoutError,
        HomingFailedError,
        CollisionDetectedError,
        SafetyViolation,
        SoftLimitViolationError,
        CommunicationError,
        HardwareError
    )
except ImportError:
    # Fallback if import fails - define dummy classes
    class PositionOutOfBoundsError(Exception):
        def __init__(self, msg, details=None):
            super().__init__(msg)
            self.details = details or {}
            self.error_code = 1202
    
    class MovementTimeoutError(Exception):
        def __init__(self, msg, details=None):
            super().__init__(msg)
            self.details = details or {}
            self.error_code = 1201
    
    class HomingFailedError(Exception):
        def __init__(self, msg, details=None):
            super().__init__(msg)
            self.details = details or {}
            self.error_code = 1204
    
    class CollisionDetectedError(Exception):
        def __init__(self, msg, details=None):
            super().__init__(msg)
            self.details = details or {}
            self.error_code = 1203
    
    class SafetyViolation(Exception):
        def __init__(self, msg, details=None):
            super().__init__(msg)
            self.details = details or {}
            self.error_code = 1300
    
    class SoftLimitViolationError(SafetyViolation):
        def __init__(self, msg, details=None):
            super().__init__(msg, details)
            self.error_code = 1301
    
    class CommunicationError(Exception):
        def __init__(self, msg, details=None):
            super().__init__(msg)
            self.details = details or {}
            self.error_code = 1101
    
    class HardwareError(Exception):
        def __init__(self, msg, details=None):
            super().__init__(msg)
            self.details = details or {}
            self.error_code = 1400



class OperationStatus(Enum):
    """Status enumeration for long-running operations."""
    IDLE = "idle"
    HOMING = "homing"
    MOVING = "moving"
    JOGGING = "jogging"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"

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


    def _device_units_to_mm_per_s(self, device_units: float) -> float:
        """Convert device velocity units to mm/s."""
        return device_units * self.config.velocity_conversion_factor

    def _mm_per_s_to_device_units(self, mm_per_s: float) -> float:
        """Convert mm/s to device velocity units."""
        return mm_per_s / self.config.velocity_conversion_factor


    def _collision_check(self, other_axis_position: float):
        """
        Checks for a potential collision using the current position of the other axis.
        
        Args:
            other_axis_position (float): The current position of the other axis, passed in by the node.
            
        Raises:
            CollisionDetectedError: If collision risk is detected.
        """
        if (other_axis_position is not None and
                other_axis_position > self.config.collision_threshold):
            raise CollisionDetectedError(
                f"Collision risk detected! Other axis at {other_axis_position:.2f}mm exceeds "
                f"threshold {self.config.collision_threshold}mm",
                details={
                    'other_axis_position': other_axis_position,
                    'collision_threshold': self.config.collision_threshold,
                    'axis_name': self.config.node_name
                }
            )

    def _validate_position(self, position: float):
        """
        Validates if a position is within the configured safety limits.
        
        Args:
            position (float): The target position to validate in mm.
            
        Raises:
            SoftLimitViolationError: If position is outside configured limits.
        """
        if position < self.config.min_position:
            raise SoftLimitViolationError(
                f"Position {position:.2f}mm below minimum limit {self.config.min_position:.2f}mm",
                details={
                    'requested_position': position,
                    'min_position': self.config.min_position,
                    'max_position': self.config.max_position,
                    'violation_type': 'min_limit'
                }
            )
        if position > self.config.max_position:
            raise SoftLimitViolationError(
                f"Position {position:.2f}mm exceeds maximum limit {self.config.max_position:.2f}mm",
                details={
                    'requested_position': position,
                    'min_position': self.config.min_position,
                    'max_position': self.config.max_position,
                    'violation_type': 'max_limit'
                }
            )

    def _validate_distance(self, distance: float):
        """
        Validates if a relative movement distance is within the configured safety limits.
        
        Args:
            distance (float): The movement distance to validate in mm.
            
        Raises:
            SoftLimitViolationError: If distance exceeds maximum single move limit.
        """
        abs_distance = abs(distance)
        if abs_distance > self.config.max_single_move:
            raise SoftLimitViolationError(
                f"Movement distance {abs_distance:.2f}mm exceeds maximum single move "
                f"limit {self.config.max_single_move:.2f}mm",
                details={
                    'requested_distance': distance,
                    'abs_distance': abs_distance,
                    'max_single_move': self.config.max_single_move,
                    'violation_type': 'max_distance'
                }
            )

    def _validate_target_position(self, current_pos: float, distance: float):
        """
        Validates if a relative movement would result in a valid target position.
        
        Args:
            current_pos (float): Current position in mm.
            distance (float): Movement distance in mm.
            
        Raises:
            SoftLimitViolationError: If target position would be outside limits.
        """
        target_pos = current_pos + distance
        self._validate_position(target_pos)

    def _async_move_operation(self, move_type: str, position: float):
        """
        Performs movement operation in a separate thread.
        
        Args:
            move_type: "absolute" or "relative"
            position: Target position or movement distance
        """
        try:
            with self.operation_lock:
                self.operation_status = OperationStatus.MOVING
                self.last_operation_message = f"Moving {move_type} to {position:.2f}mm..."
            
            self.logger.info(f"🎯 Starting {move_type} movement to {position:.2f}mm...")
            
            if move_type == "absolute":
                self.driver.move_absolute(position)
            else:  # relative
                self.driver.move_relative(position)
            
            self.logger.info(f"Hardware {move_type} movement command completed")
            
            # Get final position for confirmation
            try:
                final_pos = self.driver.get_position()
                self.logger.info(f"Final position after {move_type} movement: {final_pos:.2f}mm")
            except Exception as pos_e:
                self.logger.warn(f"Could not read position after movement: {pos_e}")
                final_pos = "unknown"
            
            with self.operation_lock:
                self.operation_status = OperationStatus.IDLE
                self.last_operation_message = f"Movement completed - final position: {final_pos}mm"
            
            self.logger.info(f"{move_type.capitalize()} movement completed successfully")
            
        except Exception as e:
            error_msg = str(e) if str(e).strip() else f"Unknown error during {move_type} movement"
            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"Movement failed: {error_msg}"
            
            self.logger.error(f"{move_type.capitalize()} movement failed: {error_msg}", exc_info=True)

    def _async_home_operation(self):
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
                self.logger.warn(f"⚠️ Could not read position after homing: {pos_e}")
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
                # Wrap in HomingFailedError for consistent error handling
                homing_error = HomingFailedError(
                    error_msg,
                    details={
                        'timeout': self.config.homing_timeout,
                        'original_error': str(e),
                        'error_type': 'timeout'
                    }
                )
            else:
                error_msg = str(e) if str(e).strip() else "Unknown error during homing"
                self.logger.error(f"❌ Homing operation failed: {error_msg}", exc_info=True)
                homing_error = HomingFailedError(
                    error_msg,
                    details={
                        'original_error': str(e),
                        'error_type': type(e).__name__
                    }
                )
            
            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"❌ Homing failed: {error_msg}"

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
        """
        Handle absolute movement service request.
        
        Uses custom exceptions for precise error handling.
        """
        start_time = time.time()
        
        try:
            # Check if another operation is already running
            with self.operation_lock:
                if self.operation_status != OperationStatus.IDLE:
                    response.success = False
                    response.status_message = f"⚠️ Operation already in progress: {self.operation_status.value}"
                    self.logger.warn(response.status_message)
                    return response

            # Safety validation - will raise SoftLimitViolationError if invalid
            self._validate_position(request.axis_position)

            # Collision check - will raise CollisionDetectedError if detected
            self._collision_check(other_axis_position)

            # Start movement in background thread
            self.logger.info(f'Starting asynchronous absolute movement to: {request.axis_position} mm')
            move_thread = threading.Thread(
                target=self._async_move_operation, 
                args=("absolute", request.axis_position), 
                daemon=True
            )
            move_thread.start()
            
            response.success = True
            response.status_message = f"🎯 Absolute movement to {request.axis_position:.2f}mm started - check status with get_operation_status"
            
        except SoftLimitViolationError as e:
            response.success = False
            response.status_message = f"🚫 Safety violation: {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Limit violation details: {e.details}")
            
        except CollisionDetectedError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Collision details: {e.details}")
            
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error starting move_absolute: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)
            
        return response

    def callback_move_relative(self, request, response, other_axis_position: float):
        """
        Handle relative movement service request.
        
        Uses custom exceptions for precise error handling.
        """
        start_time = time.time()
        
        try:
            # Check if another operation is already running
            with self.operation_lock:
                if self.operation_status != OperationStatus.IDLE:
                    response.success = False
                    response.status_message = f"⚠️ Operation already in progress: {self.operation_status.value}"
                    self.logger.warn(response.status_message)
                    return response

            # Safety validation for movement distance - will raise if invalid
            self._validate_distance(request.axis_position)

            # Safety validation for target position
            current_pos = self.driver.get_position()
            self._validate_target_position(current_pos, request.axis_position)

            # Collision check - will raise CollisionDetectedError if detected
            self._collision_check(other_axis_position)

            # Start movement in background thread
            self.logger.info(f'Starting asynchronous relative movement by: {request.axis_position} mm')
            move_thread = threading.Thread(
                target=self._async_move_operation, 
                args=("relative", request.axis_position), 
                daemon=True
            )
            move_thread.start()
            
            response.success = True
            response.status_message = f"🎯 Relative movement by {request.axis_position:.2f}mm started - check status with get_operation_status"
            
        except SoftLimitViolationError as e:
            response.success = False
            response.status_message = f"🚫 Safety violation: {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Limit violation details: {e.details}")
            
        except CollisionDetectedError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Collision details: {e.details}")
            
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error in move_relative: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)
            
        return response

    def callback_home(self, request, response):
        """Handle homing requests - automatically resets from emergency/error states."""
        # Check current status and allow homing from recoverable states
        with self.operation_lock:
            current_status = self.operation_status
            
            # Allow homing from IDLE, EMERGENCY_STOP, and ERROR states
            if current_status not in [OperationStatus.IDLE, OperationStatus.EMERGENCY_STOP, OperationStatus.ERROR]:
                response.success = False
                response.status_message = f"⚠️ Cannot home during {current_status.value}. Stop operation first."
                self.logger.warn(response.status_message)
                return response
            
            # If coming from emergency/error state, log the reset
            if current_status in [OperationStatus.EMERGENCY_STOP, OperationStatus.ERROR]:
                self.logger.info(f"🔄 Resetting from {current_status.value} state and homing...")
                response.status_message = f"🔄 Resetting from {current_status.value} and homing started - check status with get_position service"
            else:
                response.status_message = "🏠 Homing started - check status with get_position service"
        
        try:
            # Start homing in background thread (this will handle the reset automatically)
            self.logger.info('Starting asynchronous homing operation...')
            homing_thread = threading.Thread(target=self._async_home_operation, daemon=True)
            homing_thread.start()
            
            # Return immediately with status
            response.success = True
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
        
        except CommunicationError as e:
            response.axis_position = -1.0
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Communication error details: {e.details}")
            
        except Exception as e:
            response.axis_position = -1.0
            response.success = False
            response.status_message = f"❌ Error getting position: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)
            
        return response
        
    def callback_set_velocity_parameters(self, request, response):
        """Handle velocity parameter setting requests."""
        try:
            # Convert from mm/s to device units
            min_vel = None if request.min_velocity < 0 else self._mm_per_s_to_device_units(request.min_velocity)
            accel = None if request.acceleration < 0 else self._mm_per_s_to_device_units(request.acceleration)
            max_vel = None if request.max_velocity < 0 else self._mm_per_s_to_device_units(request.max_velocity)
            
            self.logger.info(f"Setting velocity parameters: min={min_vel}, accel={accel}, max={max_vel} (device units)")
            self.logger.info(f"Converted from mm/s: min={request.min_velocity}, accel={request.acceleration}, max={request.max_velocity}")
            
            result = self.driver.set_velocity_parameters(min_vel, accel, max_vel)
            
            response.success = True
            response.status_message = "✅ Velocity parameters updated"
            
            # Convert back to mm/s for response
            if result:
                response.actual_min_velocity = self._device_units_to_mm_per_s(result[0])
                response.actual_acceleration = self._device_units_to_mm_per_s(result[1])
                response.actual_max_velocity = self._device_units_to_mm_per_s(result[2])
                
                self.logger.info(f"Actual velocity parameters set: "
                               f"min={response.actual_min_velocity:.2f}mm/s, "
                               f"accel={response.actual_acceleration:.2f}mm/s², "
                               f"max={response.actual_max_velocity:.2f}mm/s")
        
        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")
            
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error setting velocity: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)
            
        return response

    def callback_get_velocity_parameters(self, request, response):
        """Handle velocity parameter query requests."""
        try:
            params = self.driver.get_velocity_parameters()
            response.success = True
            response.status_message = "✅ Velocity parameters retrieved"
            
            if params is not None:
                # Convert from device units to mm/s
                response.min_velocity = self._device_units_to_mm_per_s(params[0])
                response.acceleration = self._device_units_to_mm_per_s(params[1])
                response.max_velocity = self._device_units_to_mm_per_s(params[2])
                
                # Also set actual values (same as regular values for get)
                response.actual_min_velocity = response.min_velocity
                response.actual_acceleration = response.acceleration
                response.actual_max_velocity = response.max_velocity
                
                self.logger.info(f"Retrieved velocity parameters: "
                               f"min={response.min_velocity:.2f}mm/s, "
                               f"accel={response.acceleration:.2f}mm/s², "
                               f"max={response.max_velocity:.2f}mm/s")
        
        except CommunicationError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Communication error details: {e.details}")
                               
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error getting velocity: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)
            
        return response

    def callback_shutdown(self, request, response):
        """Handle shutdown requests by homing and disconnecting."""
        try:
            self.logger.info("Shutdown requested. Homing device before disconnect...")
            self.driver.home()
            self.interface.disconnect() # Use the interface to manage connection state
            response.success = True
            response.status_message = "✅ Device homed and disconnected successfully."
            
        except HomingFailedError as e:
            response.success = False
            response.status_message = f"⚠️ Shutdown partial: {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Homing failed details: {e.details}")
            # Still try to disconnect
            try:
                self.interface.disconnect()
            except:
                pass
                
        except CommunicationError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Communication error details: {e.details}")
            
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error during shutdown: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)
            
        return response

    def callback_get_operation_status(self, request, response):
        """Handle operation status requests."""
        try:
            status, status_msg = self.get_operation_status()
            
            response.success = True
            response.operation_status = status.value
            response.status_message = status_msg
            
        except Exception as e:
            response.success = False
            response.operation_status = "error"
            response.status_message = f"❌ Error getting operation status: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_emergency_stop(self, request, response):
        """Handle emergency stop requests - immediately stop all movement and interrupt operations."""
        try:
            # Check if the axis was moving before stopping
            was_moving = False
            try:
                was_moving = self.driver.is_moving()
            except:
                pass  # If we can't check, assume not moving
            
            # Force stop any hardware movement immediately
            self.driver.stop()
            self.logger.warn("🛑 EMERGENCY STOP: Hardware movement halted immediately")
            
            # Update operation status to emergency stop
            with self.operation_lock:
                previous_status = self.operation_status
                self.operation_status = OperationStatus.EMERGENCY_STOP
                self.last_operation_message = f"🛑 Emergency stop triggered (was: {previous_status.value})"
            
            response.success = True
            response.was_moving = was_moving
            response.status_message = f"🛑 Emergency stop executed - movement halted (was_moving: {was_moving})"
            
            self.logger.warn(f"🛑 Emergency stop completed. Previous state: {previous_status.value}")
            
        except Exception as e:
            response.success = False
            response.was_moving = False
            response.status_message = f"❌ Emergency stop failed: {str(e)}"
            self.logger.error(response.status_message)
        
        return response

    def callback_jog_axis(self, request, response):
        """Handle axis jogging requests with simplified step-based movement."""
        try:
            # Safety check: only allow jogging if not in critical operations
            with self.operation_lock:
                if self.operation_status in [OperationStatus.HOMING, OperationStatus.EMERGENCY_STOP]:
                    response.success = False
                    response.final_position = -1.0
                    response.status_message = f"🚫 Jogging not allowed during {self.operation_status.value}"
                    self.logger.warn(response.status_message)
                    return response
                
                if self.operation_status != OperationStatus.IDLE:
                    response.success = False
                    response.final_position = -1.0
                    response.status_message = f"⚠️ Cannot jog: operation already in progress: {self.operation_status.value}"
                    return response
                
                self.operation_status = OperationStatus.JOGGING
                direction_str = "positive" if request.step_size >= 0 else "negative"
                self.last_operation_message = f"Jogging {direction_str} by {abs(request.step_size):.2f}mm..."
            
            try:
                step_size = request.step_size
                self.logger.info(f"🕹️ Jog step: {step_size:+.2f}mm ({'positive' if step_size >= 0 else 'negative'} direction)")
                
                # Use the simplified driver method
                if step_size >= 0:
                    self.driver.jog_positive(abs(step_size))
                else:
                    self.driver.jog_negative(abs(step_size))
                
                # Get final position
                final_pos = self.driver.get_position()
                
                with self.operation_lock:
                    self.operation_status = OperationStatus.IDLE
                    self.last_operation_message = f"✅ Jog completed - position: {final_pos:.2f}mm"
                
                response.success = True
                response.final_position = final_pos
                response.status_message = f"✅ Jog {step_size:+.2f}mm completed: {final_pos:.2f}mm"
                
            except SoftLimitViolationError as e:
                with self.operation_lock:
                    self.operation_status = OperationStatus.ERROR
                    self.last_operation_message = f"⚠️ Jog limit violation: {str(e)}"
                response.success = False
                response.final_position = -1.0
                response.status_message = f"⚠️ {str(e)}"
                self.logger.warn(response.status_message)
                self.logger.debug(f"Soft limit violation details: {e.details}")
                
            except HardwareError as e:
                with self.operation_lock:
                    self.operation_status = OperationStatus.ERROR
                    self.last_operation_message = f"❌ Jog hardware error: {str(e)}"
                response.success = False
                response.final_position = -1.0
                response.status_message = f"⚠️ {str(e)}"
                self.logger.error(response.status_message)
                self.logger.debug(f"Hardware error details: {e.details}")
                
            except Exception as jog_e:
                with self.operation_lock:
                    self.operation_status = OperationStatus.ERROR
                    self.last_operation_message = f"❌ Jog failed: {str(jog_e)}"
                raise jog_e
        
        except Exception as e:
            response.success = False
            response.final_position = -1.0
            response.status_message = f"❌ Jog operation failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)
            
            # Reset status on error
            with self.operation_lock:
                self.operation_status = OperationStatus.ERROR
                self.last_operation_message = f"❌ Jog error: {str(e)}"
        
        return response

