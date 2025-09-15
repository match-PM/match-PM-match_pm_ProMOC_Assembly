import math
from .mover_pmc_interface import PmcInterface
from .mover_position_utils import PositionUtils, MotionStatus
from .mover_node_config import NodeConfig


class ServiceCallbacks:
    """
    Handles all ROS service callback logic, decoupled from the ROS node.
    It contains the business logic for motion commands and other services.
    """

    def __init__(self, logger, pmc_interface: PmcInterface, pos_utils: PositionUtils, config: NodeConfig):
        """
        Initializes the callbacks with explicit dependencies.

        Args:
            logger: The ROS 2 logger instance.
            pmc_interface: The interface to the hardware library.
            pos_utils: The utility class for position calculations.
            config: The dataclass holding all node parameters.
        """
        self.logger = logger
        self.pmc = pmc_interface
        self.pos_utils = pos_utils
        self.config = config

        # Velocity parameters are now managed here, not in the node.
        self.velocity_params = {}
        self.standard_velocity_params = {
            'xy_vel': 1.00, 'z_vel': 0.10, 'rx_vel': 0.10, 'ry_vel': 0.10,
            'rz_vel': 0.10, 'xy_max_accel': 5.00, 'z_max_accel': 1.00
        }
        self.logger.info(f"🔧 ServiceCallbacks initialized. Using PMCLib: {self.pmc.status['source']}")

    def _get_speed_params(self, xbot_id: int) -> dict:
        """Helper to get speed parameters for a specific XBot."""
        return self.velocity_params.get(xbot_id, self.standard_velocity_params)

    def _handle_service_error(self, error: Exception, response):
        """Handles service errors consistently."""
        error_msg = f"Service error: {str(error)}"
        self.logger.error(f"❌ {error_msg}")
        response.success = False
        response.status_message = error_msg
        
    def _process_6dof_input(self, request, current_position: list) -> list:
        """Process 6DOF input with a special value for 'no change'."""
        NO_CHANGE = -999999
        return [
            request.x_pos / 1000.0 if request.x_pos != NO_CHANGE else current_position[0],
            request.y_pos / 1000.0 if request.y_pos != NO_CHANGE else current_position[1],
            request.z_pos / 1000.0 if request.z_pos != NO_CHANGE else current_position[2],
            math.radians(request.rx_pos) if request.rx_pos != NO_CHANGE else current_position[3],
            math.radians(request.ry_pos) if request.ry_pos != NO_CHANGE else current_position[4],
            math.radians(request.rz_pos) if request.rz_pos != NO_CHANGE else current_position[5]
        ]

    # --- Service Callback Implementations ---

    def callback_linear_motion_si(self, request, response):
        """Handle linear motion requests with XBot status monitoring."""
        try:
            target_m = [request.x_pos / 1000.0, request.y_pos / 1000.0]

            if not self.pos_utils.is_position_in_bounds(target_m[0], target_m[1], 0.001):
                response.success = False
                response.status_message = "Position outside valid bounds."
                return response

            speed_params = self._get_speed_params(request.xbot_id)
            travel_time = self.pmc.bot.linear_motion_si(
                request.xbot_id, target_m[0], target_m[1],
                speed_params['xy_vel'], speed_params['xy_max_accel']
            )

            target_6dof = target_m + [0.001, 0.0, 0.0, 0.0]
            timeout = max((travel_time * 1.5 + 3.0) if travel_time else 5.0, 5.0)
            motion_result = self.pos_utils.wait_for_motion_completion(
                request.xbot_id, target_6dof, self.config.xy_tolerance, timeout
            )
            
            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Motion status: {motion_result.value}"
        except Exception as e:
            self._handle_service_error(e, response)
        return response

    def callback_six_d_motion(self, request, response):
        """Handle 6-DOF motion requests."""
        try:
            current_pos = self.pos_utils.get_current_position(request.xbot_id)
            if current_pos is None:
                current_pos = [0.1, 0.1, 0.001, 0.0, 0.0, 0.0] # Safe default
                self.logger.warning("Could not get current position, using safe default.")

            target_pos = self._process_6dof_input(request, current_pos)
            
            if not self.pos_utils.is_position_in_bounds(target_pos[0], target_pos[1], target_pos[2]):
                 response.success = False
                 response.status_message = "Position outside valid bounds."
                 return response

            speed_params = self._get_speed_params(request.xbot_id)
            travel_time = self.pmc.bot.six_d_of_motion_si(
                request.xbot_id,
                target_pos[0], target_pos[1], target_pos[2],
                target_pos[3], target_pos[4], target_pos[5],
                speed_params['xy_vel'], speed_params['xy_max_accel'],
                speed_params['z_vel'], speed_params['rx_vel'],
                speed_params['ry_vel'], speed_params['rz_vel']
            )

            timeout = max(travel_time * 1.5 + 5.0, 8.0) if travel_time else 10.0
            motion_result = self.pos_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config.six_d_tolerance, timeout
            )
            
            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Motion status: {motion_result.value}"
        except Exception as e:
            self._handle_service_error(e, response)
        return response

    def callback_activate_xbot(self, request, response):
        """Handle XBot activation/deactivation."""
        try:
            if request.activation_status:
                self.pmc.bot.activate_xbots()
                response.status_message = "XBots successfully activated"
            else:
                self.pmc.bot.deactivate_xbots()
                response.status_message = "XBots successfully deactivated"
            response.success = True
        except Exception as e:
            self._handle_service_error(e, response)
        return response

    def callback_levitation_xbot(self, request, response):
        """Handle XBot levitation."""
        try:
            command = 1 if request.levitation else 0
            self.pmc.bot.levitation_command(0, command) # Assumes XBot ID 0 for global command
            response.status_message = f"Levitation command sent: {'enable' if request.levitation else 'disable'}"
            response.success = True
        except Exception as e:
            self._handle_service_error(e, response)
        return response

    def callback_rotary_motion(self, request, response):
        """Handle rotary motion requests."""
        try:
            target_rz_rad = math.radians(request.target_rz)
            current_pos = self.pos_utils.get_current_position(request.xbot_id)
            if current_pos is None:
                raise ValueError("Could not get current position for rotary motion.")

            travel_time = self.pmc.bot.rotary_motion(
                request.xbot_id,
                target_rz_rad / 10,  # PMC specific scaling
                request.max_rz_speed,
                request.max_accel_rz
            )
            
            target_pos = current_pos[:]
            target_pos[5] = target_rz_rad
            timeout = max((travel_time * 1.5 + 2.0) if travel_time else 4.0, 4.0)
            motion_result = self.pos_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config.six_d_tolerance, timeout)

            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Rotary motion status: {motion_result.value}"
        except Exception as e:
            self._handle_service_error(e, response)
        return response
    
    def callback_arc_motion_target_radius(self, request, response):
        """Handle arc motion requests."""
        try:
            travel_time = self.pmc.bot.arc_motion_target_radius(
                request.xbot_id, request.x_pos / 1000.0, request.y_pos / 1000.0,
                request.arc_type, request.position_mode, request.arc_dir,
                request.radius_meters / 1000.0, request.xy_max_speed,
                request.xy_max_accl, request.final_speed
            )

            # NOTE: For simplicity, we are not waiting for completion here.
            # A full implementation would require calculating the final 6DOF target.
            response.success = True
            response.status_message = f"Arc motion initiated. Estimated time: {travel_time}s"
        except Exception as e:
            self._handle_service_error(e, response)
        return response

    def callback_stop_motion(self, request, response):
        """Handle stop motion requests."""
        try:
            self.pmc.bot.stop_motion(request.xbot_id)
            # For simplicity, we assume the command is successful.
            # A more robust version could poll the state until it's IDLE.
            response.success = True
            response.status_message = f"Stop command sent to XBot {request.xbot_id}."
        except Exception as e:
            self._handle_service_error(e, response)
        return response

    def callback_set_velocity_acceleration(self, request, response):
        """Handle velocity/acceleration parameter setting."""
        try:
            # You could add validation here to ensure values are positive etc.
            self.velocity_params[request.xbot_id] = {
                'xy_vel': request.xy_vel, 'z_vel': request.z_vel,
                'rx_vel': request.rx_vel, 'ry_vel': request.ry_vel,
                'rz_vel': request.rz_vel, 'xy_max_accel': request.xy_max_accel,
                'z_max_accel': request.z_max_accel
            }
            self.logger.info(f"✅ Velocity/acceleration parameters set for XBot {request.xbot_id}")
            response.success = True
            response.status_message = "Parameters set successfully"
        except Exception as e:
            self._handle_service_error(e, response)
        return response