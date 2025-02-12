# ROS 2 imports
import rclpy
from rclpy.node import Node

'Thorlabs Kinesis imports'
import platform
import time
import clr

if platform.system() != "Windows":
    print("This script is intended to run on Windows only.")
    exit()

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import *
from System import Decimal  # necessary for real world units



# Import custom message and service interfaces from promoc_assembly_interfaces
from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import (
    ActivateXbots,
    ArcMotionTargetRadius,
    LevitationXbots,
    LinearMotionSi,
    RotaryMotion,
    SetVelocityAcceleration,
    SixDofMotion,
    StopMotion,
)




class Z_Axis_Service_Node(Node): 
    def __init__(self):
        """
        Initialize the MoverServiceNode class.

        This function sets up the ROS node, creates publishers and service servers for handling motions and commands,
        initializes the connection to the PMC and XBot, and starts a timer to periodically publish XBot position.
        """

        super().__init__("z_axis_service_node")

        # Initialize core parameters
        self.initialize_parameters()

        # Setup ROS publishers and services
        self.setup_publishers()
        self.setup_services()

        # Initialize connections
        self.startup_connection()



    def startup_connection(self):
        # create new device
        serial_no = "45877001"  # Replace this line with your device's serial number

        # Connect, begin polling, and enable
        device = LongTravelStage.CreateLongTravelStage(serial_no)
        device.Connect(serial_no)

        # Ensure that the device settings have been initialized
        if not device.IsSettingsInitialized():
            device.WaitForSettingsInitialized(10000)  # 10 second timeout
            assert device.IsSettingsInitialized() is True

        # Start polling and enable
        device.StartPolling(250)  #250ms polling rate
        time.sleep(0.25)
        device.EnableDevice()
        time.sleep(0.25)  # Wait for device to enable

        # Get Device Information and display description
        device_info = device.GetDeviceInfo()
        print(device_info.Description)

        # Load any configuration settings needed by the controller/stage
        motor_config = device.LoadMotorConfiguration(serial_no)

        # Get parameters related to homing/zeroing/other
        home_params = device.GetHomingParams()
        print(f'Homing velocity: {home_params.Velocity}\n,'
              f'Homing Direction: {home_params.Direction}')
        home_params.Velocity = Decimal(10.0)  # real units, mm/s
        # Set homing params (if changed)
        device.SetHomingParams(home_params)






def main(args=None):
    rclpy.init(args=args)   
    node = Z_Axis_Service_Node()   
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except rclpy.exceptions.RCLError:
                pass  # Ignore the shutdown error 

if __name__ == "__main__":
    main()

