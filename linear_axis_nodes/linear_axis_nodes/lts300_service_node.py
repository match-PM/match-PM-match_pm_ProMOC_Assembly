# ROS 2 imports
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from std_srvs.srv import Trigger
from geometry_msgs.msg import Point

# Import the platform check and Thorlabs libraries from lts300.py
import platform
import time
import clr
import threading

# Check if running on Windows, as Thorlabs libraries only work on Windows
if platform.system() != "Windows":
    print("This script is intended to run on Windows only.")
    exit()

# Load Thorlabs .NET assemblies using Python.NET (clr)
# These DLLs provide the interface to control Thorlabs motion devices
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")

# Import specific classes from the Thorlabs .NET libraries
from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI  # For device discovery and connection             #type:ignore
from Thorlabs.MotionControl.GenericMotorCLI import MotorDirection     # For specifying motor direction                  #type:ignore
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import LongTravelStage  # For controlling the LTS300 stage       #type:ignore
from System import Decimal  # .NET Decimal type for precise position values                                             #type:ignore    

# Import custom service and message types
from promoc_assembly_interfaces.srv import MoveTo, Home
from promoc_assembly_interfaces.msg import LinearAxisInfo

class LTS300ServiceNode(Node):
    """
    ROS2 Node for controlling a Thorlabs LTS300 Linear Translation Stage.
    
    This node provides services to move the stage to specific positions and to home the stage.
    It uses the Thorlabs Kinesis .NET libraries via Python.NET to communicate with the hardware.
    """
    def __init__(self):

        # Initialize the ROS2 node with name 'lts300_service_node'
        super().__init__('lts300_service_node')
        
        # Initialize core parameters and device connection
        self.initialize_parameters()
        
        # Set up ROS2 services
        self.setup_services()
        
        # Connect to the physical LTS300 device
        self.connect()

        # Log initialization status
        if self.connected:
            self.get_logger().info('LTS300 node initialized')
        else:
            self.get_logger().error('Failed to initialize LTS300 node')
        
    def initialize_parameters(self):
        # Declare the serial number parameter with a default value
        # This can be overridden when launching the node
        self.declare_parameter('serial_number', '45318394')  # Default serial number
        
        # Get the serial number from parameters
        self.serial_no = self.get_parameter('serial_number').get_parameter_value().string_value
        
        # Initialize connection state variables
        self.connected = False  # Flag to track connection status
        self.device = None      # Will hold the device object when connected
        
        # Additional state variables could be added here (position, status, etc.)

    def connect(self):
        """
        Connect to the LTS300 device using the Thorlabs Kinesis library.
        
        This method:
        1. Builds a list of connected devices
        2. Checks if our device is connected
        3. Creates and connects to the device
        4. Initializes the device settings
        5. Starts polling and enables the device
        """
        try:
            self.get_logger().info(f'Connecting to LTS300 (SN: {self.serial_no})...')

            # Initialize the DeviceManager to discover connected devices
            DeviceManagerCLI.BuildDeviceList()

            # Check if our device is connected by serial number
            if not DeviceManagerCLI.IsDeviceConnected(self.serial_no):
                # If not connected, list available devices to help troubleshooting
                available_devices = DeviceManagerCLI.GetDeviceList()
                self.get_logger().error(f'Device with serial number {self.serial_no} not found!')
                self.get_logger().info('Available devices:')
                for device in available_devices:
                    self.get_logger().info(f' - {device}')
                return

            # Create the device object and connect to it
            self.device = LongTravelStage.CreateLongTravelStage(self.serial_no)
            self.device.Connect(self.serial_no)

            # Ensure that the device settings have been initialized
            # This is important before sending commands to the device
            if not self.device.IsSettingsInitialized():
                self.device.WaitForSettingsInitialized(10000)  # 10 second timeout
                assert self.device.IsSettingsInitialized() is True

            # Start polling (periodic status updates from the device)
            # and enable the device for operation
            self.device.StartPolling(250)  # 250ms polling rate
            time.sleep(0.25)  # Short delay to allow polling to start
            self.device.EnableDevice()
            time.sleep(0.25)  # Wait for device to enable

            # Get and log the device info
            device_info = self.device.GetDeviceInfo()
            self.get_logger().info(f'Connected to {device_info.Name}')

            # Set the device connected flag to true
            self.connected = True

        except Exception as e:
            # Log any errors that occur during connection
            self.get_logger().error(f'Error connecting: {e}')
            self.connected = False

    def move_to_callback(self, request, response):
        """
        Handle move_to service requests to move the stage to a specific position.
        
        Args:
            request: The service request containing the target position
            response: The service response to be filled
            
        Returns:
            The filled service response
        """
        # Check if device is connected before attempting to move
        if not self.connected:
            response.success = False
            response.message = "Device not connected"
            return response
        
        try:
            position = request.position
            self.get_logger().info(f'Moving to position: {position} mm')
            
            # Convert to Decimal for the Thorlabs API (requires .NET Decimal type)
            decimal_position = Decimal(position)
            
            # Move to position with a timeout
            # The is_moving flag could be used by other methods to check movement status
            self.is_moving = True
            self.device.MoveTo(decimal_position, 60000)  # 60 second timeout
            self.is_moving = False
            
            # Update internal position state and prepare successful response
            self.position = position
            response.success = True
            response.message = f"Moved to {position} mm"
        except Exception as e:
            # Log and return any errors that occur during movement
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.message = f"Error: {str(e)}"
        
        return response

    def home_callback(self, request, response):
        """
        Handle home service requests to home the stage.
        
        Homing is the process of moving to a known reference position (usually zero).
        
        Args:
            request: The service request (empty for Home service)
            response: The service response to be filled
            
        Returns:
            The filled service response
        """
        # Check if device is connected before attempting to home
        if not self.connected:
            response.success = False
            response.message = "Device not connected"
            return response
        
        try:
            self.get_logger().info('Homing device...')
            
            # Execute the homing operation with a timeout
            self.is_moving = True
            self.device.Home(60000)  # 60 second timeout
            self.is_moving = False
            
            # Update internal position state (home is position 0)
            self.position = 0.0
            
            # Prepare successful response
            response.success = True
            response.message = "Homing completed successfully"
        except Exception as e:
            # Log and return any errors that occur during homing
            self.get_logger().error(f'Error during homing: {e}')
            response.success = False
            response.message = f"Error: {str(e)}"
        
        return response
    
    def setup_services(self):
        # Create service for moving to a position
        self.move_to_service = self.create_service(
            MoveTo, 'lts300/move_to', self.move_to_callback)
        
        # Create service for homing the device
        self.home_service = self.create_service(
            Home, 'lts300/home', self.home_callback)
        
        # Additional services could be added here (get_position, stop, etc.)

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

def main(args=None):
    # Initialize the ROS2 Python client library
    rclpy.init(args=args)
    
    # Create the node
    node = LTS300ServiceNode()
    
    try:
        # Keep the node running until interrupted
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        pass
    finally:
        # Ensure proper cleanup
        node.shutdown()  # Properly shutdown the device
        node.destroy_node()
        
        # Shutdown ROS2 client library if it's still running
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except rclpy.exceptions.RCLError:
                pass  # Ignore the shutdown error if ROS is already shutting down

if __name__ == "__main__":
    main()
