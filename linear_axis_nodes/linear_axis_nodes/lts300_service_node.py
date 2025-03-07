
import os
import sys
import time
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from promoc_assembly_interfaces.srv import MoveTo, Home

# Add path to Thorlabs DLLs
kinesis_path = "C:\\Program Files\\Thorlabs\\Kinesis"
if kinesis_path not in sys.path:
    sys.path.append(kinesis_path)

# Import .NET interoperability
import clr

# Load required .NET assemblies
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")

from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.KCube.DCServoCLI import *
from System import Decimal

class LTS300Node(Node):
    def __init__(self):
        super().__init__('lts300_node')
        
        # Parameters
        self.declare_parameter('serial_number', '')
        self.serial_no = self.get_parameter('serial_number').get_parameter_value().string_value
        
        if not self.serial_no:
            self.get_logger().error('No serial number provided. Please set the "serial_number" parameter.')
            return
            
        self.device = None
        self.connected = False
        self.lock = threading.Lock()
        
        # Services
        self.move_to_service = self.create_service(
            MoveTo, 'lts300/move_to', self.move_to_callback)
        self.home_service = self.create_service(
            Home, 'lts300/home', self.home_callback)
            
        # Publisher
        self.position_pub = self.create_publisher(
            Float64, 'lts300/position', 10)
            
        # Timer for regular position updates
        self.position_timer = self.create_timer(0.1, self.publish_position)
        
        # Establish connection
        self.connect()
        
    def connect(self):
        """Establish connection to the LTS300"""
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
            
            # Connect to the controller
            self.device = KCubeDCServo.CreateKCubeDCServo(self.serial_no)
            self.device.Connect(self.serial_no)
            
            # Wait for initialization
            time.sleep(1)
            
            # Initialize the controller
            self.device.EnableDevice()
            self.get_logger().info('Device enabled')
            
            # Load the configuration
            self.device.LoadMotorConfiguration(self.serial_no)
            
            # Get the configuration
            device_info = self.device.GetDeviceInfo()
            
            self.get_logger().info(f'Connected to {device_info.Name}')
            self.connected = True
            
        except Exception as e:
            self.get_logger().error(f'Error connecting: {e}')
            self.connected = False
    
    def disconnect(self):
        """Disconnect from the LTS300"""
        if self.device and self.connected:
            try:
                self.device.Disconnect(True)
                self.get_logger().info('Connection closed')
                self.connected = False
            except Exception as e:
                self.get_logger().error(f'Error disconnecting: {e}')
    
    def move_to_callback(self, request, response):
        """Callback for the MoveTo service"""
        if not self.connected or not self.device:
            response.success = False
            response.message = "Not connected to device"
            return response
            
        try:
            with self.lock:
                self.get_logger().info(f'Moving to position {request.position}mm...')
                self.device.MoveTo(Decimal(request.position), 60000)  # 60s timeout
                
                # Read current position
                pos = self.device.Position
                self.get_logger().info(f'Position reached: {pos}mm')
                
                response.success = True
                response.message = f"Position {pos}mm reached"
        except Exception as e:
            self.get_logger().error(f'Error during movement: {e}')
            response.success = False
            response.message = str(e)
            
        return response
    
    def home_callback(self, request, response):
        """Callback for the Home service"""
        if not self.connected or not self.device:
            response.success = False
            response.message = "Not connected to device"
            return response
            
        try:
            with self.lock:
                self.get_logger().info('Moving to home position...')
                self.device.Home(60000)  # 60s timeout
                self.get_logger().info('Home position reached')
                
                response.success = True
                response.message = "Home position reached"
        except Exception as e:
            self.get_logger().error(f'Error during homing: {e}')
            response.success = False
            response.message = str(e)
            
        return response
    
    def publish_position(self):
        """Publish current position"""
        if not self.connected or not self.device:
            return
            
        try:
            # Read current position
            pos = self.device.Position
            
            # Publish position
            msg = Float64()
            msg.data = float(pos)
            self.position_pub.publish(msg)
        except Exception as e:
            self.get_logger().debug(f'Error reading position: {e}')
    
    def __del__(self):
        """Destructor"""
        self.disconnect()

def main(args=None):
    rclpy.init(args=args)
    
    node = LTS300Node()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.disconnect()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()