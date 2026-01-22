# real Hardware drive neccesary for hardware connection

import time
import warnings
from typing import Optional, Tuple
import struct
import sys
import os

# Try to import Thorlabs library
try:
    from pylablib.devices import Thorlabs
except ImportError as e:
    Thorlabs = None  # Set to None if import fails

from .linear_axis_driver import LinearAxisDriver
from promoc_core.promoc_exceptions import (
    DeviceNotFoundError,
    CommunicationTimeoutError,
    CommunicationError,
    HardwareError,
    HomingFailedError,
    MovementTimeoutError,
    SoftLimitViolationError,
    DriverNotAvailableError
)

# Alias for backwards compatibility
ConnectionTimeoutError = CommunicationTimeoutError
ConnectionError = CommunicationError

# Suppress pylablib warnings during import
warnings.filterwarnings("ignore", message="can't recognize the stage name*")
warnings.filterwarnings("ignore", message="can't recognize motor model*")

ABSOLUTE_MAX_POSITION = 300.0


class ThorlabsLTS300Driver(LinearAxisDriver):
    def __init__(self, logger):
        """
        Initialize the Thorlabs LTS300 driver.

        Args:
            logger: ROS2 logger instance from parent node for logging messages.
        """
        self.logger = logger
        self.device: Optional[Thorlabs.KinesisMotor] = None  # type: ignore
        self.connected: bool = False
        self.serial_no: Optional[str] = None
        self.axis_type: Optional[str] = None
        # LTS300 uses 409600 device units per mm
        self.device_units_per_mm: float = 409600.0
        self.x_axis_serial: Optional[str] = None
        self.z_axis_serial: Optional[str] = None

        # Communication lock to prevent concurrent hardware access
        import threading
        self._comm_lock = threading.Lock()
        self._last_position_cache = 0.0
        self._last_position_time = 0.0
        self._poll_interval_s = 0.1
        self._poll_stop_event = threading.Event()
        self._poll_thread = None

    def connect(self, port: str = None) -> bool:
        """Connect to the Thorlabs LTS300 device"""
        if Thorlabs is None:
            raise DriverNotAvailableError(
                "Thorlabs library (pylablib) not available",
                details={'library': 'pylablib', 'module': 'Thorlabs'}
            )

        try:
            if not port:
                raise DeviceNotFoundError(
                    "No port specified for connection",
                    details={'port': port}
                )

            self.logger.info(f"Connecting to LTS300 on port {port}...")

            # Convert /dev/serial/by-id/... to /dev/ttyUSB* if needed
            actual_port = port
            if '/dev/serial/by-id/' in port:
                try:
                    import os
                    actual_port = os.readlink(port)
                    if not actual_port.startswith('/dev/'):
                        actual_port = '/dev/' + os.path.basename(actual_port)
                    self.logger.debug(f"Converted {port} to {actual_port}")
                except Exception as e:
                    self.logger.warn(f"Could not resolve symlink: {e}")
                    # Fallback: try to find ttyUSB device
                    import glob
                    usb_devices = glob.glob('/dev/ttyUSB*')
                    if usb_devices:
                        actual_port = usb_devices[0]  # Take first available
                        self.logger.info(f"Using fallback port: {actual_port}")

            # Now connect using the actual ttyUSB port
            self.device = Thorlabs.KinesisMotor(actual_port, scale="m")

            # Read the serial number from device
            device_info = self.device.get_device_info()
            self.serial_no = str(device_info[0])
            self.logger.info(f"Detected serial number: {self.serial_no}")

            self.connected = True
            self.logger.info(
                f"Connected to Thorlabs LTS300 (S/N: {self.serial_no}) on port {actual_port}")

            return True

        except (DriverNotAvailableError, DeviceNotFoundError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            raise HardwareError(
                f"Connection failed: {type(e).__name__}: {e}",
                details={'port': port, 'error_type': type(
                    e).__name__, 'error': str(e)}
            )

    def disconnect(self):
        """Disconnect from the device and cleanup resources."""
        if self.connected and self.device:
            try:
                self.stop_position_polling()
                self.device.close()
                self.connected = False
                self.logger.info('Device disconnected')
            except Exception as e:
                self.logger.error(
                    f'Error during disconnect: {e}')

    # POSITION POLLING

    def start_position_polling(self, interval_s: float = 0.1):
        """Start a background thread to poll the device position regularly."""
        if interval_s <= 0:
            return

        self._poll_interval_s = float(interval_s)

        if self._poll_thread and self._poll_thread.is_alive():
            return

        self._poll_stop_event.clear()

        import threading

        def _poll_loop():
            while not self._poll_stop_event.is_set():
                if not self.connected or not self.device:
                    time.sleep(self._poll_interval_s)
                    continue

                acquired = self._comm_lock.acquire(timeout=0.05)
                if acquired:
                    try:
                        position = self.device.get_position() / self.device_units_per_mm
                        self._last_position_cache = position
                        self._last_position_time = time.time()
                    except Exception as e:
                        self.logger.debug(f'Position polling error: {e}')
                    finally:
                        self._comm_lock.release()
                time.sleep(self._poll_interval_s)

        self._poll_thread = threading.Thread(target=_poll_loop, daemon=True)
        self._poll_thread.start()
        self.logger.info(
            f'Position polling started ({self._poll_interval_s:.3f}s interval)')

    def stop_position_polling(self):
        """Stop the background position polling thread."""
        self._poll_stop_event.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
        self._poll_thread = None

    def move_absolute(self, position: float):
        """Move to absolute position in millimeters."""
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        self.logger.debug(f'Moving to absolute position: {position} mm')

        try:
            # Start the movement
            with self._comm_lock:
                self.device.move_to(
                    position * self.device_units_per_mm, scale=False)
        except Exception as e:
            raise HardwareError(
                f"Failed to start movement: {str(e)}",
                details={'target_position': position, 'error': str(e)}
            )

        # Wait for movement completion with robust error handling
        import time
        max_wait_time = 300.0  # 5 minutes maximum wait
        start_time = time.time()
        check_interval = 0.5   # Check every 500ms

        while time.time() - start_time < max_wait_time:
            try:
                with self._comm_lock:
                    moving = self.device.is_moving()
                if not moving:
                    break
            except Exception as e:
                self.logger.warn(
                    f'Error checking movement status, continuing: {e}')
                # If we can't check status, wait a bit and try again
                time.sleep(check_interval * 2)

            time.sleep(check_interval)
        else:
            # Timeout occurred
            raise MovementTimeoutError(
                f"Movement timeout after {max_wait_time}s",
                details={
                    'target_position': position,
                    'timeout': max_wait_time,
                    'elapsed_time': time.time() - start_time
                }
            )

        # Update position cache
        try:
            with self._comm_lock:
                current_pos = self.device.get_position() / self.device_units_per_mm
            self._last_position_cache = current_pos
            self._last_position_time = time.time()
        except Exception as e:
            self.logger.warn(f'Error updating position cache: {e}')

    def move_relative(self, distance: float):
        """Move relative distance from current position in millimeters."""
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        self.logger.debug(f'Moving relatively by: {distance} mm')

        try:
            with self._comm_lock:
                current_position = self.device.get_position()
                target_position = current_position + \
                    (distance * self.device_units_per_mm)

                # Start the movement
                self.device.move_to(target_position, scale=False)
        except Exception as e:
            raise HardwareError(
                f"Failed to start relative movement: {str(e)}",
                details={'distance': distance, 'error': str(e)}
            )

        # Wait for movement completion with robust error handling
        import time
        max_wait_time = 300.0  # 5 minutes maximum wait
        start_time = time.time()
        check_interval = 0.5   # Check every 500ms

        while time.time() - start_time < max_wait_time:
            try:
                with self._comm_lock:
                    moving = self.device.is_moving()
                if not moving:
                    break
            except Exception as e:
                self.logger.warn(
                    f'Error checking movement status, continuing: {e}')
                # If we can't check status, wait a bit and try again
                time.sleep(check_interval * 2)

            time.sleep(check_interval)
        else:
            # Timeout occurred
            raise MovementTimeoutError(
                f"Relative movement timeout after {max_wait_time}s",
                details={
                    'distance': distance,
                    'timeout': max_wait_time,
                    'elapsed_time': time.time() - start_time
                }
            )

        # Update position cache
        try:
            with self._comm_lock:
                current_pos = self.device.get_position() / self.device_units_per_mm
            self._last_position_cache = current_pos
            self._last_position_time = time.time()
        except Exception as e:
            self.logger.warn(f'Error updating position cache: {e}')

    def home(self, timeout: float = 180.0):
        """
        Home the device with configurable timeout.

        Args:
            timeout (float): Homing timeout in seconds (default: 180s)
        """
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        self.logger.info(f'Homing device with {timeout}s timeout...')

        with self._comm_lock:
            try:
                # Use configurable timeout for homing operations
                # LTS300 can take up to 2+ minutes for full-range homing
                self.device.home(force=True, timeout=timeout)
            except Exception as e:
                raise HomingFailedError(
                    f"Homing command failed: {str(e)}",
                    details={'timeout': timeout, 'error': str(e)}
                )

            # Wait for homing completion with robust error handling
            import time
            max_wait_time = timeout + 30.0  # Add 30s buffer to device timeout
            start_time = time.time()
            check_interval = 1.0   # Check every 1s for homing

            while time.time() - start_time < max_wait_time:
                try:
                    if not self.device.is_moving():
                        break
                except Exception as e:
                    self.logger.warn(
                        f'Error checking homing status, continuing: {e}')
                    # If we can't check status, wait a bit and try again
                    time.sleep(check_interval * 2)

                time.sleep(check_interval)
            else:
                # Timeout occurred
                raise HomingFailedError(
                    f"Homing timeout after {max_wait_time}s",
                    details={
                        'requested_timeout': timeout,
                        'max_wait_time': max_wait_time,
                        'elapsed_time': time.time() - start_time
                    }
                )

            # Update position cache
            try:
                current_pos = self.device.get_position() / self.device_units_per_mm
                self._last_position_cache = current_pos
                self._last_position_time = time.time()
                self.logger.info(
                    f'Homing complete. Position: {current_pos:.2f}mm')
            except Exception as e:
                self.logger.warn(
                    f'Error updating position cache after homing: {e}')

    def get_position(self) -> float:
        """Get current position in millimeters with caching."""
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        # Use cached position during operations to reduce hardware communication
        import time
        current_time = time.time()

        # Try to get lock without blocking for position queries
        if self._comm_lock.acquire(blocking=False):
            try:
                position = self.device.get_position() / self.device_units_per_mm
                self._last_position_cache = position
                self._last_position_time = current_time
                return position
            except Exception as e:
                self.logger.warn(f'Error getting position: {e}')
                # Return cached position if available
                if hasattr(self, '_last_position_cache'):
                    return self._last_position_cache
                return -1.0
            finally:
                self._comm_lock.release()
        else:
            # Communication busy, return cached position if recent enough (< 2 seconds)
            if (hasattr(self, '_last_position_cache') and
                hasattr(self, '_last_position_time') and
                    current_time - self._last_position_time < 2.0):
                self.logger.debug(
                    f'Using cached position: {self._last_position_cache:.2f}mm')
                return self._last_position_cache

            # No recent cache, wait briefly for lock
            if self._comm_lock.acquire(timeout=0.5):
                try:
                    position = self.device.get_position() / self.device_units_per_mm
                    self._last_position_cache = position
                    self._last_position_time = current_time
                    return position
                except Exception as e:
                    self.logger.warn(f'Error getting position: {e}')
                    return self._last_position_cache if hasattr(self, '_last_position_cache') else -1.0
                finally:
                    self._comm_lock.release()
            else:
                # Still can't get lock, return cached value or error
                return self._last_position_cache if hasattr(self, '_last_position_cache') else -1.0

    def is_moving(self) -> bool:
        """Check if axis is currently moving."""
        if not self.connected or not self.device:
            return False

        # Use timeout to avoid blocking indefinitely
        if self._comm_lock.acquire(timeout=0.3):
            try:
                moving_status = self.device.is_moving()
                return moving_status
            except Exception as e:
                # Handle Thorlabs communication errors gracefully
                self.logger.debug(f'Error checking movement status: {e}')
                # Return False as safe default when we can't check status
                return False
            finally:
                self._comm_lock.release()
        else:
            # Can't acquire lock, assume still moving if we were recently
            return True

    def get_serial_number(self) -> str:
        return self.serial_no if self.serial_no else ""

    def get_axis_type(self) -> str:
        return self.axis_type if self.axis_type else "unknown"

    def determine_axis(self, serial_number: str):
        if serial_number == self.x_axis_serial:
            return 'x'
        elif serial_number == self.z_axis_serial:
            return 'z'
        else:
            return 'unknown'

    def update_position(self):
        # This method is called internally by the driver after movements
        # The actual position is retrieved by get_position()
        pass

    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """
        Get current velocity parameters (min_velocity, acceleration, max_velocity).

        Returns:
            Tuple of (min_velocity, acceleration, max_velocity) in mm/s and mm/s^2
        """
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        try:
            # Get velocity parameters from device (returns in device units)
            with self._comm_lock:
                params = self.device.get_velocity_parameters(scale=False)

            # Convert from device units to mm/s and mm/s^2
            min_velocity = params.min_velocity / self.device_units_per_mm
            acceleration = params.acceleration / self.device_units_per_mm
            max_velocity = params.max_velocity / self.device_units_per_mm

            self.logger.debug(
                f'Current velocity parameters: min={min_velocity:.3f}mm/s, '
                f'accel={acceleration:.3f}mm/s², max={max_velocity:.3f}mm/s'
            )

            return (min_velocity, acceleration, max_velocity)

        except Exception as e:
            self.logger.error(
                f'Error getting velocity parameters: {e}')
            # Return default safe values in case of error
            return (0.0, 1.0, 5.0)

    def set_velocity_parameters(self, min_velocity=None, acceleration=None, max_velocity=None) -> Tuple[float, float, float]:
        """
        Set velocity parameters. If any parameter is None, use current value.

        Args:
            min_velocity: Minimum velocity in mm/s (None to keep current)
            acceleration: Acceleration in mm/s^2 (None to keep current)
            max_velocity: Maximum velocity in mm/s (None to keep current)

        Returns:
            Tuple of actual set parameters in mm/s and mm/s^2
        """
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        try:
            # Get current parameters if some are not specified
            current_params = self.get_velocity_parameters()

            # Use current values for unspecified parameters
            if min_velocity is None:
                min_velocity = current_params[0]
            if acceleration is None:
                acceleration = current_params[1]
            if max_velocity is None:
                max_velocity = current_params[2]

            self.logger.debug(
                f'Setting velocity parameters: min={min_velocity:.3f}mm/s, '
                f'accel={acceleration:.3f}mm/s², max={max_velocity:.3f}mm/s'
            )

            # Convert to device units
            min_vel_device = int(min_velocity * self.device_units_per_mm)
            accel_device = int(acceleration * self.device_units_per_mm)
            max_vel_device = int(max_velocity * self.device_units_per_mm)

            # Set the parameters (scale=False means we're providing device units)
            with self._comm_lock:
                self.device.setup_velocity(
                    min_velocity=min_vel_device,
                    acceleration=accel_device,
                    max_velocity=max_vel_device,
                    scale=False
                )

            self.logger.debug('Velocity parameters updated successfully')

            return self.get_velocity_parameters()

        except Exception as e:
            self.logger.error(
                f'Error setting velocity parameters: {e}')
            raise

    def stop(self):
        """
        Immediately stop any ongoing movement.
        This is an emergency stop function that halts all motion.
        """
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        # For emergency stop, try to acquire lock with timeout
        # If we can't get it quickly, force the stop anyway
        if self._comm_lock.acquire(timeout=0.1):
            try:
                self.logger.warn(
                    'Emergency stop requested - stopping all movement immediately')

                # Use pylablib's stop method for immediate halt
                self.device.stop()

                self.logger.info('Movement stopped successfully')

            except Exception as e:
                self.logger.error(
                    f'Error during emergency stop: {e}')
                raise
            finally:
                self._comm_lock.release()
        else:
            # Emergency case - force stop even if lock is busy
            try:
                self.logger.warn('EMERGENCY STOP - forcing stop without lock')
                self.device.stop()
            except Exception as e:
                self.logger.error(
                    f'Error during force stop: {e}')
                raise

    def jog_positive(self, step_size: float = 1.0):
        """
        Jog the axis in positive direction by the specified step size.

        Args:
            step_size (float): Distance to jog in mm (default: 1.0mm)
        """
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        try:
            self.logger.debug(f'Jogging positive by {step_size} mm')

            # Get current position and calculate target
            current_pos = self.get_position()
            target_pos = current_pos + step_size

            # Validate target position
            if not self.validate_position(target_pos):
                raise SoftLimitViolationError(
                    f"Jog target position would exceed safety limits",
                    details={
                        'current_position': current_pos,
                        'step_size': step_size,
                        'target_position': target_pos,
                        'limits': {'min': 0.0, 'max': ABSOLUTE_MAX_POSITION}
                    }
                )

            # Use relative move for jogging
            self.move_relative(step_size)

        except SoftLimitViolationError:
            raise
        except Exception as e:
            raise HardwareError(
                f"Error during positive jog: {str(e)}",
                details={'step_size': step_size, 'error': str(e)}
            )

    def jog_negative(self, step_size: float = 1.0):
        """
        Jog the axis in negative direction by the specified step size.

        Args:
            step_size (float): Distance to jog in mm (default: 1.0mm)
        """
        if not self.connected or not self.device:
            raise CommunicationError(
                "Device not connected",
                details={'connected': self.connected,
                         'device_initialized': self.device is not None}
            )

        try:
            self.logger.debug(f'Jogging negative by {step_size} mm')

            # Get current position and calculate target
            current_pos = self.get_position()
            target_pos = current_pos - step_size

            # Validate target position
            if not self.validate_position(target_pos):
                raise SoftLimitViolationError(
                    f"Jog target position would exceed safety limits",
                    details={
                        'current_position': current_pos,
                        'step_size': -step_size,
                        'target_position': target_pos,
                        'limits': {'min': 0.0, 'max': ABSOLUTE_MAX_POSITION}
                    }
                )

            # Use relative move for jogging (negative distance)
            self.move_relative(-step_size)

        except SoftLimitViolationError:
            raise
        except Exception as e:
            raise HardwareError(
                f"Error during negative jog: {str(e)}",
                details={'step_size': -step_size, 'error': str(e)}
            )

    def validate_position(self, position: float) -> bool:
        """
        Validate if position is within safe hardware limits.
        Uses conservative defaults to ensure safety.

        Args:
            position: Position to validate in mm

        Returns:
            True if position is valid, False otherwise
        """
        # Use conservative safety limits
        min_position = 0.0
        max_position = min(300.0, ABSOLUTE_MAX_POSITION)

        if position < min_position or position > max_position:
            self.logger.warn(
                f"Position {position}mm outside limits [{min_position}, {max_position}]mm")
            return False
        return True
