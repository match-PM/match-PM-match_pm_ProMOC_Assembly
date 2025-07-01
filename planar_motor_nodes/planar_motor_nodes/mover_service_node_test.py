import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import (
    ActivateXbots, ArcMotionTargetRadius, LevitationXbots,
    LinearMotionSi, RotaryMotion, SetVelocityAcceleration,
    SixDofMotion, StopMotion
)

# Import lokale Module
from .position_utils import PositionUtils
from .service_callbacks import ServiceCallbacks

# Smart PMCLib import
from .pmclib_loader import sys_cmd, bot, get_pmclib_status


class MoverServiceNode(Node):

    def __init__(self):
        super().__init__("mover_node")

        # Log PMCLib Status

        pmclib_status = get_pmclib_status()
        self.get_logger().info(f"🎯 PMCLib Source: {pmclib_status['source']}")

        # Initialize in logical order
        self._initialize_parameters()
        self._initialize_utils()
        self._setup_ros_interfaces()
        self._initialize_connection()
        self._start_timers()

        self.get_logger().info("✅ Mover Service Node initialized successfully!")

    def _initialize_parameters(self):
        """Initialize and load all ROS parameters."""
        # Declare parameters with defaults
        self.declare_parameter('debug_mode', True)  # Enable debug mode by default
        self.declare_parameter('xy_tolerance', 0.001)
        self.declare_parameter('six_d_tolerance', 0.001)

        # Movement boundaries - Based on XBot working area specifications
        self.declare_parameter('x_min', 0.055)  # 55mm minimum
        self.declare_parameter('x_max', 0.360)  # 360mm maximum
        self.declare_parameter('y_min', 0.055)  # 55mm minimum  
        self.declare_parameter('y_max', 0.180)  # 180mm maximum
        self.declare_parameter('z_min', 0.000)  # 0mm minimum
        self.declare_parameter('z_max', 0.004)  # 4mm maximum

        # Load parameter values
        self.debug_mode = self.get_parameter('debug_mode').value
        self.xy_tolerance = self.get_parameter('xy_tolerance').value
        self.six_d_tolerance = self.get_parameter('six_d_tolerance').value

        # Movement boundaries
        self.x_min = self.get_parameter('x_min').value
        self.x_max = self.get_parameter('x_max').value
        self.y_min = self.get_parameter('y_min').value
        self.y_max = self.get_parameter('y_max').value
        self.z_min = self.get_parameter('z_min').value
        self.z_max = self.get_parameter('z_max').value

        # Log the loaded boundaries
        self.get_logger().info(
            f"🔧 Movement boundaries loaded: "
            f"X=[{self.x_min:.3f}, {self.x_max:.3f}]m, "
            f"Y=[{self.y_min:.3f}, {self.y_max:.3f}]m, "
            f"Z=[{self.z_min:.3f}, {self.z_max:.3f}]m"
        )

        # Initialize velocity parameters
        self._initialize_velocity_parameters()

    def _initialize_velocity_parameters(self):
        """Initialize standard velocity and acceleration parameters."""
        self.velocity_acceleration_standard_params = {
            'xy_vel': 1.00,
            'z_vel': 0.10,
            'rx_vel': 0.10,
            'ry_vel': 0.10,
            'rz_vel': 0.10,
            'xy_max_accel': 5.00,
            'z_max_accel': 1.00
        }
        self.velocity_acceleration_params = {}

    def _initialize_utils(self):
        """Initialize utility classes."""
        self.pos_utils = PositionUtils(self)
        self.callbacks = ServiceCallbacks(self, self.pos_utils)

    def _setup_ros_interfaces(self):
        """Setup all ROS interfaces."""
        self._setup_publishers()
        self._setup_services()

    def _setup_publishers(self):
        """Create ROS publishers."""
        self.xbot_pos_publisher_ = self.create_publisher(
            XBotInfo, "xbot_info", 10)

    def _setup_services(self):
        """Create all ROS service servers."""
        services = [
            ('linear_mover_motion', LinearMotionSi,
             self.callbacks.callback_linear_motion_si),
            ('six_d_mover_motion', SixDofMotion,
             self.callbacks.callback_six_d_motion),
            ('activate_xbots', ActivateXbots,
             self.callbacks.callback_activate_xbot),
            ('levitation_xbots', LevitationXbots,
             self.callbacks.callback_levitation_xbot),
            ('arcmotion_target_radius', ArcMotionTargetRadius,
             self.callbacks.callback_arc_motion_target_radius),
            ('stop_motion', StopMotion, self.callbacks.callback_stop_motion),
            ('rotary_motion', RotaryMotion, self.callbacks.callback_rotary_motion),
            ('set_velocity_acceleration', SetVelocityAcceleration,
             self.callbacks.callback_set_velocity_acceleration)
        ]

        for service_name, service_type, callback in services:
            self.create_service(
                service_type, f"{self.get_name()}/{service_name}", callback)
            self.get_logger().info(f"✅ Service created: {service_name}")

    def _initialize_connection(self):
        """Initialize connection to PMC."""
        self.get_logger().info("🔗 Connecting to PMC...")
        success = False
        while not success:
            success = sys_cmd.connect_to_pmc("192.168.10.100")

        self.get_logger().info("✅ Connected")
        bot.activate_xbots()
        self.get_logger().info("✅ XBot Activated")

    def _start_timers(self):
        """Start periodic timers."""
        self.xbot_position_timer = self.create_timer(
            0.1, self._publish_xbot_position)
        
        # Add periodic XBot diagnosis for real PMCLib
        pmclib_status = get_pmclib_status()
        if not pmclib_status['is_mock']:
            self.xbot_diagnosis_timer = self.create_timer(
                5.0, self._diagnose_xbot_availability)

    def _diagnose_xbot_availability(self):
        """Periodic diagnosis of XBot availability (only for real PMCLib)."""
        try:
            diagnosis = self.pos_utils.diagnose_xbot_availability()
            
            # Log summary
            available_count = len([x for x in diagnosis['available_xbots'] if x['status'] == 'available'])
            total_from_api = diagnosis['total_from_get_all']
            
            self.get_logger().info(
                f"🔍 XBot diagnosis: {available_count} responding to status calls, "
                f"{total_from_api} in get_all_xbot_info"
            )
            
            # Log details only for available XBots
            for xbot_info in diagnosis['available_xbots']:
                if xbot_info['status'] == 'available':
                    self.get_logger().debug(
                        f"🔍 XBot {xbot_info['id']}: {xbot_info['state']}")
                    
        except Exception as e:
            self.get_logger().error(f"❌ XBot diagnosis failed: {e}")

    def _publish_xbot_position(self):
        """Publish current XBot position with state information."""
        msg = XBotInfo()
        try:
            # Get current position (most reliable) - default to XBot 0
            current_pos = self.pos_utils.get_current_position(0)
            if current_pos:
                msg.x_pos = current_pos[0]
                msg.y_pos = current_pos[1]
                msg.z_pos = current_pos[2]
                msg.rx_pos = current_pos[3]
                msg.ry_pos = current_pos[4]
                msg.rz_pos = current_pos[5]
            else:
                # Default values if position can't be read
                msg.x_pos = 0.0
                msg.y_pos = 0.0
                msg.z_pos = 0.0
                msg.rx_pos = 0.0
                msg.ry_pos = 0.0
                msg.rz_pos = 0.0

            # Get state (simple method)
            msg.xbot_state = self.pos_utils.get_xbot_state_string(0)

            self.xbot_pos_publisher_.publish(msg)

        except Exception as e:
            if self.debug_mode:
                self.get_logger().error(f"❌ Position publishing error: {e}")
            # Even if there's an error, publish a basic message
            msg.x_pos = 0.0
            msg.y_pos = 0.0
            msg.z_pos = 0.0
            msg.rx_pos = 0.0
            msg.ry_pos = 0.0
            msg.rz_pos = 0.0
            msg.xbot_state = "ERROR"
            self.xbot_pos_publisher_.publish(msg)

    # Helper methods
    def _get_speed_params(self, xbot_id: int) -> dict:
        """Get speed parameters for a specific XBot."""
        return self.velocity_acceleration_params.get(
            xbot_id, self.velocity_acceleration_standard_params)

    def _log_debug(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug_mode:
            self.get_logger().debug(f"🔧 {message}")

    def destroy_node(self):
        """Clean shutdown."""
        self.get_logger().info("🔄 Shutting down MoverServiceNode...")
        try:
            self.get_logger().info("Deactivating XBots...")
            bot.deactivate_xbots()
            self.get_logger().info("✅ XBots deactivated successfully")
        except Exception as e:
            self.get_logger().error(f"❌ Error deactivating XBots: {e}")
        finally:
            super().destroy_node()
            self.get_logger().info("✅ MoverServiceNode shutdown complete")


def main(args=None):
    rclpy.init(args=args)
    node = MoverServiceNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("🛑 Keyboard interrupt received")
    finally:
        node.destroy_node()
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except rclpy.exceptions.RCLError:
                pass


if __name__ == "__main__":
    main()
