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

if platform.system() != "Windows":
    print("This script is intended to run on Windows only.")
    exit()

# Load Thorlabs .NET assemblies
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")
from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.GenericMotorCLI import MotorDirection
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import LongTravelStage
from System import Decimal  # necessary for real world units

from promoc_assembly_interfaces.srv import MoveTo, Home
from promoc_assembly_interfaces.msg import LinearAxisInfo

class LTS300ServiceNode(Node):
    def __init__(self):
        super().__init__('lts300_service_node')
        # Initialize core parameter
        self.initialize_parameters()
        

        # Services
        self.setup_services()
        
        # Connect to the device
        self.connect()

        if self.connected:
            self.get_logger().info('LTS300 node initialized')
        else:
            self.get_logger().error('Failed to initialize LTS300 node')
        
    def initialize_parameters(self):
        # Parameters
        self.declare_parameter('serial_number', '45318394')  # Default serial number
        self.serial_no = self.get_parameter('serial_number').get_parameter_value().string_value
        self.connected = False
        self.device = None

    def connect(self):
        """Connect to the LTS300 device"""
        try:
            self.get_logger().info(f'Connecting to LTS300 (SN: {self.serial_no})...')

            # Initialize the DeviceManager
            DeviceManagerCLI.BuildDeviceList()

            # Check if the device is connected
            if not DeviceManagerCLI.IsDeviceConnected(self.serial_no):
                available_devices = DeviceManagerCLI.GetDeviceList()
                self.get_logger().error(f'Device with serial number {self.serial_no} not found!')
                self.get_logger().info('Available devices:')
                for device in available_devices:
                    self.get_logger().info(f' - {device}')
                return

            # Create and connect to the device
            self.device = LongTravelStage.CreateLongTravelStage(self.serial_no)
            self.device.Connect(self.serial_no)

            # Ensure that the device settings have been initialized
            if not self.device.IsSettingsInitialized():
                self.device.WaitForSettingsInitialized(10000)  # 10 second timeout
                assert self.device.IsSettingsInitialized() is True

            # Start polling and enable
            self.device.StartPolling(250)  # 250ms polling rate
            time.sleep(0.25)
            self.device.EnableDevice()
            time.sleep(0.25)  # Wait for device to enable

            # Get the device info
            device_info = self.device.GetDeviceInfo()
            self.get_logger().info(f'Connected to {device_info.Name}')

            # Set the device connected flag
            self.connected = True

        except Exception as e:
            self.get_logger().error(f'Error connecting: {e}')
            self.connected = False
    def move_to_callback(self, request, response):
        """Handle move_to service requests"""
        if not self.connected:
            response.success = False
            response.message = "Device not connected"
            return response
        
        try:
            position = request.position
            self.get_logger().info(f'Moving to position: {position} mm')
            
            # Convert to Decimal for the Thorlabs API
            decimal_position = Decimal(position)
            
            # Move to position
            self.is_moving = True
            self.device.MoveTo(decimal_position, 60000)  # 60 second timeout
            self.is_moving = False
            
            self.position = position
            response.success = True
            response.message = f"Moved to {position} mm"
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.message = f"Error: {str(e)}"
        
        return response

    def home_callback(self, request, response):
        """Handle home service requests"""
        if not self.connected:
            response.success = False
            response.message = "Device not connected"
            return response
        
        try:
            self.get_logger().info('Homing device...')
            self.is_moving = True
            self.device.Home(60000)  # 60 second timeout
            self.is_moving = False
            self.position = 0.0
            
            response.success = True
            response.message = "Homing completed successfully"
        except Exception as e:
            self.get_logger().error(f'Error during homing: {e}')
            response.success = False
            response.message = f"Error: {str(e)}"
        
        return response
    
    def setup_services(self):
        self.move_to_service = self.create_service(MoveTo, 'lts300/move_to', self.move_to_callback)
        self.home_service = self.create_service(Home, 'lts300/home', self.home_callback)

    def shutdown(self):
        """Shutdown the device properly"""
        if self.connected and self.device:
            try:
                self.device.StopPolling()
                self.device.Disconnect(False)
                self.connected = False
                self.get_logger().info('Device disconnected')
            except Exception as e:
                self.get_logger().error(f'Error during shutdown: {e}')
def main(args=None):
    rclpy.init(args=args)   
    node = LTS300ServiceNode()   
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()  # Properly shutdown the device
        node.destroy_node()
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except rclpy.exceptions.RCLError:
                pass  # Ignore the shutdown error 

if __name__ == "__main__":
    main()

