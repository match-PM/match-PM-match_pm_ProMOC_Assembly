#!/usr/bin/env python3
# filepath: /home/soc/Development/Ros2/promoc_assembly/src/match-PM-match_pm_ProMOC_Assembly/linear_axis_nodes/linear_axis_nodes/drivers/gazebo_linear_axis_driver.py

import time
import math
from typing import Optional
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from .linear_axis_driver import LinearAxisDriver


class GazeboLinearAxisDriver(LinearAxisDriver):
    """Enhanced simulation driver with Gazebo integration"""

    def __init__(self, node: Node = None):
        self._position: float = 0.0
        self._is_moving: bool = False
        self._target_position: float = 0.0
        self._serial_number: Optional[str] = None
        self._axis_type: Optional[str] = None
        self.debug_mode: bool = False

        # Gazebo integration
        self.node = node
        self.joint_name = ""  # Will be set during connect
        self.gazebo_position_sub = None
        self.gazebo_command_pub = None

        # Movement simulation
        self._move_start_time: float = 0.0
        self._move_duration: float = 0.0
        self._start_position: float = 0.0

    def connect(self, serial_port: str, x_axis_serial: str, z_axis_serial: str, debug_mode: bool):
        self.debug_mode = debug_mode

        # Determine axis type and joint name
        if x_axis_serial == "SIM_X":
            self._serial_number = x_axis_serial
            self._axis_type = 'x'
            self.joint_name = 'linear_x_joint'  # Match your URDF
        elif z_axis_serial == "SIM_Z":
            self._serial_number = z_axis_serial
            self._axis_type = 'z'
            self.joint_name = 'linear_z_joint'  # Match your URDF
        else:
            self._serial_number = "SIM_UNKNOWN"
            self._axis_type = 'unknown'
            self.joint_name = 'linear_unknown_joint'

        # Setup Gazebo communication if node is available
        if self.node:
            self._setup_gazebo_interface()

        if self.debug_mode:
            print(
                f"✅ Gazebo driver connected. Axis: {self._axis_type}, Joint: {self.joint_name}")

        return True

    def _setup_gazebo_interface(self):
        """Setup ROS2 topics for Gazebo communication"""
        try:
            # Subscribe to joint states from Gazebo
            self.gazebo_position_sub = self.node.create_subscription(
                JointState,
                '/joint_states',
                self._joint_state_callback,
                10
            )

            # Publisher for sending commands to Gazebo controller
            # This assumes you're using position_controllers/JointPositionController
            controller_topic = f'/{self.joint_name}_position_controller/command'
            self.gazebo_command_pub = self.node.create_publisher(
                Float64,
                controller_topic,
                10
            )

            if self.debug_mode:
                print(f"🔗 Gazebo interface setup for {self.joint_name}")
                print(f"   Subscribing to: /joint_states")
                print(f"   Publishing to: {controller_topic}")

        except Exception as e:
            if self.debug_mode:
                print(f"⚠️ Could not setup Gazebo interface: {e}")

    def _joint_state_callback(self, msg: JointState):
        """Update position from Gazebo joint states"""
        try:
            if self.joint_name in msg.name:
                idx = msg.name.index(self.joint_name)
                # Convert from meters to mm
                gazebo_position_mm = msg.position[idx] * 1000.0

                # Update position if not actively moving
                if not self._is_moving:
                    self._position = gazebo_position_mm

                if self.debug_mode and abs(self._position - gazebo_position_mm) > 0.1:
                    print(
                        f"🔧 Gazebo position update: {gazebo_position_mm:.2f}mm")

        except (ValueError, IndexError) as e:
            if self.debug_mode:
                print(f"⚠️ Error reading joint state: {e}")

    def move_absolute(self, position: float):
        """Move to absolute position with Gazebo integration"""
        if self.debug_mode:
            print(f"🎯 Moving to: {position}mm")

        self._target_position = position
        self._start_position = self._position
        self._move_start_time = time.time()

        # Calculate realistic movement duration (speed: ~50mm/s)
        distance = abs(position - self._position)
        self._move_duration = max(distance / 50.0, 0.1)  # Min 0.1s

        self._is_moving = True

        # Send command to Gazebo if available
        if self.gazebo_command_pub:
            cmd_msg = Float64()
            cmd_msg.data = position / 1000.0  # Convert mm to meters
            self.gazebo_command_pub.publish(cmd_msg)

    def move_relative(self, distance: float):
        """Move relative distance"""
        self.move_absolute(self._position + distance)

    def home(self):
        """Home to zero position"""
        if self.debug_mode:
            print("🏠 Homing to 0.0mm")
        self.move_absolute(0.0)

    def get_position(self) -> float:
        """Get current position with movement simulation"""
        if self._is_moving:
            elapsed_time = time.time() - self._move_start_time

            if elapsed_time >= self._move_duration:
                # Movement complete
                self._position = self._target_position
                self._is_moving = False
                if self.debug_mode:
                    print(f"✅ Movement complete: {self._position:.2f}mm")
            else:
                # Interpolate position during movement
                progress = elapsed_time / self._move_duration
                # Smooth S-curve interpolation
                smooth_progress = 3 * progress**2 - 2 * progress**3
                self._position = self._start_position + \
                    (self._target_position - self._start_position) * smooth_progress

        return self._position

    def is_moving(self) -> bool:
        """Check if axis is currently moving"""
        self.get_position()  # Update movement state
        return self._is_moving

    def get_serial_number(self) -> str:
        return self._serial_number if self._serial_number else ""

    def get_axis_type(self) -> str:
        return self._axis_type if self._axis_type else "unknown"

    def disconnect(self):
        """Clean disconnect"""
        if self.debug_mode:
            print(f"🔌 Gazebo driver disconnected: {self._axis_type}")
        self._is_moving = False
