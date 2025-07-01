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
            
            # Debug logging for position validation
            self.node.get_logger().info(
                f"🔧 Position conversion: mm({request.x_pos}, {request.y_pos}) -> m({target_position[0]:.3f}, {target_position[1]:.3f})")
            self.node.get_logger().info(
                f"🔧 Valid bounds: x=[{self.node.x_min:.3f}, {self.node.x_max:.3f}], y=[{self.node.y_min:.3f}, {self.node.y_max:.3f}]")

            if not self.pos_utils.validate_target_position(target_position[0], target_position[1], 0.001):
                response.success = False
                response.status_message = f"Position outside valid bounds. Target: ({target_position[0]:.3f}, {target_position[1]:.3f})m, Valid: x=[{self.node.x_min:.3f}, {self.node.x_max:.3f}], y=[{self.node.y_min:.3f}, {self.node.y_max:.3f}]"
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
                    f"Linear motion estimated travel time: {travel_time:.2f}s" if travel_time else "Linear motion executed")

            except Exception as motion_error:
                self.node.get_logger().error(
                    f"❌ Linear motion execution failed: {motion_error}")
                response.success = False
                response.status_message = f"Motion command failed: {str(motion_error)}"
                return response

            # 5. Wait for completion using XBot status
            target_position_6dof = target_position + \
                [0.001, 0.0, 0.0, 0.0]  # Add Z and rotations
            timeout = max((travel_time * 1.5 + 3.0) if travel_time else 5.0, 5.0)  # Generous timeout

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
        """
        Handle 6-DOF motion requests with enhanced XBot status monitoring.
        
        Usage for position values:
        - Set to desired value (in mm for x,y,z; in degrees for rx,ry,rz) to change position
        - Set to 0 to move to exactly 0 position/rotation  
        - Set to -999999 to keep current position unchanged
        
        Examples:
        - x_pos=100, y_pos=120, z_pos=1, rx_pos=0, ry_pos=0, rz_pos=0 
          → Move to (100mm, 120mm, 1mm) with 0° rotation
        - x_pos=-999999, y_pos=-999999, z_pos=-999999, rx_pos=5, ry_pos=-999999, rz_pos=-999999
          → Keep current position, rotate only rx to 5°
        """
        try:
            # 1. Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            # 2. Get current position for smart fallback
            current_position = self.pos_utils.get_current_position(request.xbot_id)
            if current_position is None:
                # Use default safe position as fallback
                self.node.get_logger().warning(f"⚠️ Cannot get current position for XBot {request.xbot_id}, using default position")
                current_position = [0.1, 0.1, 0.001, 0.0, 0.0, 0.0]  # Safe default position

            # 3. Process and validate input
            target_position_raw = self._process_6dof_input(request, current_position)
            validated_position = self._validate_6dof_position(target_position_raw, current_position, request.xbot_id)

            if validated_position is None:
                response.success = False
                response.status_message = "Position validation failed - out of bounds or unsafe"
                return response

            # 4. Get speed parameters
            speed_params = self.node._get_speed_params(request.xbot_id)

            # 5. Log motion details (check for None values)
            try:
                self.node._log_debug(
                    f"6DOF motion for XBot {request.xbot_id}:\n"
                    f"  Target: ({validated_position[0]:.4f}, {validated_position[1]:.4f}, {validated_position[2]:.4f})m\n"
                    f"  Rotation: ({math.degrees(validated_position[3]):.1f}°, {math.degrees(validated_position[4]):.1f}°, {math.degrees(validated_position[5]):.1f}°)"
                )
            except Exception as log_error:
                self.node.get_logger().warning(f"⚠️ Logging error: {log_error}")

            # 6. Execute 6DOF motion
            try:
                self.node.get_logger().debug("🔧 Executing 6DOF motion command...")
                travel_time = bot.six_d_of_motion_si(
                    request.xbot_id,
                    validated_position[0], validated_position[1], validated_position[2],
                    validated_position[3], validated_position[4], validated_position[5],
                    speed_params['xy_vel'], speed_params['xy_max_accel'],
                    speed_params['z_vel'], speed_params['rx_vel'],
                    speed_params['ry_vel'], speed_params['rz_vel']
                )

                self.node.get_logger().debug(f"🔧 travel_time result: {travel_time} (type: {type(travel_time)})")
                self.node._log_debug(f"6DOF motion estimated travel time: {travel_time:.2f}s" if travel_time else "6DOF motion executed")

            except Exception as motion_error:
                self.node.get_logger().error(f"❌ 6DOF motion execution failed: {motion_error}")
                response.success = False
                response.status_message = f"Motion execution failed: {str(motion_error)}"
                return response

            # 7. Wait for completion using XBot status monitoring
            # More time for complex 6DOF motions
            timeout = max(travel_time * 1.5 + 5.0, 8.0) if travel_time else 10.0

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
        """Handle levitation control for all XBots."""
        try:
            # Import the LevitateOptions enum from PMCLib
            from .pmclib_loader import pmc_types
            
            # This service controls levitation for ALL XBots, not a specific one
            # Use xbot_id = 0 to indicate all XBots
            xbot_id = 0  # All XBots
            
            # Use the proper enum if available, otherwise fallback to int
            if hasattr(pmc_types, 'LevitateOptions'):
                lev_mode = pmc_types.LevitateOptions.LEVITATE if request.levitation else pmc_types.LevitateOptions.LAND
            else:
                lev_mode = 1 if request.levitation else 0
            
            # Apply levitation command to all XBots
            bot.levitation_command(xbot_id, lev_mode)

            response.success = True
            response.levitation = request.levitation
            status = "levitated" if request.levitation else "landed"
            response.status_message = f"All XBots {status} successfully"

            self.node.get_logger().info(
                f"✅ All XBots {status} successfully")

        except Exception as e:
            self._handle_service_error(e, response)
            response.levitation = False

        return response

    def callback_rotary_motion(self, request, response):
        """Handle rotary motion with XBot status monitoring."""
        try:
            # Validate XBot ID
            if not self.pos_utils.validate_xbot_id(request.xbot_id):
                response.success = False
                response.status_message = "Invalid XBot ID"
                return response

            target_rz_rad = math.radians(request.target_rz)

            self.node._log_debug(
                f"Rotary motion for XBot {request.xbot_id} to {request.target_rz}°")

            # Get current position for motion monitoring
            current_position = self.pos_utils.get_current_position(request.xbot_id)
            if current_position is None:
                response.success = False
                response.status_message = "Failed to get current XBot position"
                return response

            # Execute rotary motion
            try:
                travel_time = bot.rotary_motion(
                    request.xbot_id,
                    target_rz_rad / 10,  # PMC specific scaling
                    request.max_rz_speed,
                    request.max_accel_rz
                )

                self.node._log_debug(
                    f"Rotary motion estimated travel time: {travel_time:.2f}s" if travel_time else "Rotary motion executed")

            except Exception as motion_error:
                self.node.get_logger().error(
                    f"❌ Rotary motion execution failed: {motion_error}")
                response.success = False
                response.status_message = f"Motion command failed: {str(motion_error)}"
                return response

            # Prepare target position for monitoring (only rotation changes)
            target_position = current_position.copy()
            target_position[5] = target_rz_rad  # Update RZ position

            # Wait for completion
            timeout = max((travel_time * 1.5 + 2.0) if travel_time else 4.0, 4.0)  # Generous timeout for rotation
            motion_result = self.pos_utils.wait_for_motion_completion(
                request.xbot_id,
                target_position,
                self.node.six_d_tolerance,  # Use rotation tolerance
                timeout
            )

            # Prepare response based on motion result
            success = motion_result == MotionStatus.COMPLETED

            if success:
                response.success = True
                response.status_message = (
                    f"Rotary motion completed successfully to {request.target_rz}°. "
                    f"XBot {request.xbot_id} is now IDLE."
                )
            else:
                response.success = False
                if motion_result == MotionStatus.TIMEOUT:
                    response.status_message = f"Rotary motion timeout after {timeout:.1f}s. XBot may still be moving."
                elif motion_result == MotionStatus.ERROR:
                    response.status_message = "Rotary motion failed - XBot reports error state."
                else:
                    response.status_message = f"Rotary motion incomplete - XBot status: {motion_result.value}"

        except Exception as e:
            self._handle_service_error(e, response)

        return response

    def callback_arc_motion_target_radius(self, request, response):
        """Handle arc motion with XBot status monitoring."""
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

            # Get current position for motion monitoring
            current_position = self.pos_utils.get_current_position(request.xbot_id)
            if current_position is None:
                response.success = False
                response.status_message = "Failed to get current XBot position"
                return response

            # Execute arc motion
            try:
                travel_time = bot.arc_motion_target_radius(
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

                self.node._log_debug(
                    f"Arc motion estimated travel time: {travel_time:.2f}s" if travel_time else "Arc motion executed")

            except Exception as motion_error:
                self.node.get_logger().error(
                    f"❌ Arc motion execution failed: {motion_error}")
                response.success = False
                response.status_message = f"Motion command failed: {str(motion_error)}"
                return response

            # Prepare target position for monitoring
            target_position = current_position.copy()
            target_position[0] = x_pos_m  # Update X position
            target_position[1] = y_pos_m  # Update Y position

            # Wait for completion - arc motions can take longer
            timeout = max((travel_time * 1.5 + 3.0) if travel_time else 6.0, 6.0)
            motion_result = self.pos_utils.wait_for_motion_completion(
                request.xbot_id,
                target_position,
                self.node.xy_tolerance,
                timeout
            )

            # Prepare response based on motion result
            success = motion_result == MotionStatus.COMPLETED

            if success:
                response.success = True
                response.status_message = (
                    f"Arc motion completed successfully to ({x_pos_m:.3f}, {y_pos_m:.3f})m. "
                    f"XBot {request.xbot_id} is now IDLE."
                )
            else:
                response.success = False
                if motion_result == MotionStatus.TIMEOUT:
                    response.status_message = f"Arc motion timeout after {timeout:.1f}s. XBot may still be moving."
                elif motion_result == MotionStatus.ERROR:
                    response.status_message = "Arc motion failed - XBot reports error state."
                else:
                    response.status_message = f"Arc motion incomplete - XBot status: {motion_result.value}"

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
        try:
            if not current_position or len(current_position) < 6:
                # Use safe default position if current position unavailable
                current_position = [0.1, 0.1, 0.001, 0.0, 0.0, 0.0]
            
            # Use a special value (-999999) to indicate "no change"
            # This allows setting positions to exactly 0
            NO_CHANGE = -999999
            
            return [
                request.x_pos / 1000.0 if request.x_pos != NO_CHANGE else current_position[0],
                request.y_pos / 1000.0 if request.y_pos != NO_CHANGE else current_position[1],
                request.z_pos / 1000.0 if request.z_pos != NO_CHANGE else current_position[2],
                math.radians(request.rx_pos) if request.rx_pos != NO_CHANGE else current_position[3],
                math.radians(request.ry_pos) if request.ry_pos != NO_CHANGE else current_position[4],
                math.radians(request.rz_pos) if request.rz_pos != NO_CHANGE else current_position[5]
            ]
        except Exception as e:
            self.node.get_logger().error(f"❌ Error processing 6DOF input: {e}")
            # Return safe default position
            return [0.1, 0.1, 0.001, 0.0, 0.0, 0.0]

    def _validate_6dof_position(self, target_pos: List[float],
                                current_pos: List[float], xbot_id: int) -> Optional[List[float]]:
        """Enhanced 6DOF position validation."""
        try:
            if not target_pos or not current_pos:
                self.node.get_logger().error("❌ Invalid position data for validation")
                return None
            
            if len(target_pos) < 6 or len(current_pos) < 6:
                self.node.get_logger().error("❌ Insufficient position data (need 6 DOF)")
                return None
                
            result = self.pos_utils.constrain_position_to_bounds(current_pos, target_pos)
            return result
        except Exception as e:
            self.node.get_logger().error(f"❌ Position validation failed: {e}")
            return None

    def _handle_service_error(self, error: Exception, response):
        """Handle service errors consistently."""
        error_msg = f"Service error: {str(error)}"
        self.node.get_logger().error(f"❌ {error_msg}")
        response.success = False
        response.status_message = error_msg
