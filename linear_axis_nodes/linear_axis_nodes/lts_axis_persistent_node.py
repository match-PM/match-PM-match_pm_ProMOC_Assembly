import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from promoc_assembly_interfaces.srv import MoveAxis  # Angenommen, Sie haben diesen Service-Typ

# Importieren Sie hier Ihre LTS300-Bibliothek
# from your_lts300_module import LTS300Controller

class LTSAxisPersistentNode(Node):
    def __init__(self):
        super().__init__('lts_axis_persistent_node')
        self.get_logger().info("Starting Z-Axis Persistent Node")
        
        # Initialisieren Sie die Verbindung zum Gerät
        self.initialize_device()
        
        # Erstellen Sie die Services
        self.home_service = self.create_service(
            Trigger, 'z_axis/home', self.home_callback)
        self.move_service = self.create_service(
            MoveAxis, 'z_axis/move', self.move_callback)
        self.status_service = self.create_service(
            Trigger, 'z_axis/status', self.status_callback)
            
        self.get_logger().info("Z-Axis Persistent Node ready")
        
    def initialize_device(self):
        """Initialisiert die Verbindung zum Gerät und führt das Homing durch."""
        try:
            self.get_logger().info("Initializing device connection")
            # Hier Ihre Verbindungslogik einfügen
            # self.device = LTS300Controller("45318394")
            # self.device.connect()
            
            # Führen Sie das Homing durch
            self.get_logger().info("Performing initial homing")
            # self.device.home()
            self.get_logger().info("Homing completed")
            
            self.is_homed = True
            self.is_connected = True
        except Exception as e:
            self.get_logger().error(f"Failed to initialize device: {str(e)}")
            self.is_homed = False
            self.is_connected = False
    
    def home_callback(self, request, response):
        """Callback für den Home-Service."""
        try:
            if not self.is_connected:
                self.initialize_device()
                
            if not self.is_connected:
                response.success = False
                response.message = "Device not connected"
                return response
                
            self.get_logger().info("Homing Z-Axis")
            # self.device.home()
            self.is_homed = True
            response.success = True
            response.message = "Homing completed successfully"
        except Exception as e:
            self.get_logger().error(f"Homing failed: {str(e)}")
            response.success = False
            response.message = f"Homing failed: {str(e)}"
        return response
        
    def move_callback(self, request, response):
        """Callback für den Move-Service."""
        try:
            if not self.is_connected:
                response.success = False
                response.message = "Device not connected"
                return response
                
            if not self.is_homed:
                self.get_logger().warn("Device not homed, performing homing first")
                # self.device.home()
                self.is_homed = True
                
            self.get_logger().info(f"Moving Z-Axis to position {request.position}")
            # self.device.move_to_position(request.position)
            response.success = True
            response.message = f"Moved to position {request.position}"
        except Exception as e:
            self.get_logger().error(f"Move failed: {str(e)}")
            response.success = False
            response.message = f"Move failed: {str(e)}"
        return response
        
    def status_callback(self, request, response):
        """Callback für den Status-Service."""
        try:
            if not self.is_connected:
                response.success = False
                response.message = "Device not connected"
                return response
                
            # status = self.device.get_status()
            response.success = True
            response.message = f"Device status: Connected={self.is_connected}, Homed={self.is_homed}"
        except Exception as e:
            self.get_logger().error(f"Status check failed: {str(e)}")
            response.success = False
            response.message = f"Status check failed: {str(e)}"
        return response
        
    def destroy_node(self):
        """Cleanup beim Beenden des Nodes."""
        if hasattr(self, 'device') and self.is_connected:
            self.get_logger().info("Disconnecting from device")
            # self.device.disconnect()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = LTSAxisPersistentNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
