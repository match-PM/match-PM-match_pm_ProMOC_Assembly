#!/usr/bin/env python3
"""\
Unified Demo Controller for ProMOC Assembly

Supports three demo modes:
- planar_motor: XBot motion only
- linear_axes: Linear axes only
- full: Complete system demo (default)

Usage:
    ros2 run promoc_bringup unified_demo --ros-args -p demo_mode:=full

Parameters:
    demo_mode: 'full' | 'planar_motor' | 'linear_axes'
    xbot_id: XBot ID to control (default: 1)
    axes: List of linear axis names
    cycle_delay: Delay between cycles in seconds (default: 5.0)
"""

import rclpy
from rclpy.node import Node
import time
import threading
import math
from typing import Dict, List, Optional

# Service interfaces
from promoc_assembly_interfaces.srv import (
    ActivateXbots,
    LevitationXbots,
    SixDofMotion,
    Home,
    MoveAbsolute
)
from promoc_assembly_interfaces.msg import LinearAxisInfo

# Local helper
from .service_helper import ServiceHelper


class UnifiedDemoController(Node):
    """
    Unified demo controller for the ProMOC assembly system.

    This controller consolidates previous demo variations into a single,
    configurable node.
    """

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(self):
        super().__init__('unified_demo_controller')
        self.get_logger().info('Unified Demo Controller starting...')

        # Initialize helper
        self.helper = ServiceHelper(self)

        # Load parameters
        self._load_parameters()

        # Setup based on demo mode
        self._setup_clients()

        # Wait for services
        if not self._wait_for_required_services():
            self.get_logger().error('Required services not available. Exiting.')
            return

        # Start demo thread
        self.get_logger().info(f'Starting demo in {self.demo_mode} mode')
        self._start_demo_thread()

    def _load_parameters(self):
        """Load and validate ROS parameters."""
        self.declare_parameter('demo_mode', 'full')
        self.demo_mode = self.get_parameter('demo_mode').value

        valid_modes = ['full', 'planar_motor', 'linear_axes']
        if self.demo_mode not in valid_modes:
            self.get_logger().warn(
                f"Invalid demo_mode '{self.demo_mode}'. Using 'full'."
            )
            self.demo_mode = 'full'

        self.declare_parameter('xbot_id', 1)
        self.xbot_id = self.get_parameter('xbot_id').value

        self.declare_parameter('axes', ['lts300_x_axis', 'lts300_z_axis'])
        self.axes_names = self.get_parameter('axes').value

        self.declare_parameter('cycle_delay', 5.0)
        self.cycle_delay = self.get_parameter('cycle_delay').value

        self.get_logger().info('Configuration:')
        self.get_logger().info(f'   Demo mode: {self.demo_mode}')
        self.get_logger().info(f'   XBot ID: {self.xbot_id}')
        self.get_logger().info(f'   Axes: {self.axes_names}')
        self.get_logger().info(f'   Cycle delay: {self.cycle_delay}s')

    def _setup_clients(self):
        """Create service clients based on demo mode."""
        self.axis_clients: Dict[str, dict] = {}
        self.axis_positions: Dict[str, float] = {}

        if self.demo_mode in ['full', 'planar_motor']:
            self.activate_client = self.create_client(
                ActivateXbots, '/mover_node/activate_xbots'
            )
            self.levitation_client = self.create_client(
                LevitationXbots, '/mover_node/levitation_xbots'
            )
            self.six_dof_client = self.create_client(
                SixDofMotion, '/mover_node/six_d_mover_motion'
            )

        if self.demo_mode in ['full', 'linear_axes']:
            self._setup_axis_clients()

    def _setup_axis_clients(self):
        """Setup linear axis clients."""
        self.get_logger().info('Searching for linear axis services...')

        for axis_name in self.axes_names:
            move_client = self.create_client(
                MoveAbsolute, f'/{axis_name}/move_absolute'
            )
            home_client = self.create_client(
                Home, f'/{axis_name}/home'
            )

            # Try to connect with short timeout
            if (move_client.wait_for_service(timeout_sec=2.0) and
                    home_client.wait_for_service(timeout_sec=2.0)):

                self.get_logger().info(f"  Found '{axis_name}'")
                self.axis_clients[axis_name] = {
                    'move': move_client,
                    'home': home_client
                }

                self.create_subscription(
                    LinearAxisInfo,
                    f'/promoc_assembly/{axis_name}/position',
                    lambda msg, name=axis_name: self._axis_position_callback(
                        msg, name),
                    10
                )
            else:
                self.get_logger().warn(f"  '{axis_name}' not available")

    def _axis_position_callback(self, msg: LinearAxisInfo, axis_name: str):
        """Store axis position from subscriber."""
        self.axis_positions[axis_name] = msg.axis_position

    # =========================================================================
    # Service Waiting
    # =========================================================================

    def _wait_for_required_services(self) -> bool:
        """Wait for all required services based on demo mode."""
        services = []

        if self.demo_mode in ['full', 'planar_motor']:
            services.extend([
                (self.activate_client, 'activate_xbots'),
                (self.levitation_client, 'levitation_xbots'),
                (self.six_dof_client, 'six_dof_motion'),
            ])

        if not self.helper.wait_for_services(services):
            return False

        if self.demo_mode in ['full', 'planar_motor']:
            if not self._wait_for_pmc_connection():
                return False

        return True

    def _wait_for_pmc_connection(self, max_retries: int = 10) -> bool:
        """Test PMC connection with retries."""
        self.get_logger().info('⏳ Testing PMC connection...')

        for attempt in range(max_retries):
            if not rclpy.ok():
                return False

            request = ActivateXbots.Request()
            request.activation_status = True

            result = self.helper.call_service(
                self.activate_client, request,
                '✅ PMC connection OK',
                '⚠️ PMC not ready',
                timeout_sec=3.0
            )

            if self.helper.was_successful(result):
                return True

            self.get_logger().info(
                f'⏳ PMC not ready, retry {attempt + 1}/{max_retries}...'
            )
            time.sleep(2.0)

        return False

    # =========================================================================
    # Demo Execution
    # =========================================================================

    def _start_demo_thread(self):
        """Starts the demo loop in a background thread."""
        self.demo_thread = threading.Thread(target=self._run_demo_loop)
        self.demo_thread.daemon = True
        self.demo_thread.start()

    def _run_demo_loop(self):
        """Main demo loop, including error handling."""
        cycle_count = 0

        try:
            while rclpy.ok():
                cycle_count += 1
                self.get_logger().info(f'🔄 Demo cycle #{cycle_count}')

                self._run_demo_cycle()

                self.get_logger().info(
                    f'✅ Cycle complete. Waiting {self.cycle_delay}s...'
                )
                self._interruptible_sleep(self.cycle_delay)

        except KeyboardInterrupt:
            self.get_logger().info('🛑 Demo stopped by user')
        except Exception as e:
            self.get_logger().error(f'❌ Demo error: {e}')

    def _interruptible_sleep(self, seconds: float):
        """Sleep that can be cleanly interrupted on shutdown."""
        for _ in range(int(seconds)):
            if not rclpy.ok():
                return
            time.sleep(1.0)
        remaining = seconds - int(seconds)
        if remaining > 0 and rclpy.ok():
            time.sleep(remaining)

    def _run_demo_cycle(self):
        """Run one demo cycle based on mode."""
        if self.demo_mode == 'planar_motor':
            self._run_planar_motor_demo()
        elif self.demo_mode == 'linear_axes':
            self._run_linear_axes_demo()
        else:
            self._run_full_demo()

    # =========================================================================
    # Planar Motor Demo
    # =========================================================================

    def _run_planar_motor_demo(self):
        """Planar motor demo sequence."""
        self.get_logger().info('🤖 Planar Motor Demo')

        self._activate_xbots(True)
        time.sleep(1.0)

        self._set_levitation(True)
        time.sleep(1.0)

        self._move_6dof(120.0, 120.0, 2.5, 0, 0, 0)
        time.sleep(1.0)

        self._run_corner_pattern()

        self._move_6dof(120.0, 120.0, 2.5, 0, 0, 0)

    def _run_corner_pattern(self):
        """Run corner pattern with sinusoidal tilt."""
        corners = [
            (60, 60),
            (180, 60),
            (180, 180),
            (60, 180),
        ]

        max_tilt = 25.0
        max_z = 4.0
        min_z = 1.0
        steps_per_corner = 8

        for corner_idx, (x, y) in enumerate(corners):
            self.get_logger().info(f'📍 Corner {corner_idx + 1}: ({x}, {y})')

            for step in range(steps_per_corner):
                angle = (step / steps_per_corner) * 2 * math.pi

                z = min_z + (max_z - min_z) * (0.5 + 0.5 * math.sin(angle * 2))

                tilt_scale = z / max_z
                rx = max_tilt * tilt_scale * math.sin(angle)
                ry = max_tilt * tilt_scale * math.cos(angle)

                self._move_6dof(x, y, z, rx, ry, 0)
                time.sleep(0.2)

    # =========================================================================
    # Linear Axes Demo
    # =========================================================================

    def _run_linear_axes_demo(self):
        """Linear axes demo sequence."""
        self.get_logger().info('↕️ Linear Axes Demo')

        for axis_name in self.axis_clients:
            self.get_logger().info(f'  Moving {axis_name}...')
            self._move_axis(axis_name, 250.0)
            time.sleep(2.0)
            self._move_axis(axis_name, 10.0)
            time.sleep(2.0)

    # =========================================================================
    # Full System Demo
    # =========================================================================

    def _run_full_demo(self):
        """Full system demo (planar motor + linear axes)."""
        self.get_logger().info('🔧 Full System Demo')

        self._run_planar_motor_demo()
        time.sleep(2.0)

        if self.axis_clients:
            self._run_linear_axes_demo()

    # =========================================================================
    # Motion Commands
    # =========================================================================

    def _activate_xbots(self, activate: bool):
        """Activates or deactivates the XBots."""
        request = ActivateXbots.Request()
        request.activation_status = activate

        status = "activated" if activate else "deactivated"
        self.helper.call_service(
            self.activate_client, request,
            f'✅ XBots {status}',
            f'❌ Failed to {status[:-1]}e XBots'
        )

    def _set_levitation(self, enable: bool):
        """Enables or disables levitation."""
        request = LevitationXbots.Request()
        request.levitation = enable

        status = "enabled" if enable else "disabled"
        self.helper.call_service(
            self.levitation_client, request,
            f'✅ Levitation {status}',
            f'❌ Failed to set levitation'
        )

    def _move_6dof(
        self, x: float, y: float, z: float,
        rx: float, ry: float, rz: float
    ):
        """Executes a 6-DOF motion command."""
        request = SixDofMotion.Request()
        request.xbot_id = self.xbot_id
        request.x_pos = float(x)
        request.y_pos = float(y)
        request.z_pos = float(z)
        request.rx_pos = float(rx)
        request.ry_pos = float(ry)
        request.rz_pos = float(rz)

        self.helper.call_service(
            self.six_dof_client, request,
            f'📍 ({x:.0f}, {y:.0f}, {z:.1f})mm',
            '❌ 6DOF motion failed'
        )

    def _move_axis(self, axis_name: str, position: float):
        """Moves a linear axis to a target position."""
        if axis_name not in self.axis_clients:
            self.get_logger().warn(f"⚠️ Axis '{axis_name}' not available")
            return

        request = MoveAbsolute.Request()
        request.axis_position = float(position)

        self.helper.call_service(
            self.axis_clients[axis_name]['move'], request,
            f"✅ {axis_name} → {position}mm",
            f"❌ {axis_name} move failed",
            timeout_sec=30.0
        )


def main(args=None):
    """Entry point for the unified demo controller."""
    rclpy.init(args=args)

    controller = UnifiedDemoController()

    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        controller.get_logger().info('🛑 Shutting down...')
    finally:
        controller.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
