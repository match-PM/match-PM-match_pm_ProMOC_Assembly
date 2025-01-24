
import sys
import os

# To use the mock_pmclib we need to add the current script's directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import rclpy
from rclpy.node import Node

try:
    from pmclib import system_commands as sys
    from pmclib import xbot_commands as bot
    from pmclib import pmc_types
except ImportError as e:
    print(f"Using mock pmclib due to import error: {e}")
    from mock_pmclib import system_commands as sys
    from mock_pmclib import xbot_commands as bot
    from mock_pmclib import pmc_types


from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import LinearMotionSi
from promoc_assembly_interfaces.srv import SixDofMotion
from promoc_assembly_interfaces.srv import ActivateXbots
from promoc_assembly_interfaces.srv import LevitationXbots
from promoc_assembly_interfaces.srv import ArcMotionTargetRadius
from promoc_assembly_interfaces.srv import StopMotion
from promoc_assembly_interfaces.srv import RotaryMotion

import time

class MoverServiceNode(Node): 
    def __init__(self):
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
            bot.linear_motion_si(request.xbot_id, request.x_pos / 1000, request.y_pos / 1000, request.xy_max_speed, request.xy_max_accl)
            response.finished = True
        except:
            self.get_logger().error("INVALID PARAMETER")
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
        try:
            bot.six_d_of_motion_si(request.xbot_id, request.x_pos / 1000, request.y_pos / 1000, request.z_pos / 1000,
                                   request.rx_pos / 1000, request.ry_pos / 1000, request.rz_pos / 1000,
                                   request.xy_max_speed, request.xy_max_accl, request.z_max_speed,
                                   request.rx_max_speed, request.ry_max_speed, request.rz_max_speed)
            response.finished = True
        except:
            self.get_logger().error("INVALID PARAMETER")
            response.finished = False
        return response

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