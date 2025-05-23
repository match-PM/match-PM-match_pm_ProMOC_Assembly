
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
from promoc_assembly_interfaces.msg import XBotInfo
import sys
import os
import time
import math

# ROS 2 imports
import rclpy
from rclpy.node import Node

# Ensure the current script's directory is in the Python path to allow local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    # Try to import from standard pmclib module
try: 
    from pmclib import system_commands as sys_cmd
    from pmclib import xbot_commands as bot
    from pmclib import pmc_types
    print("Successfully imported modules from standard pmclib")
except ImportError as e:
    #Fall back to Mock_implementation
    print(f"Using mock pmclib due to import error: {e}")
    from mock_pmclib import system_commands as sys_cmd
    from mock_pmclib import xbot_commands as bot
    from mock_pmclib import pmc_types

# Import custom message and service interfaces from promoc_assembly_interfaces


class MoverServiceNode(Node):
    def __init__(self):
        """
        Initialize the MoverServiceNode class.

        This function sets up the ROS node, creates publishers and service servers for handling motions and commands,
        initializes the connection to the PMC and XBot, and starts a timer to periodically publish XBot position.
        """

        super().__init__("mover_node")

        # Initialize core parameters
        self.initialize_parameters()

        # Setup ROS publishers and services
        self.setup_publishers()
        self.setup_services()

        # Initialize connections
        self.startup_connection()

        # Start timers
        self.setup_timers()

    # Initialization functions

    def initialize_parameters(self):

        # Initialize core parameters related to XBot and motion tolerances."""
        self.xy_tolerance = 0.1  # Tolerance for position in meters
        self.six_d_tolerance = 0.1  # Tolerance for position in meters  
        self.velocity_acceleration_params = {}
        self.velocity_acceleration_standard_params = {
            'xy_vel': 1.00,
            'z_vel': 0.10,
            'rx_vel': 0.10,
            'ry_vel': 0.10,
            'rz_vel': 0.10,
            'xy_max_accel': 5.00,
            'z_max_accel': 1.00
        }
        
        self.declare_parameter('node_name', 'mover_node')
        self.node_name = self.get_parameter('node_name').value  

        # Define the Movement Areas as ROS2 parameters with default values
        self.declare_parameter('x_min', 0.055)
        self.declare_parameter('x_max', 0.420)
        self.declare_parameter('y_min', -0.055)
        self.declare_parameter('y_max', 0.180)
        self.declare_parameter('z_min', 0.000)
        self.declare_parameter('z_max', 0.004)

        # Get parameter values
        self.x_min = self.get_parameter('x_min').value
        self.x_max = self.get_parameter('x_max').value
        self.y_min = self.get_parameter('y_min').value
        self.y_max = self.get_parameter('y_max').value
        self.z_min = self.get_parameter('z_min').value
        self.z_max = self.get_parameter('z_max').value

    def setup_publishers(self):
        """Create ROS publishers for XBot information."""
        self.xbot_pos_publisher_ = self.create_publisher(
            XBotInfo, "xbot_info", 10)

    def setup_services(self):
        """Define and create ROS services for handling motions and commands."""
        self.linear_movement_server = self.create_service(
            LinearMotionSi, f"{self.get_name()}/linear_mover_motion", self.callback_linear_motion_si
        )
        self.six_d_movement_server = self.create_service(
            SixDofMotion, f"{self.get_name()}/six_d_mover_motion", self.callback_six_d_motion
        )
        self.xbot_activation_server = self.create_service(
            ActivateXbots, f"{self.get_name()}/activate_xbots", self.callback_activate_xbot
        )
        self.xbot_levitation_server = self.create_service(
            LevitationXbots, f"{self.get_name()}/levitation_xbots", self.callback_levitation_xbot
        )
        self.xbot_arc_motion_target_radius_server = self.create_service(
            ArcMotionTargetRadius, f"{self.get_name()}/arcmotion_target_radius", self.callback_arc_motion_target_radius
        )
        self.xbot_stop_motion_server = self.create_service(
            StopMotion, f"{self.get_name()}/stop_motion", self.callback_stop_motion
        )
        self.xbot_rotary_motion_server = self.create_service(
            RotaryMotion, f"{self.get_name()}/rotary_motion", self.callback_rotary_motion
        )
        self.set_velocity_acceleration_server = self.create_service(
            SetVelocityAcceleration, f"{self.get_name()}/set_velocity_acceleration", self.callback_set_velocity_acceleration
        )

    def setup_timers(self):
        """
        Set up periodic timers for the node's recurring tasks.
        
        This function initializes timers that trigger callback functions at specified intervals.
        Currently, it creates a timer that publishes the XBot's position information every 0.1 seconds.
        
        Parameters:
            None
            
        Returns:
            None
        """
        self.xbot_position_timer = self.create_timer(
            0.1, self.xbot_postition_publisher)

    def startup_connection(self):
        self.get_logger().info("Mover Node Started")
        self.get_logger().info("Connecting to PMC...")
        success = False
        while not success:
            success = sys_cmd.connect_to_pmc("192.168.10.100")
        self.get_logger().info("Connected")
        bot.activate_xbots()
        self.get_logger().info("XBot Activated")
        # set standard values for velocities and acceleration
        self.velocity_acceleration_params = self.velocity_acceleration_standard_params.copy()

    # Timer callback functions

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
        except IndexError as e:
            pass
            #self.get_logger().error("Error: xbot_data_list is empty")

        self.xbot_pos_publisher_.publish(msg)

    # Callback functions for ROS services
    def calculate_rz_ry_max(self, mover_width:float,safety_factor:float=0.5,z_value:float=0.001)->float:
        """
        Calculate the maximum rz value based on the mover width and a safety factor.

        Parameters:
        mover_width (float): The width of the mover.
        safety_factor (float): The safety factor to be applied.

        Returns:
        float: The calculated maximum rz value.
        """
        r = (mover_width / 2) *math.sqrt(2)
        if z_value <= 0:
            return 0.0
        rz_max = math.atan(r / z_value) *safety_factor
        
        return rz_max
    

    def callback_linear_motion_si(self, request, response):
        """
        Handles a linear motion request for a specific XBot.

        This function converts the position values from millimeters to meters, executes the motion command with the
        converted positions and speed parameters, waits until the target position is reached within a specified tolerance,
        and returns a response indicating whether the motion was successfully completed.

        Parameters:
        - request (promoc_assembly_interfaces.srv.LinearMotionSI.Request): The motion request containing the XBot ID,
        target position, and maximum speed and acceleration parameters.

        - response (promoc_assembly_interfaces.srv.LinearMotionSI.Response): The response to be filled with the success status
        of the motion.

        Returns:
        - response (promoc_assembly_interfaces.srv.LinearMotionSI.Response): The response containing the success status
        of the motion.
        """
        try:

            # Convert position values from millimeters to meters
            target_position = [
                request.x_pos / 1000, request.y_pos / 1000
            ]
            self.get_logger().info(
                f"Starting linear motion for bot {request.xbot_id} to target position: {target_position}")

            # Get speed parameters for the bot
            speed_params = self.velocity_acceleration_params.get(
                request.xbot_id)
            if speed_params:
                # The * infront of targe_position unpacks the target_position list into individual parameters.
                bot.linear_motion_si(request.xbot_id, *target_position,
                                     speed_params['xy_vel'],
                                     speed_params['xy_max_accel']
                                     )
            else:
                self.get_logger().error(
                    f"Speed parameters not found for bot {request.xbot_id}")
                self.get_logger().error("Using standard speed parameters for this bot")

                # The * infront of targe_position unpacks the target_position list into individual parameters.
                bot.linear_motion_si(request.xbot_id, *target_position,
                                     self.velocity_acceleration_standard_params['xy_vel'],
                                     self.velocity_acceleration_standard_params['xy_max_accel']
                                     )

            # Wait until the target position is reached within tolerance
            position_reached = self.check_position_reached(
                target_position,
                self.get_current_position(),
                self.xy_tolerance,
                max_wait_time=2.0
            )

            response.finished = position_reached

        except ValueError as e:
            self.get_logger().error(f"Invalid parameter value: {e}")
            response.finished = False
        except KeyError as e:
            self.get_logger().error(f"Missing parameter in speed_params: {e}")
            response.finished = False
        except Exception as e:
            self.get_logger().error(f"Unexpected error: {e}")
            response.finished = False

        finally:
            return response

    def callback_arc_motion_target_radius(self, request, response):
        try:
            bot.arc_motion_target_radius(request.xbot_id, request.x_pos / 1000, request.y_pos / 1000, request.arc_type,
                                         request.position_mode, request.arc_dir, request.radius_meters / 1000,
                                         request.xy_max_speed, request.xy_max_accl, request.final_speed)
            response.finished = True
        except:
            self.get_logger().error("INVALID PARAMETER")
            response.finished = False
        return response

    def callback_rotary_motion(self, request, response):
        try:
            bot.rotary_motion(request.xbot_id, request.target_rz/1000,
                              request.max_speed, request.max_accel)
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
            current_position = self.get_current_position()
            # Konvertiere und validiere Positionswerte
            x_pos_m = request.x_pos / 1000
            y_pos_m = request.y_pos / 1000
            z_pos_m = request.z_pos / 1000
            rx_pos_m = request.rx_pos / 1000
            ry_pos_m = request.ry_pos / 1000
            rz_pos_m = request.rz_pos / 1000

            # Erstelle Zielposition mit Bereichsprüfung
            target_position = [
                x_pos_m if request.x_pos != 0 and self.x_min <= x_pos_m <= self.x_max 
                else current_position[0],
                y_pos_m if request.y_pos != 0 and self.y_min <= y_pos_m <= self.y_max 
                else current_position[1],
                z_pos_m if request.z_pos != 0 and self.z_min <= z_pos_m <= self.z_max 
                else current_position[2],
                rx_pos_m if -self.calculate_rz_ry_max(120,0.1,z_pos_m) <= rx_pos_m <= self.calculate_rz_ry_max(120,0.1,z_pos_m)
                else current_position[3],
                ry_pos_m if -self.calculate_rz_ry_max(120,0.1,z_pos_m) <= ry_pos_m <= self.calculate_rz_ry_max(120,0.1,z_pos_m)
                else current_position[4],
                rz_pos_m
            ]

            speed_params = self.velocity_acceleration_params.get(
                request.xbot_id)

            if speed_params:

                # Execute motion command with converted positions and speed parameters
                bot.six_d_of_motion_si(
                    request.xbot_id, *target_position,
                    speed_params['xy_vel'],
                    speed_params['xy_max_accel'],
                    speed_params['z_vel'],
                    speed_params['rx_vel'],
                    speed_params['ry_vel'],
                    speed_params['rz_vel']
                )
            else:
                self.get_logger().error(
                    f"Speed parameters not found for bot {request.xbot_id}")
                self.get_logger().error("Using standard speed parameters for this bot")

                # Execute motion command with converted positions and standard speed parameters
                bot.six_d_of_motion_si(
                    request.xbot_id, *target_position,
                    self.velocity_acceleration_standard_params['xy_vel'],
                    self.velocity_acceleration_standard_params['xy_max_accel'],
                    self.velocity_acceleration_standard_params['z_vel'],
                    self.velocity_acceleration_standard_params['rx_vel'],
                    self.velocity_acceleration_standard_params['ry_vel'],
                    self.velocity_acceleration_standard_params['rz_vel']
                )
            # Wait until the target position is reached within tolerance
            position_reached = self.check_position_reached(
                target_position,
                current_position,
                self.six_d_tolerance,
                max_wait_time=1.0
            )

            response.finished = position_reached

        except ValueError as e:
            self.get_logger().error(f"Invalid parameter value: {e}")
            response.finished = False
        except KeyError as e:
            self.get_logger().error(f"Missing parameter in speed_params: {e}")
            response.finished = False
        except Exception as e:
            self.get_logger().error(f"Unexpected error: {e}")
            response.finished = False

        finally:
            return response

    def callback_set_velocity_acceleration(self, request, response):
        try:
            # Extract xbot_id from the request
            xbot_id = request.xbot_id

            self.velocity_acceleration_params[xbot_id] = {
                'xy_vel': request.xy_vel,
                'z_vel': request.z_vel,
                'rx_vel': request.rx_vel,
                'ry_vel': request.ry_vel,
                'rz_vel': request.rz_vel,
                'xy_max_accel': request.xy_max_accel,
                'z_max_accel': request.z_max_accel
            }

            self.get_logger().info(
                f'Velocity and acceleration parameters set successfully for bot {xbot_id}')
            response.finished = True
        except Exception as e:
            # Log error and set response to False
            self.get_logger().error(
                f"INVALID PARAMETER for bot {xbot_id}: {e}")
            self.get_logger().error(
                "Setting velocity and acceleration to standard parameters for this bot")

            response.finished = False

        return response

    def callback_levitation_xbot(self, request, response):
        bot.levitate_xbot_command(request.xbot_id, int(request.levitation))
        response.levitation = request.levitation
        return response

    def callback_activate_xbot(self, request, response):
        if request.activation_status:
            bot.activate_xbots()
        else:
            bot.deactivate_xbots()
        response.activation_status = request.activation_status
        return response

    # Helper functions

    def get_current_position(self) -> list:
        try:
            xbot_data_list = bot.get_all_xbot_info(0)
            current_position = [float(xbot_data_list[0].x_pos), float(xbot_data_list[0].y_pos), float(xbot_data_list[0].z_pos),
                                float(xbot_data_list[0].rx_pos), float(xbot_data_list[0].ry_pos), float(xbot_data_list[0].rz_pos)]
            return current_position
        except IndexError:
            self.get_logger().error("Error: xbot_data_list is empty")
            return [0, 0, 0, 0, 0, 0]

    def check_position_reached(self, target_position: list, current_position: list, tolerance: float = 0.1, max_wait_time: float = 2.0) -> bool:
        """
        Check if the current position has reached the target position within a specified tolerance.
        Optionally wait until the position is reached or timeout occurs.
    
        Parameters:
        target_position (list): A list of float values representing the target position.
        current_position (list): A list of float values representing the current position.
        tolerance (float): The maximum allowed difference between corresponding components
                        of the target and current positions.
        max_wait_time (float): Maximum time to wait in seconds.
    
        Returns:
        bool: True if all components of the current position are within the specified tolerance
            of the corresponding components in the target position, False otherwise.
        """
        # Function to check if position is within tolerance
        def is_within_tolerance():
            for i in range(min(len(target_position), len(current_position))):
                if abs(target_position[i] - current_position[i]) > tolerance:
                    return False
            return True
    
        # Wait until position is reached or timeout
        start_time = time.time()
        check_interval = 0.1  # Check every 0.1 seconds
        
        while not is_within_tolerance():
            if time.time() - start_time > max_wait_time:
                self.get_logger().warning(
                    f"Timeout erreicht! Zielposition möglicherweise nicht erreichbar: {target_position}")
                return False
    
            time.sleep(check_interval)  # Fixed: removed keyword argument
            # Update current position
            current_position = self.get_current_position()
    
        return True
        
    def destroy_node(self):
        self.get_logger().info("Shutting down MoverServiceNode")
        try:
            self.get_logger().info("Deactivating XBot")
            bot.deactivate_xbots()
            self.get_logger().info("XBot deactivated Successfully")
        except Exception as e:
            self.get_logger().error(f"Error deactivating XBot: {e}")
        finally:
            super().destroy_node()


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
