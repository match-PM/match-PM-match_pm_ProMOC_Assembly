import time
from typing import Optional, Tuple
from .linear_axis_driver import LinearAxisDriver
try:
    import rclpy
    from rclpy.node import Node
    from gazebo_msgs.srv import SetEntityState, GetEntityState
    from gazebo_msgs.msg import EntityState
    from geometry_msgs.msg import Pose, Point, Quaternion, Twist, Vector3
except ImportError:
    print("ROS2 or Gazebo messages not available for Gazebo driver")

class GazeboLinearAxisDriver(LinearAxisDriver):
    def __init__(self, node: Node = None):
        self.node = node
        self._position: float = 0.0
        self._is_moving: bool = False
        self._target_position: float = 0.0
        self._move_start_time: float = 0.0
        self._move_duration: float = 0.0
        self._serial_number: Optional[str] = None
        self._axis_type: Optional[str] = None
        self.debug_mode: bool = False
        self.connected: bool = False
        
        # Velocity parameters (in mm/s and mm/s^2)
        self._min_velocity: float = 0.0
        self._acceleration: float = 10.0  # Default 10 mm/s^2
        self._max_velocity: float = 5.0   # Default 5 mm/s

    def connect(self, serial_port: str, x_axis_serial: str, z_axis_serial: str, debug_mode: bool):
        self.debug_mode = debug_mode
        if x_axis_serial == "GAZEBO_X":
            self._serial_number = x_axis_serial
            self._axis_type = 'x'
        elif z_axis_serial == "GAZEBO_Z":
            self._serial_number = z_axis_serial
            self._axis_type = 'z'
        else:
            self._serial_number = "GAZEBO_UNKNOWN"
            self._axis_type = 'unknown'

        if self.debug_mode:
            print(f"🔧 Gazebo driver connected. Axis Type: {self._axis_type}, Serial: {self._serial_number}")
        
        self.connected = True
        return True

    def disconnect(self):
        if self.debug_mode:
            print("🔧 Gazebo driver disconnected.")
        self._is_moving = False
        self.connected = False

    def move_absolute(self, position: float):
        if self.debug_mode:
            print(f"🔧 Gazebo move to: {position} mm")
        self._target_position = position
        self._move_start_time = time.time()
        
        # Calculate duration based on current velocity settings
        distance = abs(position - self._position)
        time_to_max_vel = self._max_velocity / self._acceleration
        accel_distance = 0.5 * self._acceleration * time_to_max_vel**2
        
        if distance <= 2 * accel_distance:
            self._move_duration = 2 * (distance / self._acceleration)**0.5
        else:
            const_vel_distance = distance - 2 * accel_distance
            const_vel_time = const_vel_distance / self._max_velocity
            self._move_duration = 2 * time_to_max_vel + const_vel_time
        
        self._move_duration = max(self._move_duration, 0.1)
        self._is_moving = True

    def move_relative(self, distance: float):
        if self.debug_mode:
            print(f"🔧 Gazebo relative move: {distance} mm")
        self.move_absolute(self._position + distance)

    def home(self):
        if self.debug_mode:
            print("🔧 Gazebo homing.")
        self.move_absolute(0.0)

    def get_position(self) -> float:
        if self._is_moving:
            elapsed_time = time.time() - self._move_start_time
            if elapsed_time >= self._move_duration:
                self._position = self._target_position
                self._is_moving = False
            else:
                start_pos = getattr(self, '_start_position', self._position)
                if not hasattr(self, '_start_position'):
                    self._start_position = self._position
                progress = elapsed_time / self._move_duration
                self._position = start_pos + (self._target_position - start_pos) * progress
        return self._position

    def is_moving(self) -> bool:
        self.get_position()
        return self._is_moving

    def get_serial_number(self) -> str:
        return self._serial_number if self._serial_number else ""

    def get_axis_type(self) -> str:
        return self._axis_type if self._axis_type else "unknown"

    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """Get current velocity parameters (min_velocity, acceleration, max_velocity)"""
        return (self._min_velocity, self._acceleration, self._max_velocity)

    def set_velocity_parameters(self, min_velocity=None, acceleration=None, max_velocity=None) -> Tuple[float, float, float]:
        """Set velocity parameters. If any parameter is None, use current value."""
        if min_velocity is not None:
            self._min_velocity = max(0.0, min_velocity)
        if acceleration is not None:
            self._acceleration = max(0.1, acceleration)
        if max_velocity is not None:
            self._max_velocity = max(0.1, max_velocity)
            
        if self.debug_mode:
            print(f"🔧 Gazebo velocity parameters updated:")
            print(f"   Min velocity: {self._min_velocity:.3f} mm/s")
            print(f"   Acceleration: {self._acceleration:.3f} mm/s²")
            print(f"   Max velocity: {self._max_velocity:.3f} mm/s")
            
        return self.get_velocity_parameters()