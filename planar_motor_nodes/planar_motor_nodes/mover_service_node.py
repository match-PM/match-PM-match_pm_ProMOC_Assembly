
import sys
import os
import rclpy
from rclpy.node import Node
import time

# To use the mock_pmclib we need to add the current script's directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# import of mock_pmclib incase of pmclib not being available
try:
    from pmclib import system_commands as sys
    from pmclib import xbot_commands as bot
    from pmclib import pmc_types
except ImportError as e:
    print(f"Using mock pmclib due to import error: {e}")
    from mock_pmclib import system_commands as sys
    from mock_pmclib import xbot_commands as bot
    from mock_pmclib import pmc_types

# import of promoc_assembly_interfaces
from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import ActivateXbots
from promoc_assembly_interfaces.srv import ArcMotionTargetRadius
from promoc_assembly_interfaces.srv import LevitationXbots
from promoc_assembly_interfaces.srv import LinearMotionSi
from promoc_assembly_interfaces.srv import RotaryMotion
from promoc_assembly_interfaces.srv import SixDofMotion
from promoc_assembly_interfaces.srv import StopMotion




class MoverServiceNode(Node): 
    def __init__(self):
        """
        Initialize the MoverServiceNode class.

        This function sets up the ROS node, creates publishers and service servers for handling motions and commands,
        initializes the connection to the PMC and XBot, and starts a timer to periodically publish XBot position.

        Parameters:
        None

        Returns:
        None
        """

        super().__init__("mover_node")
        self.xbot_id = 1

        # Publisher to publish XBot information (position, rotation)
        self.xbot_pos_publisher_ = self.create_publisher(XBotInfo, "xbot_info", 10)

        # Define service callbacks for handling motions and commands
        self.linear_movement_server = self.create_service(LinearMotionSi, f"{self.get_name()}/linear_mover_motion", self.callback_linear_motion_si)
        self.six_d_movement_server = self.create_service(SixDofMotion, f"{self.get_name()}/six_d_mover_motion", self.callback_six_d_motion)
        self.xbot_activation_server = self.create_service(ActivateXbots, f"{self.get_name()}/activate_xbots", self.callback_activate_xbot)
        self.xbot_levitation_server = self.create_service(LevitationXbots, f"{self.get_name()}/levitation_xbots", self.callback_levitation_xbot)
        self.xbot_arc_motion_target_radius_server = self.create_service(ArcMotionTargetRadius, f"{self.get_name()}/arcmotion_target_radius", self.callback_arc_motion_target_radius)
        self.xbot_stop_motion_server = self.create_service(StopMotion, f"{self.get_name()}/stop_motion", self.callback_stop_motion)
        self.xbot_rotary_motion_server = self.create_service(RotaryMotion, f"{self.get_name()}/rotary_motion", self.callback_rotary_motion)

        # Initialize connection to PMC and XBot
        self.startup_connection()

        # Timer to periodically publish XBot position
        self.xbot_position_timer = self.create_timer(0.1, self.xbot_postition_publisher)

    def xbot_postition_publisher(self):
        """
        This function publishes the current position of the XBot to a ROS topic.

        Parameters:
        None

        Returns:
        None

        The function initializes an XBotInfo message, retrieves the current position of the XBot using the
        `bot.get_all_xbot_info` function, and populates the message fields with the XBot's position data.
        If the `xbot_data_list` is empty, an error message is logged. Finally, the message is published to the
        `xbot_pos_publisher_` topic.
        """
        msg = XBotInfo()
        try:
            xbot_data_list = bot.get_all_xbot_info(0)
            msg.x_pos = float(xbot_data_list[0].x_pos)
            msg.y_pos = float(xbot_data_list[0].y_pos)
            msg.z_pos = float(xbot_data_list[0].z_pos)
            msg.rx_pos = float(xbot_data_list[0].rx_pos)
            msg.ry_pos = float(xbot_data_list[0].ry_pos)
            msg.rz_pos = float(xbot_data_list[0].rz_pos)
        except IndexError:
            self.get_logger().error("Error: xbot_data_list is empty")

        self.xbot_pos_publisher_.publish(msg)

    def callback_linear_motion_si(self, request, response):
        try:
            # Convert position values from millimeters to meters
            target_position = [
                request.x_pos / 1000, request.y_pos / 1000
            ]
            # The * infront of targe_postion unpacks the target_position list into individual parameters.
            bot.linear_motion_si(request.xbot_id, *target_position, request.xy_max_speed, request.xy_max_accl)
            # Wait until the target position is reached within tolerance
            while not self.check_position_reached(target_position, self.get_current_position(), tolerance=0.01):
                time.sleep(0.001)

            response.finished = True
        
        except Exception as e:
            self.get_logger().error(f"INVALID PARAMETER: {e}")
            response.finished = False

        return response

    def callback_arc_motion_target_radius(self, request, response): 
        try:
            bot.arc_motion_target_radius(request.xbot_id, request.x_pos / 1000, request.y_pos / 1000, request.arc_type,
                                         request.postion_mode, request.arc_dir, request.radius_meters / 1000,
                                         request.xy_max_speed, request.xy_max_accl, request.final_speed)
            response.finished = True
        except:
            self.get_logger().error("INVALID PARAMETER")
            response.finished = False
        return response

    def callback_rotary_motion(self, request, response):
        try:
            bot.rotary_motion(request.xbot_id, request.target_rz, request.max_speed, request.max_accel)
            response.finished = True
        except:
            self.get_logger().error("INVALID PARAMETER")
            response.finished = False
        return response 

    def callback_stop_motion(self, request, response):
        try:
            bot.stop_motion(request.xbot_id)
            response.finished = True
        except:
            self.get_logger().error("Stop Motion didn't work")
            response.finished = False
        return response

    def callback_six_d_motion(self, request, response):
        """
        Handles a six-dimensional motion request for a specific XBot.

        This function converts the position values from millimeters to meters, executes the motion command with the
        converted positions and speed parameters, waits until the target position is reached within a specified tolerance,
        and returns a response indicating whether the motion was successfully completed.

        Parameters:
        - request (promoc_assembly_interfaces.srv.SixDofMotion.Request): The motion request containing the XBot ID,
          target position, and maximum speed and acceleration parameters.

        - response (promoc_assembly_interfaces.srv.SixDofMotion.Response): The response to be filled with the success status
          of the motion.

        Returns:
        - response (promoc_assembly_interfaces.srv.SixDofMotion.Response): The response containing the success status
          of the motion.
        """
        try:
            # Convert position values from millimeters to meters
            target_position = [
                request.x_pos / 1000, request.y_pos / 1000, request.z_pos / 1000,
                request.rx_pos / 1000, request.ry_pos / 1000, request.rz_pos / 1000
            ]

            # Execute motion command with converted positions and speed parameters
            bot.six_d_of_motion_si(
                request.xbot_id, *target_position,
                request.xy_max_speed, request.xy_max_accl, request.z_max_speed,
                request.rx_max_speed, request.ry_max_speed, request.rz_max_speed
            )

            # Wait until the target position is reached within tolerance
            while not self.check_position_reached(target_position, self.get_current_position(), tolerance=0.01):
                time.sleep(0.001)

            response.finished = True

        except Exception as e:
            self.get_logger().error(f"INVALID PARAMETER: {e}")
            response.finished = False

        return response


    def check_position_reached(self, target_position:list, current_position:list, tolerance:float):
        for i in range(len(target_position)):
            if abs(target_position[i] - current_position[i]) > tolerance:
                return False
        return True
    
    def get_current_position(self) -> list:
        try:
            xbot_data_list = bot.get_all_xbot_info(0)
            current_position = [float(xbot_data_list[0].x_pos), float(xbot_data_list[0].y_pos), float(xbot_data_list[0].z_pos),
                                  float(xbot_data_list[0].rx_pos), float(xbot_data_list[0].ry_pos), float(xbot_data_list[0].rz_pos)]
            return current_position
        except IndexError:
            self.get_logger().error("Error: xbot_data_list is empty")
            return [0, 0, 0, 0, 0, 0]
        

    def callback_activate_xbot(self, request, response):
        if request.activation_status:
            bot.activate_xbots()
        else:
            bot.deactivate_xbots()
        response.activation_status = request.activation_status
        return response

    def callback_levitation_xbot(self, request, response):
        bot.levitate_xbot_command(request.xbot_id, int(request.levitation))
        response.levitation = request.levitation
        return response

    def startup_connection(self):
        self.get_logger().info("Mover Node Started")
        self.get_logger().info("Connecting to PMC...")
        success = False
        while not success:
            success = sys.connect_to_pmc("192.168.10.100")
        self.get_logger().info("Connected")
        bot.activate_xbots()
        self.get_logger().info("XBot Activated")


def main(args=None):
    rclpy.init(args=args)   
    node = MoverServiceNode()   
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