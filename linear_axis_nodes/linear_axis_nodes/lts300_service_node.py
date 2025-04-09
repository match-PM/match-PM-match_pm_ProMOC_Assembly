# ROS 2 imports
from promoc_assembly_interfaces.srv import MoveAbsolute, MoveRelativ, Home, ShutdownLinearAxis, GetPosition, GetSetHomingParams, GetSetVelocityParams
import sys
import os
import rclpy  # type:ignore
from rclpy.node import Node  # type:ignore


# Import the platform check and Thorlabs libraries from lts300.py
import platform
import time
# Ensure the current script's directory is in the Python path to allow local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Check if running on Windows, as Thorlabs libraries only work on Windows
if platform.system() == "Windows":
    import clr  # type:ignore
    # Load Thorlabs .NET assemblies using Python.NET (clr)
    # These DLLs provide the interface to control Thorlabs motion devices
    clr.AddReference(
        "C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
    clr.AddReference(
        "C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
    clr.AddReference(
        "C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")

    # Import specific classes from the Thorlabs .NET libraries
    # For device discovery and connection
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI  # type:ignore
    # For specifying motor direction
    from Thorlabs.MotionControl.GenericMotorCLI import MotorDirection  # type:ignore
    # For controlling the LTS300 stage
    from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import LongTravelStage  # type:ignore
    # .NET Decimal type for precise position values
    from System import Decimal  # type:ignore
else:
    print("This script is intended to run on Windows only.")
    try:
        from mock_thorlabs import MockDeviceManagerCLI as DeviceManagerCLI, MockMotorDirection as MotorDirection, MockLongTravelStage as LongTravelStage, MockDecimal as Decimal
    except ImportError:
        print("Failed to import mock_thorlabs. Make sure the file exists in the correct location.")
        exit()


# Import custom service and message types


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
        self.declare_parameter('serial_number', '45318394')
        self.declare_parameter('node_name', 'lts300_z_axis')
        # Declare the serial number parameter with a default value

        self.serial_no = self.get_parameter('serial_number').value
        self.node_name = self.get_parameter('node_name').value

        self.simulation_mode = platform.system() != "Windows"
        # Initialize connection state variables
        self.connected = False  # Flag to track connection status
        self.device = None      # Will hold the device object when connected
        # Additional state variables could be added here (position, status, etc.)

    def connect(self):
        try:
            self.get_logger().info(
                f'Connecting to LTS300 (SN: {self.serial_no})...')

            DeviceManagerCLI.BuildDeviceList()
            if self.simulation_mode:
                self.get_logger().info('Running in simulation mode. Simulating successful connection.')
                self.device = LongTravelStage.CreateLongTravelStage(
                    self.serial_no)
                self.connected = True
                self.position = 0
                return

            if not DeviceManagerCLI.IsDeviceConnected(self.serial_no):
                available_devices = DeviceManagerCLI.GetDeviceList()
                self.get_logger().error(
                    f'Device with serial number {self.serial_no} not found!')
                self.get_logger().info('Available devices:')
                for device in available_devices:
                    self.get_logger().info(f' - {device}')
                return

            self.device = LongTravelStage.CreateLongTravelStage(self.serial_no)

            # Connect to the device
            self.device.Connect(self.serial_no)

            # Wait for the device settings to initialize
            if not self.device.IsSettingsInitialized():
                self.device.WaitForSettingsInitialized(
                    10000)  # 10 second timeout

            if not self.device.IsSettingsInitialized():
                raise Exception("Failed to initialize device settings")

            # Load the device configuration
            self.device.LoadMotorConfiguration(self.serial_no)

            # Start polling and enable the device
            self.device.StartPolling(250)
            time.sleep(0.5)  # Increased delay to allow polling to start
            self.device.EnableDevice()
            time.sleep(0.5)  # Wait for device to enable

            # Get and log the device info
            device_info = self.device.GetDeviceInfo()
            self.get_logger().info(f'Connected to {device_info.Name}')

            # Set the device connected flag to true
            self.connected = True

            # Home the device
            self.device.Home(60000)
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
        """
        Callback function for the move_absolute service.

        Moves the linear stage to an absolute position specified in the request.
        Before moving, it checks if the device is connected and if other axes are
        in a safe position. The function handles device initialization, movement
        execution, and error reporting.

        Parameters:
            request (MoveAbsolute.Request): The service request containing:
                - axis_position (float): The target absolute position in mm
            response (MoveAbsolute.Response): The service response object to be populated with:
                - success (bool): Whether the movement was successful
                - error_message (str): Description of the result or error

        Returns:
            MoveAbsolute.Response: The populated response object indicating success or failure
                                  and providing an error message if applicable
        """
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
            return response
        if not self.check_other_axis_position():
            response.success = False
            response.error_message = f"Moving not possible\n{self.other_axis_name} is not Homed"
            return response

        try:
            target_position = request.axis_position
            self.get_logger().info(f'Moving to position: {target_position} mm')

            # Ensure the device is enabled and settings are initialized
            if not self.device.IsSettingsInitialized():
                self.device.WaitForSettingsInitialized(5000)
            if not self.device.IsSettingsInitialized():
                raise Exception("Device settings not initialized")

            # Check if the device is enabled (assuming IsEnabled is a property, not a method)
            if not self.device.IsEnabled:
                self.device.EnableDevice()
                time.sleep(0.5)  # Wait for device to enable

            decimal_position = Decimal(target_position)

            self.is_moving = True
            self.device.MoveTo(decimal_position, 60000)
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
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
            return response
        if not self.check_other_axis_position():
            response.success = False
            response.error_message = f"Moving not possible\n{self.other_axis_name} is not Homed"
            return response
        try:
            relative_position = request.axis_position
            target_position = self.position + relative_position
            self.get_logger().info(f'Moving to position: {target_position} mm')

            # Ensure the device is enabled and settings are initialized
            if not self.device.IsSettingsInitialized():
                self.device.WaitForSettingsInitialized(5000)
            if not self.device.IsSettingsInitialized():
                raise Exception("Device settings not initialized")

            # Check if the device is enabled (assuming IsEnabled is a property, not a method)
            if not self.device.IsEnabled:
                self.device.EnableDevice()
                time.sleep(0.5)  # Wait for device to enable

            decimal_position = Decimal(target_position)

            self.is_moving = True
            self.device.MoveTo(decimal_position, 60000)
            self.is_moving = False

            self.position = target_position
            response.success = True
            response.error_message = "Successfully moved to position{target_position} mm"
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"
        finally:
            return response

    def home_callback(self, request, response):
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
            return response

        try:
            self.get_logger().info('Homing device...')

            if self.simulation_mode:
                self.position = 0.0
                self.get_logger().info('Simulation: Device homed')
            else:
                self.is_moving = True
                self.device.Home(60000)  # 60 second timeout
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
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
            return response
        self.get_logger().info('Shutting down LTS300 node...')
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
        if not self.connected:
            response.axis_position = 0.0
            response.success = False
            response.error_message = "Device not connected"
            return response

        try:
            # Get the current position from the device
            response.axis_position = self.position
            device_info = self.device.TargetPosition()
            self.get_logger().info(type(device_info))
            response.error_message = "Successfully retrieved position"
            response.success = True
            self.get_logger().info(
                f'Current position: {response.axis_position} mm')
        except Exception as e:
            self.get_logger().error(f'Error getting position: {e}')
            response.success = False
            response.axis_position = 0.0
            response.error_message = f"Error: {str(e)}"

        return response

    def get_set_homing_params_callback(self, request, response):
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
            return response

        try:
            # Get current homing parameters
            home_params = self.device.GetHomingParams()

            # If a new velocity is provided, set it
            if request.new_velocity > 0:
                home_params.Velocity = Decimal(request.new_velocity)
                self.device.SetHomingParams(home_params)

            # Get the (possibly updated) homing parameters
            home_params = self.device.GetHomingParams()

            # Fill the response
            response.velocity = float(home_params.Velocity)
            response.direction = int(home_params.Direction)
            response.success = True
            response.error_message = "Set Homing Parameters Successfully"

        except Exception as e:
            self.get_logger().error(
                f'Error getting/setting homing parameters: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response

    def get_set_velocity_params_callback(self, request, response):
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
            return response

        try:
            if self.simulation_mode:
                response.max_velocity = 5.0  # Default simulated max velocity
                response.acceleration = 1.0  # Default simulated acceleration
            else:
                # Get current velocity parameters
                vel_params = self.device.GetVelocityParams()

                # Check if new parameters are provided and set them
                if request.new_max_velocity > 0 or request.new_acceleration > 0:
                    if request.new_max_velocity > 0 and request.new_max_velocity < 10:
                        vel_params.MaxVelocity = Decimal(
                            request.new_max_velocity)
                    if request.new_acceleration > 0 and request.new_acceleration < 3:
                        vel_params.Acceleration = Decimal(
                            request.new_acceleration)
                    self.device.SetVelocityParams(vel_params)

                # Get the (possibly updated) velocity parameters
                vel_params = self.device.GetVelocityParams()

                # Fill the response
                response.max_velocity = float(vel_params.MaxVelocity)
                response.acceleration = float(vel_params.Acceleration)
            response.success = True
            response.error_message = "Successfully set velocity parameters"

        except Exception as e:
            self.get_logger().error(
                f'Error getting/setting velocity parameters: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response

    # Helper functions
    def shutdown(self):
        """
        Properly shutdown the device connection.

        This ensures the device is left in a good state and resources are released.
        """
        if self.connected and self.device:
            try:
                # Stop polling for status updates
                self.device.StopPolling()

                # Disconnect from the device
                # False parameter means don't wait for responses
                self.device.Disconnect(False)

                # Update connection state
                self.connected = False
                self.get_logger().info('Device disconnected')
            except Exception as e:
                self.get_logger().error(f'Error during shutdown: {e}')

    def setup_clients(self):

        # Richtet Clients für die andere Achse ein (X oder Z).
        # Die Z-Achse fragt die Position der X-Achse ab und umgekehrt.

        # Bestimme, welche Achse dieser Node repräsentiert
        is_z_axis = 'z_axis' in self.node_name.lower()

        # Konfiguriere den Client für die jeweils andere Achse
        if is_z_axis:
            # Wenn dies die Z-Achse ist, verbinde mit der X-Achse
            self.other_axis_name = 'lts300_camera_x_axis'
            self.get_logger().info(
                f'Z-Achse: Erstelle Client für X-Achse: {self.other_axis_name}')
        else:
            # Wenn dies die X-Achse ist, verbinde mit der Z-Achse
            other_axis_name = 'lts300_z_axis'
            self.get_logger().info(
                f'X-Achse: Erstelle Client für Z-Achse: {self.other_axis_name}')

        # Initialisiere das Dictionary für den Client
        self.other_axis_clients = {}

        # Erstelle den Client für die andere Achse
        client = self.create_client(
            GetPosition, f'{other_axis_name}/get_position')
        self.other_axis_clients[other_axis_name] = client

        # Starte einen Timer, der regelmäßig versucht, die Verbindung herzustellen
        self.client_check_timer = self.create_timer(
            5.0, self.check_client_connection)

    #    Flag, um zu verfolgen, ob die Verbindung hergestellt wurde
        self.client_connected = False

    def check_client_connection(self):
        """
        Überprüft periodisch die Verbindung zum anderen Achsen-Service.
        """
        if self.client_connected:
            # Wenn bereits verbunden, Timer stoppen
            self.client_check_timer.cancel()
            return

        client = self.other_axis_clients.get(self.other_axis_name)
        if client:
            ready = client.wait_for_service(timeout_sec=1.0)
            if ready:
                self.get_logger().info(
                    f'Verbindung zu {self.other_axis_name} hergestellt')
                self.client_connected = True
                # Timer stoppen, da Verbindung hergestellt
                self.client_check_timer.cancel()
            else:
                self.get_logger().warning(
                    f'Service für {self.other_axis_name} noch nicht verfügbar, versuche erneut...')

    def check_other_axis_position(self):
        """
        Überprüft die Position der anderen Achse und implementiert Fehlerbehandlung.

        Returns:
            bool: True, wenn die andere Achse gehomed ist oder wenn der Service nicht 
                verfügbar ist (um Blockaden zu vermeiden), False sonst.
        """
        # Wenn keine Verbindung hergestellt wurde, erlaube die Bewegung trotzdem
        if not self.client_connected:
            self.get_logger().warning(
                f'Keine Verbindung zu {self.other_axis_name}, erlaube Bewegung trotzdem')
            return True

        for axis_name, client in self.other_axis_clients.items():
            try:
                request = GetPosition.Request()
                # Kürzeres Timeout für den Service-Aufruf
                future = client.call_async(request)

                # Warte maximal 2 Sekunden auf eine Antwort
                timeout_sec = 2.0
                start_time = time.time()
                while (time.time() - start_time) < timeout_sec and not future.done():
                    rclpy.spin_once(self, timeout_sec=0.1)

                if not future.done():
                    self.get_logger().error(
                        f'Timeout beim Warten auf Antwort von {axis_name}')
                    # Erlaube die Bewegung trotz Timeout
                    return True

                if future.result() is not None:
                    response = future.result()
                    if response.success:
                        if abs(response.axis_position) > 0.001:  # Toleranz für Rundungsfehler
                            self.get_logger().error(
                                f'{axis_name} ist nicht gehomed (Position: {response.axis_position})')
                            return False
                        else:
                            self.get_logger().info(
                                f'{axis_name} ist gehomed (Position: {response.axis_position})')
                            return True
                    else:
                        self.get_logger().error(
                            f'Fehler beim Abrufen der Position von {axis_name}: {response.error_message}')
                        # Erlaube die Bewegung trotz Fehler
                        return True
                else:
                    self.get_logger().error(
                        f'Service-Aufruf für {axis_name} fehlgeschlagen')
                    # Erlaube die Bewegung trotz Fehler
                    return True

            except Exception as e:
                self.get_logger().error(
                    f'Unerwarteter Fehler bei der Überprüfung von {axis_name}: {e}')
                # Erlaube die Bewegung trotz Fehler
                return True

        return True  # Alle überprüften Achsen sind gehomed


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
