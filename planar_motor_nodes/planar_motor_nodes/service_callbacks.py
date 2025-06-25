import math
import time
from typing import List, Optional, Tuple
from enum import Enum

from .pmclib_loader import bot, get_pmclib_status
from .position_utils import MotionStatus


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
        """Handle linear motion requests with XBot status monitoring."""
        try:
            # 1. Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # 2. Convert and validate position
            target_position = [request.x_pos / 1000.0, request.y_pos / 1000.0]

            if not self.pos_utils.validate_target_position(target_position[0], target_position[1], 0.001):
                response.success = False
                response.status_message = "Position outside valid bounds"
                return response

            self.node._log_debug(
                f"Linear motion for XBot {request.xbot_id} to {target_position}")

            # 3. Get speed parameters
            speed_params = self.node._get_speed_params(request.xbot_id)

            # 4. Execute motion command
            try:
                travel_time = bot.linear_motion_si(
                    request.xbot_id,
                    target_position[0],
                    target_position[1],
                    speed_params['xy_vel'],
                    speed_params['xy_max_accel']
                )

                self.node._log_debug(
                    f"Linear motion estimated travel time: {travel_time:.2f}s")

            except Exception as motion_error:
                self.node.get_logger().error(
                    f"❌ Linear motion execution failed: {motion_error}")
                response.success = False
                response.status_message = f"Motion command failed: {str(motion_error)}"
                return response

            # 5. Wait for completion using XBot status
            target_position_6dof = target_position + \
                [0.001, 0.0, 0.0, 0.0]  # Add Z and rotations
            timeout = max(travel_time * 1.5 + 3.0, 5.0)  # Generous timeout

            motion_result = self.pos_utils.wait_for_motion_completion(
                request.xbot_id,
                target_position_6dof,
                self.node.xy_tolerance,
                timeout
            )

            # 6. Prepare response based on motion result
            success = motion_result == MotionStatus.COMPLETED

            if success:
                response.success = True
                response.status_message = (
                    f"Linear motion completed successfully to ({target_position[0]:.4f}, {target_position[1]:.4f})m. "
                    f"XBot {request.xbot_id} is now IDLE."
                )
            else:
                response.success = False
                if motion_result == MotionStatus.TIMEOUT:
                    response.status_message = f"Motion timeout after {timeout:.1f}s. XBot may still be moving."
                elif motion_result == MotionStatus.ERROR:
                    response.status_message = "Motion failed - XBot reports error state."
                else:
                    response.status_message = f"Motion incomplete - XBot status: {motion_result.value}"

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    def callback_six_d_motion(self, request, response):
        """Handle 6-DOF motion requests with enhanced XBot status monitoring."""
        try:
            # 1. Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # 2. Get current position for smart fallback
            current_position = self.pos_utils.get_current_position(
                request.xbot_id)
            if current_position is None:
                response.success = False
                response.status_message = "Failed to get current XBot position"
                return response

            # 3. Process and validate input
            target_position_raw = self._process_6dof_input(
                request, current_position)
            validated_position = self._validate_6dof_position(
                target_position_raw, current_position, request.xbot_id)

            if validated_position is None:
                response.success = False
                response.status_message = "Position validation failed - out of bounds or unsafe"
                return response

            # 4. Get speed parameters
            speed_params = self.node._get_speed_params(request.xbot_id)

            # 5. Log motion details
            self.node._log_debug(
                f"6DOF motion for XBot {request.xbot_id}:\n"
                f"  Target: ({validated_position[0]:.4f}, {validated_position[1]:.4f}, {validated_position[2]:.4f})m\n"
                f"  Rotation: ({math.degrees(validated_position[3]):.1f}°, {math.degrees(validated_position[4]):.1f}°, {math.degrees(validated_position[5]):.1f}°)"
            )

            # 6. Execute 6DOF motion
            try:
                travel_time = bot.six_d_of_motion_si(
                    request.xbot_id,
                    validated_position[0], validated_position[1], validated_position[2],
                    validated_position[3], validated_position[4], validated_position[5],
                    speed_params['xy_vel'], speed_params['xy_max_accel'],
                    speed_params['z_vel'], speed_params['rx_vel'],
                    speed_params['ry_vel'], speed_params['rz_vel']
                )

                self.node._log_debug(
                    f"6DOF motion estimated travel time: {travel_time:.2f}s")

            except Exception as motion_error:
                self.node.get_logger().error(
                    f"❌ 6DOF motion execution failed: {motion_error}")
                response.success = False
                response.status_message = f"Motion execution failed: {str(motion_error)}"
                return response

            # 7. Wait for completion using XBot status monitoring
            # More time for complex 6DOF motions
            timeout = max(travel_time * 1.5 + 5.0, 8.0)

            motion_result = self.pos_utils.wait_for_motion_completion(
                request.xbot_id,
                validated_position,
                self.node.six_d_tolerance,
                timeout
            )

            # 8. Prepare comprehensive response
            success = motion_result == MotionStatus.COMPLETED

            if success:
                response.success = True
                response.status_message = (
                    f"6DOF motion completed successfully. "
                    f"Position: ({validated_position[0]:.4f}, {validated_position[1]:.4f}, {validated_position[2]:.4f})m, "
                    f"Rotation: ({math.degrees(validated_position[3]):.1f}°, {math.degrees(validated_position[4]):.1f}°, {math.degrees(validated_position[5]):.1f}°). "
                    f"XBot {request.xbot_id} is IDLE."
                )
            else:
                response.success = False
                if motion_result == MotionStatus.TIMEOUT:
                    response.status_message = (
                        f"6DOF motion timeout after {timeout:.1f}s. "
                        f"XBot may still be moving or position not reached within tolerance."
                    )
                elif motion_result == MotionStatus.ERROR:
                    response.status_message = "6DOF motion failed - XBot reports error state. Check XBot status."
                else:
                    response.status_message = f"6DOF motion incomplete - XBot status: {motion_result.value}"

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
        """Enhanced stop motion with status verification."""
        try:
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # Execute stop command
            bot.stop_motion(request.xbot_id)

            # Wait for XBot to report IDLE status
            start_time = time.time()
            max_stop_wait = 2.0

            while time.time() - start_time < max_stop_wait:
                status_info = self.pos_utils.get_xbot_status_info(
                    request.xbot_id)
                if status_info:
                    motion_status = self.pos_utils._interpret_xbot_state(
                        status_info['xbot_state'])
                    if motion_status == MotionStatus.IDLE:
                        response.success = True
                        response.status_message = f"XBot {request.xbot_id} stopped successfully and is IDLE"
                        self.node.get_logger().info(
                            f"🛑 XBot {request.xbot_id} stopped and IDLE")
                        return response

                time.sleep(0.1)

            # Timeout - command sent but status unclear
            response.success = True  # Command was sent
            response.status_message = f"Stop command sent to XBot {request.xbot_id}, but IDLE status not confirmed within timeout"
            self.node.get_logger().warning(
                f"⚠️ XBot {request.xbot_id} stop command sent, status unclear")

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

    def _process_6dof_input(self, request, current_position: List[float]) -> List[float]:
        """Process and convert 6DOF input with smart defaults."""
        return [
            request.x_pos /
            1000.0 if request.x_pos != 0 else current_position[0],
            request.y_pos /
            1000.0 if request.y_pos != 0 else current_position[1],
            request.z_pos /
            1000.0 if request.z_pos != 0 else current_position[2],
            math.radians(
                request.rx_pos) if request.rx_pos != 0 else current_position[3],
            math.radians(
                request.ry_pos) if request.ry_pos != 0 else current_position[4],
            math.radians(
                request.rz_pos) if request.rz_pos != 0 else current_position[5]
        ]

    def _validate_6dof_position(self, target_pos: List[float],
                                current_pos: List[float], xbot_id: int) -> Optional[List[float]]:
        """Enhanced 6DOF position validation."""
        return self.pos_utils.constrain_position_to_bounds(current_pos, target_pos)

    def _handle_service_error(self, error: Exception, response):
        """Handle service errors consistently."""
        error_msg = f"Service error: {str(error)}"
        self.node.get_logger().error(f"❌ {error_msg}")
        response.success = False
        response.status_message = error_msg
