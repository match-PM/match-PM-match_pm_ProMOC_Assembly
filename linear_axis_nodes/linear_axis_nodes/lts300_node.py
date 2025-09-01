import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import (
    MoveAbsolute, MoveRelativ, Home, ShutdownLinearAxis, GetPosition,
    SetVelocityParameters, GetVelocityParameters
)

from .node_config import Lts300Config
from .lts300_interface import Lts300Interface
# Umbenannt für Konsistenz
from .service_callbacks import ServiceCallbacks

class LTS300Node(Node):
    def __init__(self):
        super().__init__('lts300_node') # Name wird vom Launch-File überschrieben

        # 1. Konfiguration laden
        self.config = self._load_config()
        
        # 2. Kernkomponenten erstellen und verbinden
        self.interface = Lts300Interface(self.get_logger(), self.config)
        # Umbenannt für Konsistenz
        self.callbacks = ServiceCallbacks(self.get_logger(), self.interface, self.config)

        # 3. Verbindung herstellen
        if not self.interface.connect():
            self.get_logger().error("Shutting down node due to connection failure.")
            # self.destroy_node() # Führt zu Problemen beim schnellen Herunterfahren
            return
            
        # 4. ROS-Schnittstellen einrichten
        self.other_axis_position = None
        self._setup_ros_communication()
        
        self.get_logger().info(f"✅ {self.get_name()} with S/N {self.config.serial_number} is running.")

    def _load_config(self) -> Lts300Config:
        """Lädt alle ROS-Parameter in ein sauberes Konfigurationsobjekt."""
        self.declare_parameter('debug_mode', False)
        self.declare_parameter('use_sim_time', False)
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('serial_number', '00000000')
        self.declare_parameter('collision_threshold', 300.0)
        self.declare_parameter('namespace', 'promoc_assembly')
        
        return Lts300Config(
            debug_mode=self.get_parameter('debug_mode').value,
            use_sim_time=self.get_parameter('use_sim_time').value,
            serial_port=self.get_parameter('serial_port').value,
            serial_number=self.get_parameter('serial_number').value,
            collision_threshold=self.get_parameter('collision_threshold').value,
            namespace=self.get_parameter('namespace').value
        )

    def _setup_ros_communication(self):
        """Erstellt alle ROS-Publisher, -Subscriber und -Services."""
        node_name = self.get_name()
        
        # Publisher & Timer
        self.position_publisher = self.create_publisher(LinearAxisInfo, f"/{self.config.namespace}/{node_name}/position", 10)
        self.create_timer(0.1, self.publish_position)

        # Subscriber
        axis_type = self.interface.driver.get_axis_type()
        other_axis = 'z' if axis_type == 'x' else 'x'
        self.create_subscription(
            LinearAxisInfo,
            f"/{self.config.namespace}/lts300_{other_axis}_axis/position",
            self.other_axis_position_callback,
            10)
            
        # Services (jetzt mit lambdas und korrekten Callback-Namen)
        self.create_service(MoveAbsolute, f'{node_name}/move_absolute', 
            lambda req, res: self.callbacks.callback_move_absolute(req, res, self.other_axis_position))
        self.create_service(MoveRelativ, f'{node_name}/move_relative',
            lambda req, res: self.callbacks.callback_move_relative(req, res, self.other_axis_position))
        self.create_service(Home, f'{node_name}/home', self.callbacks.callback_home)
        self.create_service(GetPosition, f'{node_name}/get_position', self.callbacks.callback_get_position)
        self.create_service(SetVelocityParameters, f'{node_name}/set_velocity_parameters', self.callbacks.callback_set_velocity_parameters)
        self.create_service(GetVelocityParameters, f'{node_name}/get_velocity_parameters', self.callbacks.callback_get_velocity_parameters)
        self.create_service(ShutdownLinearAxis, f'{node_name}/shutdown', self.callbacks.callback_shutdown)

    def publish_position(self):
        """Veröffentlicht die aktuelle Position der Achse."""
        if not self.interface.is_connected:
            return # Nicht publishen, wenn keine Verbindung besteht
            
        msg = LinearAxisInfo()
        driver = self.interface.driver
        msg.axis_position = driver.get_position()
        msg.axis_type = driver.get_axis_type()
        msg.is_moving = driver.is_moving()
        msg.serial_number = driver.get_serial_number()
        self.position_publisher.publish(msg)

    def other_axis_position_callback(self, msg):
        """Speichert die Position der anderen Achse."""
        self.other_axis_position = msg.axis_position
        
    def shutdown_device(self):
        """Fährt das Gerät sauber herunter."""
        self.get_logger().info("Homing device before shutdown...")
        try:
            self.interface.driver.home()
        except Exception as e:
            self.get_logger().error(f"Error during homing on shutdown: {e}")
        finally:
            self.interface.disconnect()

def main(args=None):
    rclpy.init(args=args)
    node = LTS300Node()

    if node.is_valid:
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            node.get_logger().info("Keyboard interrupt, shutting down...")
        finally:
            node.get_logger().info('Final shutdown procedure...')
            node.shutdown_device()
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()

if __name__ == "__main__":
    main()