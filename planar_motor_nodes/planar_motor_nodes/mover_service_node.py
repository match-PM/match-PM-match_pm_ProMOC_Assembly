import rclpy
from rclpy.node import Node
from pmclib import system_commands as sys   # PMC System related commands
from pmclib import xbot_commands as bot     # PMC Mover related commands
from pmclib import pmc_types                # PMC API Types

from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import LinearMotionSi
from promoc_assembly_interfaces.srv import SixDofMotion
from promoc_assembly_interfaces.srv import ActivateXbots
from promoc_assembly_interfaces.srv import LevitationXbots

import time

class MoverServiceNode(Node): 
    def __init__(self):
        super().__init__("mover_node")
        self.xbot_id = 1
        # Initialize simulation variables (default values for positions)
        self.sim_x_pos = 120.0  # Simulated X position (in meters)
        self.sim_y_pos = 120.0  # Simulated Y position (in meters)
        self.sim_z_pos = 1.5    # Simulated Z position (in meters)
        self.sim_rx_pos = 0.0   # Simulated rotation around X-axis (in radians)
        self.sim_ry_pos = 0.0   # Simulated rotation around Y-axis (in radians)
        self.sim_rz_pos = 0.0   # Simulated rotation around Z-axis (in radians)

        # Declare the 'use_simulation_mode' parameter (set to False by default)
        self.declare_parameter('use_simulation_mode', False)
        self.use_simulation_mode = self.get_parameter('use_simulation_mode').get_parameter_value().bool_value

        # Publisher to publish XBot information (position, rotation)
        self.xbot_pos_publisher_ = self.create_publisher(XBotInfo, "xbot_info", 10)

        # Define service callbacks for handling motions and commands
        self.linear_movement_server = self.create_service(LinearMotionSi, f"{self.get_name()}/linear_mover_motion", self.callback_linear_motion_si)
        self.six_d_movement_server = self.create_service(SixDofMotion, f"{self.get_name()}/six_d_mover_motion", self.callback_six_d_motion)
        self.xbot_activation_server = self.create_service(ActivateXbots, f"{self.get_name()}/activate_xbots", self.callback_activate_xbot)
        self.xbot_levitation_server = self.create_service(LevitationXbots, f"{self.get_name()}/levitation_xbots", self.callback_levitation_xbot)

        # Timer to periodically publish XBot position
        self.xbot_position_timer = self.create_timer(0.1, self.xbot_postition_publisher)
        
        # Initialize connection to PMC and XBot
        self.startup_connection()

    def xbot_postition_publisher(self):
        
        # Periodically publishes the XBot position.
        # In simulation mode, it uses simulated values; otherwise, it fetches real data from the XBot.
        
        msg = XBotInfo()
        
        if self.use_simulation_mode:
            # In simulation mode, use the simulated position values
            msg.x_pos = self.sim_x_pos
            msg.y_pos = self.sim_y_pos
            msg.z_pos = self.sim_z_pos
            msg.rx_pos = self.sim_rx_pos
            msg.ry_pos = self.sim_ry_pos
            msg.rz_pos = self.sim_rz_pos
        else:
            # In real mode, fetch the actual position data from the XBot
            xbot_data_list = bot.get_all_xbot_info(0)
            msg.x_pos = float(xbot_data_list[0].x_pos)
            msg.y_pos = float(xbot_data_list[0].y_pos)
            msg.z_pos = float(xbot_data_list[0].z_pos)
            msg.rx_pos = float(xbot_data_list[0].rx_pos)
            msg.ry_pos = float(xbot_data_list[0].ry_pos)
            msg.rz_pos = float(xbot_data_list[0].rz_pos)
        
        # Publish the XBot position message
        self.xbot_pos_publisher_.publish(msg)

    def callback_linear_motion_si(self, request, response):
        
        # Service callback for handling linear motion requests.
        # Updates XBot position in simulation mode or sends commands in real mode.
        
        if self.use_simulation_mode:
            self.get_logger().info("Running in simulation mode. Simulating linear motion.")
            # In simulation mode, simulate motion by updating position
            self.sim_x_pos = request.x_pos / 1000  # Convert from mm to meters
            self.sim_y_pos = request.y_pos / 1000
            response.finished = True
        else:
            # In real mode, send the linear motion command to the XBot
            xbot_id = request.xbot_id
            x_pos = request.x_pos  
            y_pos = request.y_pos
            xy_max_speed = request.xy_max_speed
            xy_max_accl = request.xy_max_accl

            # Execute the linear motion command
            travel_time_sec = bot.linear_motion_si(xbot_id, x_pos/1000, y_pos/1000, xy_max_speed, xy_max_accl)
            
            # Set the response based on whether the motion was successful
            if travel_time_sec > 0.0:
                response.finished = True
            else:
                response.finished = False
            
        return response

    def callback_six_d_motion(self, request, response):
        
        # Service callback for handling 6D motion requests.
        # Updates XBot position in simulation mode or sends commands in real mode.
        
        if self.use_simulation_mode:
            self.get_logger().info("Running in simulation mode. Simulating 6D motion.")
            # In simulation mode, simulate motion by updating all 6D position values
            self.sim_x_pos = request.x_pos / 1000  # Convert from mm to meters
            self.sim_y_pos = request.y_pos / 1000
            self.sim_z_pos = request.z_pos / 1000
            self.sim_rx_pos = request.rx_pos / 1000
            self.sim_ry_pos = request.ry_pos / 1000
            self.sim_rz_pos = request.rz_pos / 1000
            response.finished = True
            
        else:
            # In real mode, send the 6D motion command to the XBot
            xbot_id = 1
            x_pos = request.x_pos  
            y_pos = request.y_pos
            z_pos = request.z_pos
            rx_pos = request.rx_pos
            ry_pos = request.ry_pos
            rz_pos = request.rz_pos
            xy_max_speed = request.xy_max_speed
            xy_max_accl = request.xy_max_accl
            z_max_speed = request.z_max_speed
            rx_max_speed = request.rx_max_speed
            ry_max_speed = request.ry_max_speed
            rz_max_speed = request.rz_max_speed

            # Execute the 6D motion command
            bot.six_d_of_motion_si(xbot_id, x_pos/1000, y_pos/1000, z_pos/1000, rx_pos/1000, ry_pos/1000, rz_pos/1000, 
                                    xy_max_speed, xy_max_accl, z_max_speed, rx_max_speed, ry_max_speed, rz_max_speed)

            response.finished = True

        return response

    def callback_activate_xbot(self, request, response):
        
        # Service callback for activating or deactivating the XBot.
        # Skips the activation process in simulation mode.
        
        if self.use_simulation_mode:
            self.get_logger().info("Running in simulation mode. Skipping XBot activation.")
            response.activation_status = True if request.activation_status else False
        else:
            # In real mode, activate or deactivate the XBot
            if request.activation_status:
                bot.activate_xbots()
                response.activation_status = True 
            else:
                bot.deactivate_xbots()
                response.activation_status = False

        return response

    def callback_levitation_xbot(self, request, response):

        # Service callback for levitating or landing the XBot.
        # Skips levitation in simulation mode.

        xbot_id = request.xbot_id
        if self.use_simulation_mode:
            self.get_logger().info("Running in simulation mode. Skipping levitation command.")
            response.levitation = True if request.levitation else False
        else:
            if request.levitation:
                bot.match_levitate_xbot_command(xbot_id)
                response.levitation = True
            else:
                bot.match_land_xbot_command(xbot_id)
                response.levitation = False

        return response
    
    def startup_connection(self):
        
        # Initializes the connection to the PMC system and activates the XBot if not in simulation mode.
        
        if not self.use_simulation_mode:
            # In real mode, connect to PMC and activate the XBot
            self.get_logger().info("Mover Node Started")
            self.get_logger().info("Connecting to PMC...")
            input_id = 1
            success = False

            while not success:
                success = sys.connect_to_pmc("192.168.10.100")
            self.get_logger().info("Connected")

            # Activate the XBot system
            bot.activate_xbots()
            self.get_logger().info("XBot Activated")

            # Wait for PMC to achieve full control (timeout after 60 seconds)
            max_time = time.time() + 60
            while sys.get_pmc_status() is not pmc_types.PmcStatus.PMC_FULLCTRL:
                time.sleep(0.5)
                if time.time() > max_time:
                    raise TimeoutError("PMC Activation timeout")
        else:
            # In simulation mode, no actual connection to PMC is made
            self.get_logger().info("Simulated Mover Node Started")
            self.get_logger().info("No actual connection to the PMC")

def main(args=None):
    """
    Initializes the ROS2 node and starts spinning to handle services and callbacks.
    """
    rclpy.init(args=args)   
    node = MoverServiceNode()   
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure that the cleanup function is called when the node shuts down
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()

# %%
