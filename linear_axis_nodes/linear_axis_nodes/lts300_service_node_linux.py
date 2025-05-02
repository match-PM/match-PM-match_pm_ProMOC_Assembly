from pylablib.devices import Thorlabs
import sys
print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")
print(f"sys.path: {sys.path}")

try:
    from pylablib.devices import Thorlabs
    print("Successfully imported Thorlabs from pylablib")
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
        """
        Initialize the LTS300ServiceNode with improved service handling.
        """
        # Initialisieren Sie den ROS2-Node mit dem konfigurierten Namen
        super().__init__('lts300_service_node')

        # Initialisieren Sie die Kernparameter und die Geräteverbindung
        self.initialize_parameters()

        # Flag für Client-Verbindung
        self.client_connected = False

        # Verbinden Sie sich mit dem physischen LTS300-Gerät
        self.connect()

        # Richten Sie ROS2-Dienste ein
        self.setup_services()

        # Richten Sie Clients für andere Achsen ein
        self.setup_clients()

        # Protokollieren Sie den Initialisierungsstatus
        if self.connected:
            self.get_logger().info(f'{self.node_name} initialisiert')
        else:
            self.get_logger().error(
                f'Fehler bei der Initialisierung von {self.node_name}')
    # Initialization functions

    def initialize_parameters(self):
        """
        Initialize the node parameters and state variables.

        This function declares and retrieves ROS parameters for the node,
        sets up the simulation mode based on the operating system,
        and initializes connection state variables.

        Parameters:
            None




        Returns:
            None
        """
        # default value as string
        self.declare_parameter('serial_number', '45407924')
        self.declare_parameter('node_name', 'lts300_z_axis')
        self.declare_parameter('number_of_axes', 1)
        # Declare the serial number parameter with a default value

        self.serial_no = self.get_parameter('serial_number').value
        self.node_name = self.get_parameter('node_name').value
        self.number_of_axes = int(self.get_parameter('number_of_axes').value)

        self.simulation_mode = False #platform.system() != "Windows"
        # Initialize connection state variables
        self.connected = False  # Flag to track connection status
        self.device = None      # Will hold the device object when connected

        # Additional state variables could be added here (position, status, etc.)

    def connect(self):
        try:
            self.get_logger().info(
                f'Connecting to LTS300 (SN: {self.serial_no})...')
            self.device = Thorlabs.KinesisMotor("/dev/ttyUSB1", scale="m")


            # Set the device connected flag to true
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
            target_position = request.axis_position*409600
            self.get_logger().info(f'Moving to position: {target_position} mm')

            self.is_moving = True
            self.device.move_to(target_position)
            self.is_moving = False

            self.position = target_position
            response.success = True
            response.error_message = "Successfully moved to position{target_position} mm"
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response

    def move_relative_callback(self, request, response):
        pass

    def home_callback(self, request, response):
        try:
            self.get_logger().info('Homing device...')
            self.is_moving = True
            self.device.home(force=True)  
            self.is_moving = False
            self.position = 0.0

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
       pass

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
                self.device.close(False)

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





