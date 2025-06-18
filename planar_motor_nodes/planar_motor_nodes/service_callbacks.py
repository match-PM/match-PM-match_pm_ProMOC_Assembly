import math
import time
from typing import List

from .pmclib_loader import bot, get_pmclib_status


class ServiceCallbacks:
    """Alle ROS Service Callback-Funktionen für den Mover Node"""

    def __init__(self, node, position_utils):
        self.node = node
        self.pos_utils = position_utils

        pmclib_status = get_pmclib_status()
        self.node.get_logger().info(
            f"🔧 Using PMCLib: {pmclib_status['source']}")
        if pmclib_status['is_mock']:
            self.node.get_logger().warning("⚠️ Running in MOCK mode!")

    def callback_linear_motion_si(self, request, response):
        """Handle linear motion requests."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # Convert mm to meters
            target_position = [request.x_pos / 1000.0, request.y_pos / 1000.0]

            # Validate position bounds
            if not self.pos_utils.validate_target_position(target_position[0], target_position[1], 0.001):
                response.success = False
                response.status_message = "Position outside valid bounds"
                return response

            self.node._log_debug(
                f"Linear motion for XBot {request.xbot_id} to {target_position}")

            # Get speed parameters
            speed_params = self.node._get_speed_params(request.xbot_id)

            # Execute motion
            bot.linear_motion_si(
                request.xbot_id,
                *target_position,
                speed_params['xy_vel'],
                speed_params['xy_max_accel']
            )

            # Wait for completion
            success = self.pos_utils.check_position_reached(
                target_position + [0.0, 0.0, 0.0, 0.0],  # Extend to 6DOF
                self.node.xy_tolerance,
                max_wait_time=2.0,
                xbot_id=request.xbot_id
            )

            response.success = success
            response.status_message = (
                f"Successfully moved to {target_position}" if success
                else "Failed to reach target position within timeout"
            )

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    def callback_six_d_motion(self, request, response):
        """Handle 6-DOF motion requests."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # Get current position for fallback values
            current_position = self.pos_utils.get_current_position(
                request.xbot_id)

            # Convert positions from mm/degrees to m/radians
            target_position_raw = [
                request.x_pos / 1000.0,      # mm to m
                request.y_pos / 1000.0,      # mm to m
                request.z_pos / 1000.0,      # mm to m
                # degrees to rad
                math.radians(
                    request.rx_pos) if request.rx_pos != 0 else current_position[3],
                # degrees to rad
                math.radians(
                    request.ry_pos) if request.ry_pos != 0 else current_position[4],
                # degrees to rad
                math.radians(
                    request.rz_pos) if request.rz_pos != 0 else current_position[5]
            ]

            # Constrain to valid bounds (use current position if out of bounds)
            target_position = self.pos_utils.constrain_position_to_bounds(
                current_position, target_position_raw)

            self.node._log_debug(
                f"6DOF motion for XBot {request.xbot_id} to {target_position}")

            # Get speed parameters
            speed_params = self.node._get_speed_params(request.xbot_id)

            # Execute 6DOF motion
            bot.six_d_of_motion_si(
                request.xbot_id,
                *target_position,
                speed_params['xy_vel'],
                speed_params['xy_max_accel'],
                speed_params['z_vel'],
                speed_params['rx_vel'],
                speed_params['ry_vel'],
                speed_params['rz_vel']
            )

            # Wait for completion
            success = self.pos_utils.check_position_reached(
                target_position,
                self.node.six_d_tolerance,
                max_wait_time=3.0,  # Longer timeout for 6DOF
                xbot_id=request.xbot_id
            )

            response.success = success
            response.status_message = (
                f"Successfully moved to 6-DOF position {target_position}" if success
                else "Failed to reach target position within timeout"
            )

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    def callback_activate_xbot(self, request, response):
        """Handle XBot activation/deactivation."""
        try:
            if request.activation_status:
                bot.activate_xbots()
                self.node.get_logger().info("✅ XBots activated")
                response.status_message = "XBots successfully activated"
            else:
                bot.deactivate_xbots()
                self.node.get_logger().info("✅ XBots deactivated")
                response.status_message = "XBots successfully deactivated"

            response.success = True
            response.activation_status = request.activation_status

        except Exception as e:
            self._handle_service_error(e, response)
            response.activation_status = False

        return response

    def callback_levitation_xbot(self, request, response):
        """Handle levitation control."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.levitation = False
                response.status_message = "Invalid XBot ID"
                return response

            lev_enum = 1 if request.levitation else 0
            bot.levitation_command(request.xbot_id, int(lev_enum))

            response.success = True
            response.levitation = request.levitation
            status = "activated" if request.levitation else "deactivated"
            response.status_message = f"Levitation {status} for XBot {request.xbot_id}"

            self.node.get_logger().info(
                f"✅ Levitation {status} for XBot {request.xbot_id}")

        except Exception as e:
            self._handle_service_error(e, response)
            response.levitation = False

        return response

    def callback_rotary_motion(self, request, response):
        """Handle rotary motion."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            target_rz_rad = math.radians(request.target_rz)

            self.node._log_debug(
                f"Rotary motion for XBot {request.xbot_id} to {request.target_rz}°")

            bot.rotary_motion(
                request.xbot_id,
                target_rz_rad / 10,  # PMC specific scaling
                request.max_rz_speed,
                request.max_accel_rz
            )

            response.success = True
            response.status_message = f"Rotary motion to {request.target_rz}° executed successfully"

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    def callback_arc_motion_target_radius(self, request, response):
        """Handle arc motion."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # Convert mm to meters
            x_pos_m = request.x_pos / 1000.0
            y_pos_m = request.y_pos / 1000.0
            radius_m = request.radius_meters / 1000.0

            self.node._log_debug(
                f"Arc motion for XBot {request.xbot_id} to ({x_pos_m:.3f}, {y_pos_m:.3f})m, radius={radius_m:.3f}m")

            bot.arc_motion_target_radius(
                request.xbot_id,
                x_pos_m,
                y_pos_m,
                request.arc_type,
                request.position_mode,
                request.arc_dir,
                radius_m,
                request.xy_max_speed,
                request.xy_max_accl,
                request.final_speed
            )

            response.success = True
            response.status_message = "Arc motion executed successfully"

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    def callback_stop_motion(self, request, response):
        """Handle stop motion."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            bot.stop_motion(request.xbot_id)
            response.success = True
            response.status_message = f"Motion stopped for XBot {request.xbot_id}"

            self.node.get_logger().info(
                f"🛑 Motion stopped for XBot {request.xbot_id}")

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    def callback_set_velocity_acceleration(self, request, response):
        """Handle velocity/acceleration parameter setting."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # Validate speed parameters
            if not self._validate_speed_params(request):
                response.success = False
                response.status_message = "Invalid speed parameters"
                return response

            xbot_id = request.xbot_id

            self.node.velocity_acceleration_params[xbot_id] = {
                'xy_vel': request.xy_vel,
                'z_vel': request.z_vel,
                'rx_vel': request.rx_vel,
                'ry_vel': request.ry_vel,
                'rz_vel': request.rz_vel,
                'xy_max_accel': request.xy_max_accel,
                'z_max_accel': request.z_max_accel
            }

            self.node.get_logger().info(
                f'✅ Velocity/acceleration parameters set for XBot {xbot_id}')
            response.success = True
            response.status_message = "✅ Parameters set successfully"

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    # Helper methods
    def _validate_speed_params(self, request) -> bool:
        """Validate speed and acceleration parameters."""
        params = {
            'xy_vel': request.xy_vel,
            'z_vel': request.z_vel,
            'rx_vel': request.rx_vel,
            'ry_vel': request.ry_vel,
            'rz_vel': request.rz_vel,
            'xy_max_accel': request.xy_max_accel,
            'z_max_accel': request.z_max_accel
        }

        for name, value in params.items():
            if value < 0:
                self.node.get_logger().error(f"❌ Negative {name}: {value}")
                return False
            if value > 10.0:  # Reasonable upper limit
                self.node.get_logger().error(f"❌ {name} too high: {value}")
                return False

        return True

    def _handle_service_error(self, error: Exception, response):
        """Handle service errors consistently."""
        error_msg = f"Service error: {str(error)}"
        self.node.get_logger().error(f"❌ {error_msg}")
        response.success = False
        response.status_message = error_msg
        """Handle service errors consistently."""
        error_msg = f"Service error: {str(error)}"
        self.node.get_logger().error(f"❌ {error_msg}")
        response.success = False
        response.status_message = error_msg
