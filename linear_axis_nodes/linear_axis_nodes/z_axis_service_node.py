# ROS 2 imports
import rclpy
from rclpy.node import Node

'Thorlabs Kinesis imports'
import platform
import time
import clr # type: ignore

if platform.system() != "Windows":
    print("This script is intended to run on Windows only.")
    exit()

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")
from Thorlabs.MotionControl.DeviceManagerCLI import * # type: ignore
from Thorlabs.MotionControl.GenericMotorCLI import * # type: ignore
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import * # type: ignore
from System import Decimal  # type: ignore # necessary for real world units



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
        self.device = None
        # Initialize core parameters
        

        # Setup ROS publishers and services
        self.setup_services()

        # Initialize connections
        self.startup_connection()


    
    def startup_connection(self):
        device_serial_number = '45318394'
        print(f"Attempting to connect to device with serial number: {device_serial_number}")

        # Connect to the device
        self.connect_to_device(device_serial_number)

        # Initialize device settings
        self.initialize_device_settings(device_serial_number)

    def connect_to_device(self, device_serial_number):
        while self.device_instance is None:
            try:
                self.device_instance = LongTravelStage.CreateLongTravelStage(device_serial_number)
                self.device_instance.Connect(device_serial_number)
                print("Device connected successfully!")
            except Exception as e:
                print(f"Connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)
        self.device_instance.StartPolling(500)  # Increase polling rate to 500ms
        time.sleep(0.5)  # Give some time to establish the connection

    def initialize_device_settings(self, device_serial_number):
        try:
            if not self.device_instance.IsSettingsInitialized():
                self.device_instance.WaitForSettingsInitialized(10000)  # 10 second timeout
                assert self.device_instance.IsSettingsInitialized() is True

            # Start polling and enable
            self.device_instance.StartPolling(250)  # 250ms polling rate
            time.sleep(0.25)
            self.device_instance.EnableDevice()
            time.sleep(0.25)  # Wait for the device to enable

            # Get device information and display description
            device_information = self.device_instance.GetDeviceInfo()

            # Load any configuration settings needed by the controller/stage
            motor_configuration = self.device_instance.LoadMotorConfiguration(device_serial_number)

            # Get parameters related to homing/zeroing/other
            homing_parameters = self.device_instance.GetHomingParams()
            print(f'Homing velocity: {homing_parameters.Velocity}\n,'
                  f'Homing Direction: {homing_parameters.Direction}')
            
            homing_parameters.Velocity = Decimal(5.0)  # real units, mm/s

            # Set homing params (if changed)
            self.device_instance.SetHomingParams(homing_parameters)
        except DeviceNotReadyException:
            print(f"Device with serial number {device_serial_number} is not ready.")
        except Exception as e:
            print(f"Error occurred during initialization: {e}")


        
      

        

   


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
                self.get_logger().info(f'Nothing Happened')
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

