# Simulated linear axis driver for testing and development without hardware

import time
from typing import Optional, Tuple
from .linear_axis_driver import LinearAxisDriver
from promoc_core.promoc_exceptions import SoftLimitViolationError

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
        
        # Default velocity parameters for simulation
        self._min_velocity: float = 0.1    # mm/s
        self._acceleration: float = 10.0   # mm/s^2
        self._max_velocity: float = 50.0   # mm/s
        
        # Dummy jog parameters
        self._jog_step_size: float = 1.0
        self._jog_speed: float = 10.0

    def connect(self, port: str = None, x_axis_serial: str = None, z_axis_serial: str = None, debug_mode: bool = False) -> bool:
        """Connect to simulated device - compatible with real driver interface."""
        self.debug_mode = True  # Enable debug for simulation
        
        # Simulate serial numbers based on port or use defaults
        if port and "x" in port.lower():
            self._serial_number = "SIM_X_45456044"
            self._axis_type = 'x'
        elif port and "z" in port.lower():
            self._serial_number = "SIM_Z_45407924"
            self._axis_type = 'z'
        else:
            self._serial_number = "SIM_UNKNOWN"
            self._axis_type = 'unknown'

        if self.debug_mode:
            print(f"✅ Simulated driver connected. Axis Type: {self._axis_type}, Serial: {self._serial_number}")
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
                start_pos = self._position if hasattr(self, '_start_position') else 0.0
                self._position = start_pos + (self._target_position - start_pos) * progress
        
        return self._position

    def is_moving(self) -> bool:
        # Update position to check if movement is complete
        self.get_position()
        return self._is_moving

    def get_serial_number(self) -> str:
        return self._serial_number if self._serial_number else ""

    def get_axis_type(self) -> str:
        return self._axis_type if self._axis_type else "unknown"
    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """Get current velocity parameters (min_velocity, acceleration, max_velocity)"""
        return (self._min_velocity, self._acceleration, self._max_velocity)

    def set_velocity_parameters(self, min_velocity=None, acceleration=None, max_velocity=None):
        """Set velocity parameters. If any parameter is None, use current value."""
        if min_velocity is not None:
            self._min_velocity = max(0.0, min_velocity)
        if acceleration is not None:
            self._acceleration = max(0.1, acceleration)  # Minimum 0.1 mm/s^2
        if max_velocity is not None:
            self._max_velocity = max(0.1, max_velocity)  # Minimum 0.1 mm/s
            
        if self.debug_mode:
            print(f"🔧 Simulated velocity parameters updated:")
            print(f"   Min velocity: {self._min_velocity:.3f} mm/s")
            print(f"   Acceleration: {self._acceleration:.3f} mm/s²")
            print(f"   Max velocity: {self._max_velocity:.3f} mm/s")
            
        return self.get_velocity_parameters()

    def stop(self):
        """Immediately stop any ongoing movement."""
        if self.debug_mode:
            print('🛑 Simulated emergency stop - halting all movement')
        
        self._is_moving = False
        self._target_position = self._position  # Stay at current position
        
    def jog_positive(self, step_size: float = 1.0):
        """Jog the axis in positive direction by the specified step size."""
        if self.debug_mode:
            print(f'🔧 Simulated jog positive by {step_size} mm')
        
        # Validate position
        target_pos = self._position + step_size
        if target_pos > 300.0:  # Assume 300mm max limit
            raise SoftLimitViolationError(
                f"Jog target position {target_pos:.2f}mm would exceed safety limits",
                details={
                    'current_position': self._position,
                    'step_size': step_size,
                    'target_position': target_pos,
                    'limits': {'min': 0.0, 'max': 300.0}
                }
            )
        
        self.move_relative(step_size)
        
    def jog_negative(self, step_size: float = 1.0):
        """Jog the axis in negative direction by the specified step size."""
        if self.debug_mode:
            print(f'🔧 Simulated jog negative by {step_size} mm')
        
        # Validate position
        target_pos = self._position - step_size
        if target_pos < 0.0:  # Assume 0mm min limit
            raise SoftLimitViolationError(
                f"Jog target position {target_pos:.2f}mm would exceed safety limits",
                details={
                    'current_position': self._position,
                    'step_size': -step_size,
                    'target_position': target_pos,
                    'limits': {'min': 0.0, 'max': 300.0}
                }
            )
        
        self.move_relative(-step_size)

    # --- Dummy implementations for abstract methods ---

    def set_jog_parameters(self, step_size: float, speed: float = None) -> tuple:
        if self.debug_mode:
            print(f"[DUMMY] Setting jog parameters: step_size={step_size}, speed={speed}")
        self._jog_step_size = step_size
        if speed is not None:
            self._jog_speed = speed
        return (self._jog_step_size, self._jog_speed)

    def get_jog_parameters(self) -> tuple:
        if self.debug_mode:
            print(f"[DUMMY] Getting jog parameters: step_size={self._jog_step_size}, speed={self._jog_speed}")
        return (self._jog_step_size, self._jog_speed)

    def get_jog_step_size(self) -> float:
        if self.debug_mode:
            print(f"[DUMMY] Getting jog step size: {self._jog_step_size}")
        return self._jog_step_size

    def jog_step(self, direction: int):
        if self.debug_mode:
            print(f"[DUMMY] Jogging step with direction: {direction}")
        step = self._jog_step_size if direction > 0 else -self._jog_step_size
        self.move_relative(step)
