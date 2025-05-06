from pylablib.devices import Thorlabs
import sys
import time


try:
    from pylablib.devices import Thorlabs
except ImportError as e:
    print(f"Error importing Thorlabs: {e}")

# ROS 2 imports
from promoc_assembly_interfaces.srv import MoveAbsolute, MoveRelativ, Home, ShutdownLinearAxis, GetPosition, GetSetHomingParams, GetSetVelocityParams


# Import ROS 2-Komponenten
import rclpy  # type:ignore
from rclpy.node import Node  # type:ignore

#Todo Anpassen des launchfiles damit die axen unter linux starten und die restlichen funktiuonen implementieren


class LTS300ServiceNode(Node):
    def __init__(self):
        # Initialisieren Sie den ROS2-Node mit einem temporären Namen
        super().__init__('lts300_service_node_temp')

        # Initialisieren Sie die Kernparameter und die Geräteverbindung
        self.initialize_parameters()

        # Verbinden Sie sich mit dem physischen LTS300-Gerät
        self.connect()

        # Ändern Sie den Node-Namen nach der Verbindung
        if self.connected:
            self.get_logger().info(f'Changing node name to {self.node_name}')
            self.get_node_names_and_namespaces()  # This is required to update the node name
            rclpy.shutdown()
            rclpy.init()
            super().__init__(self.node_name)

        # Flag für Client-Verbindung
        self.client_connected = False

        # Richten Sie ROS2-Dienste ein
        self.setup_services()

        # Richten Sie Clients für andere Achsen ein
        self.setup_clients()

        # Protokollieren Sie den Initialisierungsstatus
        if self.connected:
            self.get_logger().info(f'{self.node_name} initialisiert')
        else:
            self.get_logger().error(f'Fehler bei der Initialisierung von {self.node_name}')
    
    
    def initialize_parameters(self):
        
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.serial_port = self.get_parameter('serial_port').value

        self.simulation_mode = False
        self.connected = False
        self.device = None

        # Initialisieren Sie diese Variablen erst nach der Verbindung
        self.serial_no = None
        self.axis_type = None
        self.node_name = None


    def connect(self):
        try:
            self.get_logger().info(f'Connecting to LTS300 on port {self.serial_port}...')
            
            self.device = Thorlabs.KinesisMotor(self.serial_port, scale="m")
            
            # Lesen Sie die Seriennummer aus
            self.serial_no = self.device.get_device_info()[0]
            self.get_logger().info(f'Detected serial number: {self.serial_no}')
            
            # Bestimmen Sie den Achsentyp
            self.axis_type = self.determine_axis(self.serial_no)
            
            # Setzen Sie den Node-Namen basierend auf dem Achsentyp
            self.node_name = f'lts300_{self.axis_type}_axis'
            
            self.get_logger().info(f'Connected to {self.axis_type.upper()}-axis (SN: {self.serial_no})')

            self.connected = True

            # Home the device
            self.device.home()
            self.position = 0

        except Exception as e:
            self.get_logger().error(f'Error connecting: {e}')
            self.connected = False

    def setup_services(self):
        """
        Set up ROS2 services for controlling the LTS300 linear stage.

        This function creates and registers all the service endpoints that allow
        external nodes to interact with the linear stage. Services include
        movement control (absolute and relative), homing operations, parameter
        configuration, position queries, and shutdown functionality.

        Parameters:
            None

        Returns:
            None: The function registers service handlers with the ROS2 node
                 but does not return any values.
        """
        # Create service for moving
        self.move_absolute_service = self.create_service(
            MoveAbsolute, f'{self.node_name}/move_absolute', self.move_absolute_callback)

        self.move_relative_service = self.create_service(
            MoveRelativ, f'{self.node_name}/move_relative', self.move_relative_callback)

        # Create service for homing the device
        self.home_service = self.create_service(
            Home, f'{self.node_name}/home', self.home_callback)

        self.get_set_homing_params_service = self.create_service(
            GetSetHomingParams, f'{self.node_name}/get_set_homing_params', self.get_set_homing_params_callback)

        self.shutdown_service = self.create_service(
            ShutdownLinearAxis, f'{self.node_name}/shutdown', self.shutdown_callback)

        self.get_position_service = self.create_service(
            GetPosition, f'{self.node_name}/get_position', self.get_position_callback)

    # Callback functions for ROS services
    def move_absolute_callback(self, request, response):
    
        try:
            target_position = request.axis_position
            self.get_logger().info(f'Moving to position: {target_position} mm')

            
            self.device.move_to(target_position*409600,scale=False)
            while self.device.is_moving():
                time.sleep(0.1)
            

            self.position = self.device.get_position()/409600
            response.success = True
            response.error_message = f"Successfully moved to position{self.position} mm"
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response

    def move_relative_callback(self, request, response):
        try:
            relative_position = request.axis_position * 409600
            current_position = self.device.get_position()
            target_position = current_position + relative_position
            
            self.get_logger().info(f'Moving relatively by: {relative_position/409600} mm')
            self.get_logger().info(f'Target position: {target_position/409600} mm')

            
            self.device.move_by(relative_position)
            while self.device.is_moving():
                time.sleep(0.1)
            

            self.position = self.device.get_position()/409600
            response.success = True
            response.error_message = f"Successfully moved to position {self.position/409600} mm"
        except Exception as e:
            self.get_logger().error(f'Error moving relatively: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response



    def home_callback(self, request, response):
        try:
            self.get_logger().info('Homing device...')
            self.is_moving = True
            self.device.home(force=True)  
            self.is_moving = False
    
            response.success = True
            response.error_message = "Homing completed successfully"
        
        except Exception as e:
            self.get_logger().error(f'Error during homing: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response

    def shutdown_callback(self, request, response):
        try:
            self.shutdown()
            response.success = True
            response.error_message = "Successfully shutdown device"
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"
        finally:
            return response

    def get_position_callback(self, request, response):
        try:
            response.position = self.device.get_position()/409600
            response.success = True
            response.error_message = "Successfully retrieved position"
            return response
        except Exception as e:
            response.position=None
            response.success = False
            self.get_logger().error(f'Error getting position: {e}')
            return response 
        

    def get_set_homing_params_callback(self, request, response):
        pass
    def get_set_velocity_params_callback(self, request, response):
        pass

    # Helper functions
    def shutdown(self):
        """
        Properly shutdown the device connection.

        This ensures the device is left in a good state and resources are released.
        """
        if self.connected and self.device:
            try:
                self.device.close()

                # Update connection state
                self.connected = False
                self.get_logger().info('Device disconnected')
            except Exception as e:
                self.get_logger().error(f'Error during shutdown: {e}')

    def setup_clients(self):
        pass

    def check_client_connection(self):
        pass
    def check_other_axis_position(self):
        pass

    def determine_axis(self, serial_number:str):
    # Definieren Sie hier Ihre Seriennummern für X und Z Achsen
        x_axis_serials = [45456044] # Seriennummer für X-Achse
        z_axis_serials = [45407924]  # Seriennummer für Z-Achse

        if serial_number in x_axis_serials:
            self.get_logger().info(f"Recognized X-axis with serial number: {serial_number}")
            return 'x'
        elif serial_number in z_axis_serials:
            self.get_logger().info(f"Recognized Z-axis with serial number: {serial_number}")
            return 'z'
        else:
            self.get_logger().warning(f"Unknown serial number: {serial_number}. Defaulting to 'unknown' axis.")
            return 'unknown'

def main(args=None):
    rclpy.init(args=args)
    node = LTS300ServiceNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Received keyboard interrupt, shutting down...')
    finally:
        node.get_logger().info('Preparing for shutdown...')
        if node.connected and node.device:
            try:
                node.get_logger().info('Homing device before shutdown...')
                node.is_moving = True
                node.device.Home(60000)  # 60 second timeout
                node.is_moving = False
                node.get_logger().info('Homing completed successfully')
            except Exception as e:
                node.get_logger().error(
                    f'Error during homing before shutdown: {e}')
            finally:
                try:
                    node.shutdown()
                except Exception as e:
                    node.get_logger().error(
                        f'Error during device shutdown: {e}')
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()





