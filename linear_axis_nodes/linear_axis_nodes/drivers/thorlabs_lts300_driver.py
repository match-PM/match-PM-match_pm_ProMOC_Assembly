import time
import warnings
from typing import Optional

# Try to import Thorlabs library
try:
    from pylablib.devices import Thorlabs
except ImportError as e:
    print(f"Error importing Thorlabs: {e}")
    Thorlabs = None # Set to None if import fails

from .linear_axis_driver import LinearAxisDriver

# Unterdrücke Pylablib Warnings beim Import
warnings.filterwarnings("ignore", message="can't recognize the stage name*")
warnings.filterwarnings("ignore", message="can't recognize motor model*")

class ThorlabsLTS300Driver(LinearAxisDriver):
    def __init__(self):
        self.device: Optional[Thorlabs.KinesisMotor] = None
        self.connected: bool = False
        self.serial_no: Optional[str] = None
        self.axis_type: Optional[str] = None
        self.device_units_per_mm: float = 409600.0 # Default value, can be overridden
        self.x_axis_serial: Optional[str] = None
        self.z_axis_serial: Optional[str] = None
        self.debug_mode: bool = False

    def connect(self, serial_port: str, x_axis_serial: str, z_axis_serial: str, debug_mode: bool):
        self.x_axis_serial = x_axis_serial
        self.z_axis_serial = z_axis_serial
        self.debug_mode = debug_mode
        try:
            if self.debug_mode:
                print(f'🔗 Connecting to LTS300 on port {serial_port}...')

            self.device = Thorlabs.KinesisMotor(serial_port)

            # Read the serial number
            self.serial_no = str(self.device.get_device_info()[0])
            if self.debug_mode:
                print(f'🔧 Detected serial number: {self.serial_no}')

            # Determine the axis type
            self.axis_type = self.determine_axis(self.serial_no)

            if self.debug_mode:
                print(f'🔧 Connected to {self.axis_type.upper()}-axis (SN: {self.serial_no})')

            self.connected = True

            # Home the device
            self.device.home()
            while self.device.is_moving():
                time.sleep(0.1)
            self.update_position()
            return True

        except Exception as e:
            print(f'Error connecting: {e}')
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
        target_position = current_position + (distance * self.device_units_per_mm)
        self.device.move_to(target_position, scale=False)
        while self.device.is_moving():
            time.sleep(0.1)
        self.update_position()

    def home(self):
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        if self.debug_mode:
            print('Homing device...')
        self.device.home(force=True, timeout=60)
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
            return -1.0 # Or raise an exception, depending on desired error handling

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
