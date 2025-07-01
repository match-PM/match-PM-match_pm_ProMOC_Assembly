import time
from typing import Optional
from .linear_axis_driver import LinearAxisDriver

class SimulatedLinearAxisDriver(LinearAxisDriver):
    def __init__(self):
        self._position: float = 0.0
        self._is_moving: bool = False
        self._target_position: float = 0.0
        self._move_start_time: float = 0.0
        self._move_duration: float = 0.0
        self._serial_number: Optional[str] = None
        self._axis_type: Optional[str] = None
        self.debug_mode: bool = False

    def connect(self, serial_port: str, x_axis_serial: str, z_axis_serial: str, debug_mode: bool):
        self.debug_mode = debug_mode
        # In a simulated environment, we can just assign a serial number and axis type
        # based on the provided x_axis_serial or z_axis_serial for demonstration.
        # For a real simulation, you might want to make this more sophisticated.
        if x_axis_serial == "SIM_X": # Example for a simulated X-axis
            self._serial_number = x_axis_serial
            self._axis_type = 'x'
        elif z_axis_serial == "SIM_Z": # Example for a simulated Z-axis
            self._serial_number = z_axis_serial
            self._axis_type = 'z'
        else:
            self._serial_number = "SIM_UNKNOWN"
            self._axis_type = 'unknown'

        if self.debug_mode:
            print(f"Simulated driver connected. Axis Type: {self._axis_type}, Serial: {self._serial_number}")
        return True

    def disconnect(self):
        if self.debug_mode:
            print("Simulated driver disconnected.")
        self._is_moving = False

    def move_absolute(self, position: float):
        if self.debug_mode:
            print(f"Simulating absolute move to: {position} mm")
        self._target_position = position
        self._move_start_time = time.time()
        # Simulate a fixed duration for movement, e.g., 1 second per 100mm
        self._move_duration = abs(position - self._position) / 100.0 + 0.5 # Min 0.5s
        self._is_moving = True

    def move_relative(self, distance: float):
        if self.debug_mode:
            print(f"Simulating relative move by: {distance} mm")
        self.move_absolute(self._position + distance)

    def home(self):
        if self.debug_mode:
            print("Simulating homing.")
        self.move_absolute(0.0) # Home to 0.0

    def get_position(self) -> float:
        if self._is_moving:
            elapsed_time = time.time() - self._move_start_time
            if elapsed_time >= self._move_duration:
                self._position = self._target_position
                self._is_moving = False
            else:
                # Linear interpolation for position during movement
                progress = elapsed_time / self._move_duration
                self._position = self._position + (self._target_position - self._position) * progress
        return self._position

    def is_moving(self) -> bool:
        # Update position to check if movement is complete
        self.get_position()
        return self._is_moving

    def get_serial_number(self) -> str:
        return self._serial_number if self._serial_number else ""

    def get_axis_type(self) -> str:
        return self._axis_type if self._axis_type else "unknown"
