# real Hardware drive neccesary for hardware connection

import time
import warnings
from typing import Optional, Tuple
import struct

# Try to import Thorlabs library
try:
    from pylablib.devices import Thorlabs
except ImportError as e:
    print(f"Error importing Thorlabs: {e}")
    Thorlabs = None  # Set to None if import fails

from .linear_axis_driver import LinearAxisDriver

# Unterdrücke Pylablib Warnings beim Import
warnings.filterwarnings("ignore", message="can't recognize the stage name*")
warnings.filterwarnings("ignore", message="can't recognize motor model*")

ABSOLUTE_MAX_POSITION = 300.0
THORLABS_STEPS_PER_MM = 409600.0  # LTS300 default


class ThorlabsLTS300Driver(LinearAxisDriver):
    def __init__(self):
        self.device: Optional[Thorlabs.KinesisMotor] = None  # type: ignore
        self.connected: bool = False
        self.serial_no: Optional[str] = None
        self.axis_type: Optional[str] = None
        # Default value, can be overridden
        self.device_units_per_mm: float = THORLABS_STEPS_PER_MM
        self.x_axis_serial: Optional[str] = None
        self.z_axis_serial: Optional[str] = None
        self.debug_mode: bool = False
        self.jog_step_size: float = 1.0  # Default jog step size in mm
        self.jog_speed: float = None  # Optional jog speed in mm/s

    def connect(self, port: str = None) -> bool:
        """Connect to the Thorlabs LTS300 device"""
        if Thorlabs is None:
            print("❌ Thorlabs library not available")
            return False

        try:
            if not port:
                print("❌ No port specified")
                return False

            print(f"🔗 Connecting to LTS300 on port {port}...")

            # Convert /dev/serial/by-id/... to /dev/ttyUSB* if needed
            actual_port = port
            if '/dev/serial/by-id/' in port:
                try:
                    import os
                    actual_port = os.readlink(port)
                    if not actual_port.startswith('/dev/'):
                        actual_port = '/dev/' + os.path.basename(actual_port)
                    print(f"🔄 Converted {port} to {actual_port}")
                except Exception as e:
                    print(f"⚠️ Could not resolve symlink: {e}")
                    # Fallback: try to find ttyUSB device
                    import glob
                    usb_devices = glob.glob('/dev/ttyUSB*')
                    if usb_devices:
                        actual_port = usb_devices[0]  # Take first available
                        print(f"🔄 Using fallback port: {actual_port}")

            # Now connect using the actual ttyUSB port
            self.device = Thorlabs.KinesisMotor(actual_port, scale="m")

            # Read the serial number from device
            device_info = self.device.get_device_info()
            self.serial_no = str(device_info[0])
            print(f"✅ Detected serial number: {self.serial_no}")

            self.connected = True
            print(
                f"✅ Connected to Thorlabs LTS300 (S/N: {self.serial_no}) on port {actual_port}")

            return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            self.connected = False
            return False

    def disconnect(self):
        if self.connected and self.device:
            try:
                self.device.close()
                self.connected = False
                if self.debug_mode:
                    print('✅ Device disconnected')
            except Exception as e:
                if self.debug_mode:
                    print(f'❌ Error during shutdown: {e}')

    def move_absolute(self, position: float):
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        if self.debug_mode:
            print(f'🔧 Moving to position: {position} mm')
        self.device.move_to(position * self.device_units_per_mm, scale=False)
        while self.device.is_moving():
            time.sleep(0.1)
        self.update_position()

    def move_relative(self, distance: float):
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        if self.debug_mode:
            print(f'🔧 Moving relatively by: {distance} mm')
        current_position = self.device.get_position()
        target_position = current_position + \
            (distance * self.device_units_per_mm)
        self.device.move_to(target_position, scale=False)
        while self.device.is_moving():
            time.sleep(0.1)
        self.update_position()

    def home(self, timeout: float = 180.0):
        """
        Home the device with configurable timeout.

        Args:
            timeout (float): Homing timeout in seconds (default: 180s)
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        if self.debug_mode:
            print(f'🔧 Homing device with {timeout}s timeout...')

        # Use configurable timeout for homing operations
        # LTS300 can take up to 2+ minutes for full-range homing
        self.device.home(force=True, timeout=timeout)
        while self.device.is_moving():
            time.sleep(0.1)
        self.update_position()

    def get_position(self) -> float:
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        try:
            return self.device.get_position() / self.device_units_per_mm
        except Exception as e:
            if self.debug_mode:
                print(f'⚠️ Error getting position: {e}')
            return -1.0  # Or raise an exception, depending on desired error handling

    def is_moving(self) -> bool:
        if not self.connected or not self.device:
            return False
        return self.device.is_moving()

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

    # New velocity control methods
    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """
        Get current velocity parameters (min_velocity, acceleration, max_velocity)
        Returns values in mm/s and mm/s^2
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")

        try:
            # Get velocity parameters from device (returns in device units)
            params = self.device.get_velocity_parameters(scale=False)

            # Convert from device units to mm/s and mm/s^2
            min_velocity = params.min_velocity / self.device_units_per_mm
            acceleration = params.acceleration / self.device_units_per_mm
            max_velocity = params.max_velocity / self.device_units_per_mm

            if self.debug_mode:
                print(f'🔧 Current velocity parameters:')
                print(f'   Min velocity: {min_velocity:.3f} mm/s')
                print(f'   Acceleration: {acceleration:.3f} mm/s²')
                print(f'   Max velocity: {max_velocity:.3f} mm/s')

            return (min_velocity, acceleration, max_velocity)

        except Exception as e:
            if self.debug_mode:
                print(f'❌ Error getting velocity parameters: {e}')
            # Return default safe values in case of error
            return (0.0, 1.0, 5.0)

    def set_velocity_parameters(self, min_velocity=None, acceleration=None, max_velocity=None) -> Tuple[float, float, float]:
        """
        Set velocity parameters. If any parameter is None, use current value.
        Parameters should be in mm/s and mm/s^2
        Returns the actual set parameters
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")

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

            if self.debug_mode:
                print(f'🔧 Setting velocity parameters:')
                print(f'   Min velocity: {min_velocity:.3f} mm/s')
                print(f'   Acceleration: {acceleration:.3f} mm/s²')
                print(f'   Max velocity: {max_velocity:.3f} mm/s')

            # Convert to device units
            min_vel_device = int(min_velocity * self.device_units_per_mm)
            accel_device = int(acceleration * self.device_units_per_mm)
            max_vel_device = int(max_velocity * self.device_units_per_mm)

            # Set the parameters (scale=False means we're providing device units)
            self.device.setup_velocity(
                min_velocity=min_vel_device,
                acceleration=accel_device,
                max_velocity=max_vel_device,
                scale=False
            )

            if self.debug_mode:
                print('✅ Velocity parameters updated successfully')

            return self.get_velocity_parameters()

        except Exception as e:
            if self.debug_mode:
                print(f'❌ Error setting velocity parameters: {e}')
            raise

    def validate_position(self, position: float) -> bool:
        # Config-basierte Limits
        config_max = getattr(self.config, 'max_position', 300.0)
        config_min = getattr(self.config, 'min_position', 0.0)

        # Hardware-basierte absolute Limits (nicht überschreibbar)
        hardware_max = min(config_max, ABSOLUTE_MAX_POSITION)
        hardware_min = max(config_min, 0.0)

        if position < hardware_min or position > hardware_max:
            print(
                f"❌ Position {position}mm outside limits [{hardware_min}, {hardware_max}]mm")
            return False
        return True

    def set_jog_parameters(self, step_size: float, speed: float = None):
        """Set jog step size and optional speed."""
        self.jog_step_size = step_size
        if speed is not None:
            self.jog_speed = speed
        return (self.jog_step_size, self.jog_speed)

    def get_jog_parameters(self):
        """Get current jog parameters."""
        return (self.jog_step_size, self.jog_speed)

    def get_jog_step_size(self):
        """Get current jog step size."""
        return self.jog_step_size

    def jog_step(self, direction: int):
        """Execute single jog step in given direction (±1)."""
        step = self.jog_step_size * direction
        self.move_relative(step)
