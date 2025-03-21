# ROS 2 imports
import rclpy                                    #type:ignore
from rclpy.node import Node                     #type:ignore    
#from std_msgs.msg import Float64                #type:ignore
#from std_srvs.srv import Trigger                #type:ignore
#from geometry_msgs.msg import Point             #type:ignore

# Import the platform check and Thorlabs libraries from lts300.py
import platform
import time
import clr
#import threading

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
from promoc_assembly_interfaces.srv import MoveAbsolute,MoveRelativ, Home, ShutdownLinearAxis, GetPosition


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

    # Initialization functions    
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
        try:
            self.get_logger().info(f'Connecting to LTS300 (SN: {self.serial_no})...')

            DeviceManagerCLI.BuildDeviceList()

            if not DeviceManagerCLI.IsDeviceConnected(self.serial_no):
                available_devices = DeviceManagerCLI.GetDeviceList()
                self.get_logger().error(f'Device with serial number {self.serial_no} not found!')
                self.get_logger().info('Available devices:')
                for device in available_devices:
                    self.get_logger().info(f' - {device}')
                return

            self.device = LongTravelStage.CreateLongTravelStage(self.serial_no)

            # Connect to the device
            self.device.Connect(self.serial_no)

            # Wait for the device settings to initialize
            if not self.device.IsSettingsInitialized():
                self.device.WaitForSettingsInitialized(10000)  # 10 second timeout

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


    # Callback functions for ROS services
    def move_absolute_callback(self, request, response):
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
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
            response.error_message = ""
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
            response.error_message = ""
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
            response.error_message = ""
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"
        finally:
            return response
    
    def get_position_callback(self, request, response):
        if not self.connected:
            response.success = False
            response.error_message = "Device not connected"
            return response

        try:
            # Get the current position from the device
            response.position = self.position
            response.error_message = ""
        except Exception as e:
            self.get_logger().error(f'Error getting position: {e}')
            response.success = False
            response.axis_position = 0.0
            response.error_message = f"Error: {str(e)}"

        return response



    # Helper functions
    def setup_services(self):
        # Create service for moving
        self.move_absolute_service = self.create_service(
            MoveAbsolute, 'lts300/move_to', self.move_absolute_callback)
        
        self.move_relative_service = self.create_service(
            MoveRelativ, 'lts300/move_to', self.move_relative_callback)
        
        # Create service for homing the device
        self.home_service = self.create_service(
            Home, 'lts300/home', self.home_callback)
        
        self.shutdown_service = self.create_service(
            ShutdownLinearAxis, 'lts300/shutdown', self.shutdown_callback)
        
        self.get_position_service = self.create_service(
            GetPosition, 'lts300/get_position', self.get_position_callback)
        
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
