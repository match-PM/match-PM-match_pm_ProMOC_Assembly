import rclpy
import time
from rclpy.node import Node
from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import (
    ActivateXbots, ArcMotionTargetRadius, LevitationXbots,
    LinearMotionSi, RotaryMotion, SetVelocityAcceleration,
    SixDofMotion, StopMotion
)

# Importiere unsere neuen, sauberen Bausteine
from .pmc_interface import PmcInterface
from .position_utils import PositionUtils
from .service_callbacks import ServiceCallbacks
from .node_config import NodeConfig


class MoverServiceNode(Node):
    """
    The main ROS 2 node, acting as an orchestrator for the planar motor system.
    It initializes and connects all decoupled components.
    """

    def __init__(self):
        super().__init__("mover_node")

        # 1. Load configuration from ROS parameters into our dataclass
        self.config = self._load_config()
        
        self.is_connected = False

        # 2. Create the core components and inject dependencies
        self.pmc = PmcInterface(self.get_logger())
        self.pos_utils = PositionUtils(self.get_logger(), self.pmc, self.config)
        self.callbacks = ServiceCallbacks(self.get_logger(), self.pmc, self.pos_utils, self.config)
        self.xbot_pos_publisher = self.create_publisher(XBotInfo, "xbot_info", 10)
        
        # 3. Setup ROS interfaces using the components
        self._setup_services()
    
        self.get_logger().info(f"🔗 Connecting to PMC at 192.168.10.100...")
        self.connection_timer = self.create_timer(0.1, self._try_connect)

        self.get_logger().info("✅ Mover Service Node initialized. Waiting for PMC connection...")
        
    def _try_connect(self):
        """Wird vom Timer aufgerufen, um die Verbindung zu versuchen."""
        
        if self.pmc.connect("192.168.10.100"):
            self.get_logger().info("✅✅✅ PMC Connected! Activating system.")
            self.is_connected = True
            
            # Timer stoppen, wir brauchen ihn nicht mehr
            self.connection_timer.cancel()
            
            # Jetzt, wo wir verbunden sind, den Rest aktivieren
            self._activate_system()

    def _activate_system(self):
        """Aktiviert die XBots und startet die Publisher, nachdem die Verbindung steht."""
        try:
            self.pmc.bot.activate_xbots()
            self.get_logger().info("✅ XBot Activated")
            # Erst jetzt den Publisher-Timer starten
            self._start_publisher_timer()
        except Exception as e:
            self.get_logger().error(f"Failed to activate XBots after connection: {e}")
    
    
    
    
    def _load_config(self) -> NodeConfig:
        """Loads all ROS parameters and populates the NodeConfig dataclass."""
        self.declare_parameter('debug_mode', True)
        self.declare_parameter('xy_tolerance', 0.001)
        self.declare_parameter('six_d_tolerance', 0.001)
        self.declare_parameter('x_min', 0.055)
        self.declare_parameter('x_max', 0.420)
        self.declare_parameter('y_min', -0.055)
        self.declare_parameter('y_max', 0.180)
        self.declare_parameter('z_min', 0.000)
        self.declare_parameter('z_max', 0.004)
        
        config = NodeConfig(
            debug_mode=self.get_parameter('debug_mode').value,
            xy_tolerance=self.get_parameter('xy_tolerance').value,
            six_d_tolerance=self.get_parameter('six_d_tolerance').value,
            x_min=self.get_parameter('x_min').value,
            x_max=self.get_parameter('x_max').value,
            y_min=self.get_parameter('y_min').value,
            y_max=self.get_parameter('y_max').value,
            z_min=self.get_parameter('z_min').value,
            z_max=self.get_parameter('z_max').value
        )
        self.get_logger().info(f"🔧 Configuration loaded: {config}")
        return config

    def _setup_services(self):
        """Creates all ROS services using the methods from the ServiceCallbacks class."""
        services = [
            ('linear_mover_motion', LinearMotionSi, self.callbacks.callback_linear_motion_si),
            ('six_d_mover_motion', SixDofMotion, self.callbacks.callback_six_d_motion),
            ('activate_xbots', ActivateXbots, self.callbacks.callback_activate_xbot),
            ('levitation_xbots', LevitationXbots, self.callbacks.callback_levitation_xbot),
            ('arcmotion_target_radius', ArcMotionTargetRadius, self.callbacks.callback_arc_motion_target_radius),
            ('stop_motion', StopMotion, self.callbacks.callback_stop_motion),
            ('rotary_motion', RotaryMotion, self.callbacks.callback_rotary_motion),
            ('set_velocity_acceleration', SetVelocityAcceleration, self.callbacks.callback_set_velocity_acceleration)
        ]
        for name, srv_type, callback in services:
            self.create_service(srv_type, f"{self.get_name()}/{name}", callback)
        self.get_logger().info("✅ All services are created.")

    def _start_publisher_timer(self):
        """Startet die periodischen Timer NACHDEM die Verbindung steht."""
        self.xbot_position_timer = self.create_timer(0.1, self._publish_xbot_position)
        if not self.pmc.status['is_mock']:
            self.xbot_diagnosis_timer = self.create_timer(5.0, self.pos_utils.diagnose_xbot_availability)
        self.get_logger().info("✅ Timers started.")

    def _publish_xbot_position(self):
        """Publiziert die aktuelle XBot-Position, aber nur wenn verbunden."""
        if not self.is_connected:
            return

        msg = XBotInfo()
        try:
            current_pos = self.pos_utils.get_current_position(0)
            if current_pos:
                msg.x_pos, msg.y_pos, msg.z_pos, msg.rx_pos, msg.ry_pos, msg.rz_pos = current_pos
            
            msg.xbot_state = self.pos_utils.get_xbot_state_string(0)
            self.xbot_pos_publisher.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Position publishing error: {e}")

    def destroy_node(self):
        """Sauberes Herunterfahren."""
        self.get_logger().info("Shutting down MoverServiceNode...")
        if self.is_connected:
            try:
                self.pmc.bot.deactivate_xbots()
                self.get_logger().info("XBots deactivated.")
            except Exception as e:
                self.get_logger().error(f"Error during deactivation: {e}")
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = MoverServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()