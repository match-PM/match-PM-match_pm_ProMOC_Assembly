#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import time
import threading

# Import service interfaces
from promoc_assembly_interfaces.srv import (
    ActivateXbots, LevitationXbots, SixDofMotion, Home, MoveAbsolute
)
from promoc_assembly_interfaces.msg import LinearAxisInfo

class DemoController(Node):
    def __init__(self):
        super().__init__('demo_controller')
        self.get_logger().info('Demo Controller started!')

        # --- Parameter laden ---
        self.declare_parameter('axes', ['lts300_x_axis', 'lts300_z_axis'])
        self.known_axes_names = self.get_parameter('axes').get_parameter_value().string_array_value
        self.declare_parameter('xbot_id', 1)
        self.xbot_id = self.get_parameter('xbot_id').get_parameter_value().integer_value
        self.get_logger().info(f'Using XBot ID: {self.xbot_id}')

        # --- Member-Variablen ---
        self.axis_clients = {}
        self.axis_positions = {}
        self.cycle_delay = 5.0

        # --- Setup ---
        self.setup_ros_communication()
        self.wait_for_services()
        
        # Start demo sequence in a separate thread
        self.demo_thread = threading.Thread(target=self.run_endless_demo)
        self.demo_thread.daemon = True
        self.demo_thread.start()

    def setup_ros_communication(self):
        """Creates clients and subscribers for the mover and all available axes dynamically."""
        self.activate_client = self.create_client(ActivateXbots, '/mover_node/activate_xbots')
        self.levitation_client = self.create_client(LevitationXbots, '/mover_node/levitation_xbots')
        self.six_dof_motion_client = self.create_client(SixDofMotion, '/mover_node/six_d_mover_motion')
        
        self.get_logger().info('Searching for available linear axis services...')
        for axis_name in self.known_axes_names:
            move_client = self.create_client(MoveAbsolute, f'/{axis_name}/move_absolute')
            home_client = self.create_client(Home, f'/{axis_name}/home')

            if move_client.wait_for_service(timeout_sec=2.0) and home_client.wait_for_service(timeout_sec=2.0):
                self.get_logger().info(f"  Found and connected to '{axis_name}'!")
                self.axis_clients[axis_name] = {'move': move_client, 'home': home_client}
                self.create_subscription(
                    LinearAxisInfo,
                    f'/promoc_assembly/{axis_name}/position',
                    lambda msg, name=axis_name: self.axis_position_callback(msg, name),
                    10)
            else:
                self.get_logger().warn(f"  Could not connect to services for '{axis_name}'. It will be ignored.")

    def axis_position_callback(self, msg, axis_name):
        """Generic callback to store the position for any given axis."""
        self.axis_positions[axis_name] = msg.axis_position

    def run_endless_demo(self):
        """Starts the endless demo loop with proper error handling."""
        cycle_count = 0
        try:
            while rclpy.ok():
                cycle_count += 1
                self.get_logger().info(f'🔄 Starting demo cycle #{cycle_count}')
                self.run_single_demo_cycle()
                self.get_logger().info(f'Cycle finished. Waiting for {self.cycle_delay} seconds.')
                time.sleep(self.cycle_delay)
        except KeyboardInterrupt:
            self.get_logger().info('🛑 Demo stopped by user (Ctrl+C)')
        except Exception as e:
            self.get_logger().error(f'An error occurred in the demo loop: {e}', exc_info=True)

    def run_single_demo_cycle(self):
        """Executes one clean demo cycle."""
        self.get_logger().info('Step 1: Activating XBots...')
        self.call_activate_xbots(True)
        
        self.get_logger().info(f'Step 2: Starting systematic 6DOF demo for XBot {self.xbot_id}...')
        self.call_six_dof_motion(self.xbot_id, 60, 120, 4, 25, 0, 100)
        self.call_six_dof_motion(self.xbot_id, 80, 140, 4, 25, 25, 0)
        self.call_six_dof_motion(self.xbot_id, 100, 160, 4, 0, 25, -100)
        self.call_six_dof_motion(self.xbot_id, 120, 140, 4, -25, 25, -50)
        self.call_six_dof_motion(self.xbot_id, 140, 120, 4, -25, 0, 0)
        self.call_six_dof_motion(self.xbot_id, 160, 100, 4, -25, -25, 50)
        self.call_six_dof_motion(self.xbot_id, 180, 80, 4, 0, -25, 100)
        self.call_six_dof_motion(self.xbot_id, 200, 60, 4, 25, -25, 0)
        self.call_six_dof_motion(self.xbot_id, 220, 80, 4, 25, 0, -100)
        self.call_six_dof_motion(self.xbot_id, 240, 100, 3, 20, 0, -0)
        self.call_six_dof_motion(self.xbot_id, 260, 120, 3, 20, 20, 50)
        self.call_six_dof_motion(self.xbot_id, 280, 140, 3, 0, 20, 100)
        self.call_six_dof_motion(self.xbot_id, 300, 160, 3, -20, 20, 0)
        self.call_six_dof_motion(self.xbot_id, 320, 140, 3, -20, -20, -50)
        self.call_six_dof_motion(self.xbot_id, 340, 120, 2, 0, -15, -100)
        self.call_six_dof_motion(self.xbot_id, 360, 100, 2, 15, 0, 100)
        self.call_six_dof_motion(self.xbot_id, 380, 80, 2, 0, 0, 0)
        self.call_six_dof_motion(self.xbot_id, 400, 60, 2, 10, 10, -100)
        self.call_six_dof_motion(self.xbot_id, 420, 80, 2, -10, -10, 100)
        self.call_six_dof_motion(self.xbot_id, 240, 120, 2, 25, 0, -100)
        self.call_six_dof_motion(self.xbot_id, 60, 60, 2, 0, 0, 0)
        self.call_six_dof_motion(self.xbot_id, 420, 180, 1, 0, 0, 0)
        self.call_six_dof_motion(self.xbot_id, 420, 60, 3, 0, 0, 0)
        self.call_six_dof_motion(self.xbot_id, 60, 180, 4, 0, 0, 0)
        self.call_six_dof_motion(self.xbot_id, 110, 180, 4, 25, 0, 100)
        self.call_six_dof_motion(self.xbot_id, 110, 180, 4, 0, 25, 0)
        self.call_six_dof_motion(self.xbot_id, 110, 180, 4, -25, 0, -100)
        
        self.get_logger().info('↕️ Step 3: Moving linear axes...')
        self.call_lts300_motion('lts300_x_axis', 250.0)
        time.sleep(1.0)
        self.call_lts300_motion('lts300_z_axis', 200.0)
        time.sleep(5.0)
        self.call_lts300_motion('lts300_x_axis', 10.0)
        time.sleep(1.0)
        self.call_lts300_motion('lts300_z_axis', 10.0)
        time.sleep(5.0)
        
        self.get_logger().info('Demo cycle completed successfully!')

    def _call_service(self, client, request, success_msg, error_msg, timeout_sec=10.0):
        """Generic helper function to call a ROS service."""
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(f'Service "{client.srv_name}" not available. Skipping call.')
            return None
        try:
            future = client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
            result = future.result()
            if result and getattr(result, 'success', True): # Checks for '.success' if it exists
                self.get_logger().info(f'{success_msg}')
                return result
            else:
                status_msg = getattr(result, 'status_message', 'Service call failed')
                self.get_logger().error(f'{error_msg}: {status_msg}')
                return result
        except Exception as e:
            self.get_logger().error(f'Exception while calling service "{client.srv_name}": {e}', exc_info=True)
            return None

    # --- Refactored call_* functions using the helper ---
    def call_activate_xbots(self, activate):
        request = ActivateXbots.Request()
        request.activation_status = activate
        status = "activated" if activate else "deactivated"
        self._call_service(self.activate_client, request, f'XBots {status}!', 'Failed to change XBot activation status')

    def call_levitation(self, enable):
        request = LevitationXbots.Request()
        request.levitation = enable
        status = "enabled" if enable else "disabled"
        self._call_service(self.levitation_client, request, f'Levitation {status}', 'Failed to set levitation')

    def call_six_dof_motion(self, xbot_id, x_pos, y_pos, z_pos, rx, ry, rz):
        request = SixDofMotion.Request()
        # Compact assignment
        request.xbot_id, request.x_pos, request.y_pos, request.z_pos, request.rx_pos, request.ry_pos, request.rz_pos = \
            xbot_id, float(x_pos), float(y_pos), float(z_pos), float(rx), float(ry), float(rz)
        self._call_service(self.six_dof_motion_client, request, f'6DOF motion for XBot {xbot_id} completed', '6DOF motion failed')

    def call_lts300_motion(self, axis_name, position):
        if axis_name in self.axis_clients:
            request = MoveAbsolute.Request()
            request.axis_position = float(position)
            client = self.axis_clients[axis_name]['move']
            self._call_service(client, request, f"Moved '{axis_name}' to {position}mm", f"Failed to move '{axis_name}'", timeout_sec=15.0)
        else:
            self.get_logger().warn(f"SKIPPING movement for '{axis_name}' as it is not available.")

    def wait_for_services(self):
        """Waits for all mover services and tests the PMC connection."""
        services = [(self.activate_client, "activate_xbots"), (self.levitation_client, "levitation_xbots"), (self.six_dof_motion_client, "six_dof_motion")]
        for client, name in services:
            while not client.wait_for_service(timeout_sec=1.0):
                if not rclpy.ok(): return
                self.get_logger().info(f'Service {name} not available, waiting...')
            self.get_logger().info(f'Service {name} is ready!')
        
        self.get_logger().info('Testing PMC connection...')
        while not self.test_mover_connection():
            if not rclpy.ok(): return
            self.get_logger().info('PMC not ready, waiting 2 seconds...')
            time.sleep(2.0)
        self.get_logger().info('PMC connection confirmed!')

    def test_mover_connection(self):
        """Tests if the mover service is truly responsive using the helper function."""
        request = ActivateXbots.Request()
        request.activation_status = True
        result = self._call_service(self.activate_client, request, 'PMC connection test successful!', 'PMC not ready yet', timeout_sec=2.0)
        return result is not None

def main(args=None):
    rclpy.init(args=args)
    demo_controller = DemoController()
    try:
        rclpy.spin(demo_controller)
    except KeyboardInterrupt:
        demo_controller.get_logger().info('🛑 Demo Controller stopped by user')
    finally:
        # Graceful shutdown
        if rclpy.ok() and demo_controller.is_valid:
            demo_controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()