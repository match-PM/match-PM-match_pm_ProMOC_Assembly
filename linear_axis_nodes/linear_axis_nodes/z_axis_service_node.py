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
from promoc_assembly_interfaces.msg import XBotInfo, LinearAxisInfo
from promoc_assembly_interfaces.srv import (
    ActivateXbots,
    ArcMotionTargetRadius,
    LevitationXbots,
    LinearMotionSi,
    RotaryMotion,
    SetVelocityAcceleration,
    SixDofMotion,
    StopMotion,
    MoveTo,
    Home,
    ShutdownLinearAxis
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
        
        self.declare_parameter('serial_number', value="45318394")

        # Setup ROS publishers and services
        self.setup_services()

        # Initialize connections
        self.startup_connection()


    

    

    def startup_connection(self):
        # create new device
        self.serial_no = self.get_parameter("serial_number").get_parameter_value().string_value
        # Connect, begin polling, and enable
        self.device = LongTravelStage.CreateLongTravelStage(self.serial_no)
        self.device.Connect(self.serial_no)

        # Ensure that the device settings have been initialized
        if not self.device.IsSettingsInitialized():
            self.device.WaitForSettingsInitialized(10000)  # 10 second timeout
            assert self.device.IsSettingsInitialized() is True

        # Start polling and enable
        self.device.StartPolling(250)  #250ms polling rate
        time.sleep(0.25)
        self.device.Enableself.device()
        time.sleep(0.25)  # Wait for self.device to enable

        # Get self.device Information and display description
        device_info = self.device.GetDeviceInfo()
        print(device_info.Description)

        # Load any configuration settings needed by the controller/stage
        motor_config = self.device.LoadMotorConfiguration(self.serial_no)

        # Get parameters related to homing/zeroing/other
        home_params = self.device.GetHomingParams()
        print(f'Homing velocity: {home_params.Velocity}\n,'
              f'Homing Direction: {home_params.Direction}')
        home_params.Velocity = Decimal(10.0)  # real units, mm/s
        # Set homing params (if changed)
        self.device.SetHomingParams(home_params)


   


    def setup_services(self):
        self.homing_server = self.create_service(Home, f"{self.get_name()}/home", self.callback_home)
        
        self.move_to_server =self.create_service(MoveTo, f"{self.get_name()}/move_to", self.callback_linear_axis_move_to)

        self.shutdown_device = self.create_service(ShutdownLinearAxis, f"{self.get_name()}/move_to", self.callback_shutdown_device)


    def callback_home(self,request,response):

        self.get_logger().info(f"Starting homing motion for Axis {self.serial_no} ")
        try: 
            if request.homing == True:
                self.device.Home(60000)
                self.get_logger().info("Device is Homed")
                response.finished = True
            else:
                self.get_logger().info("Device will do Nothing")
                response.finished = True
        except Exception as e:
                self.get_logger().warning("Something went terribly wrong")

                response.finished = False
        finally:
            return response

        


    def callback_linear_axis_move_to(self, request, response):
        try:
            target_pos = Decimal(request.axis_position)
            self.get_logger().info(f"Starting motion for Axis {self.serial_no} to position {target_pos}")
            self.device.MoveTo(target_pos, 60000)
            self.get_logger().info(f'Done')
            response.finished = True  # Indicating successful motion
        except Exception as e:
            self.get_logger().warning(f"Something went terribly wrong: {str(e)}")
            response.finished = False  # Indicating failure
        return response



    def callback_shutdown_device(self,request,response):
        try:
            if request.shutdown == True:
                self.device.StopPolling()
                self.device.Disconnect()
                response.finished = True
            else:
                self.get_logger().info(f'Nothing Happend')
                response.finished = True
                
        except Exception as e:
            self.get_logger().warning(f"Something went terribly wrong: {str(e)}")
            response.finished = False  # Indicating failure
        finally:
            return response

        


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

