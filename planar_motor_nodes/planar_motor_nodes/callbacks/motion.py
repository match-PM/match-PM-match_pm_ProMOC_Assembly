"""
Motion Callbacks for Planar Motor Node.

Contains callbacks for all motion-related services:
- Linear motion (XY)
- 6-DOF motion (X, Y, Z, Rx, Ry, Rz)
- Rotary motion (Rz only)
- Arc motion
"""

from .base import ServiceCallbacksBase, MotionStatus, InvalidParameterError, PositionOutOfBoundsError
from promoc_core.promoc_exceptions import HardwareError


class MotionCallbacks(ServiceCallbacksBase):
    """Callbacks for motion-related services."""

    def callback_linear_motion_si(self, request, response):
        """
        Execute a linear XY motion.

        Service: /mover_node/linear_motion_si

        Args:
            request: LinearMotionSi with xbot_id, x_pos, y_pos (in mm).
            response: Response with success and status_message.
        """
        try:
            # Step 1: Process Input (mm → m)
            target_pos = self._process_motion_input(request, motion_type="linear")

            # Step 2: Bounds Check
            if not self.mover_utils.is_position_in_bounds(target_pos[0], target_pos[1], target_pos[2]):
                raise PositionOutOfBoundsError(
                    "Target position outside valid bounds",
                    details={'target': target_pos[:3], 'xbot_id': request.xbot_id}
                )

            # Step 3: Execute Motion
            speed_params = self.mover_utils.get_speed_params(request.xbot_id)
            travel_time = self.pmc.bot.linear_motion_si(
                request.xbot_id, target_pos[0], target_pos[1],
                speed_params['xy_vel'], speed_params['xy_max_accel']
            )

            # Step 4: Wait for Completion
            timeout = max((travel_time * 1.5 + 3.0) if travel_time else 5.0, 5.0)
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config['xy_tolerance'], timeout
            )

            # Step 5: Return Result
            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Motion status: {motion_result.value}"

        except (InvalidParameterError, PositionOutOfBoundsError) as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Linear motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_six_d_motion(self, request, response):
        """
        Execute a 6-DOF motion (X, Y, Z, Rx, Ry, Rz).

        Service: /mover_node/six_dof_motion

        Use NO_CHANGE (-999999) for any axis to keep its current position.
        """
        try:
            target_pos = self._process_motion_input(request, motion_type="6dof")

            if not self.mover_utils.is_position_in_bounds(target_pos[0], target_pos[1], target_pos[2]):
                raise PositionOutOfBoundsError(
                    "Target position outside valid bounds",
                    details={'target': target_pos, 'xbot_id': request.xbot_id}
                )

            speed_params = self.mover_utils.get_speed_params(request.xbot_id)
            travel_time = self.pmc.bot.six_d_of_motion_si(
                request.xbot_id,
                target_pos[0], target_pos[1], target_pos[2],
                target_pos[3], target_pos[4], target_pos[5],
                speed_params['xy_vel'], speed_params['xy_max_accel'],
                speed_params['z_vel'], speed_params['rx_vel'],
                speed_params['ry_vel'], speed_params['rz_vel']
            )

            timeout = max(travel_time * 1.5 + 5.0, 8.0) if travel_time else 10.0
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config['six_d_tolerance'], timeout
            )

            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Motion status: {motion_result.value}"

        except (InvalidParameterError, PositionOutOfBoundsError) as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ 6DOF motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_rotary_motion(self, request, response):
        """
        Execute a rotational motion around the Z-axis.

        Service: /mover_node/rotary_motion

        rot_mode: 0=direct, 1=CCW, 2=CW
        """
        try:
            target_pos = self._process_motion_input(request, motion_type="rotary")
            rot_mode = request.rot_mode

            travel_time = self.pmc.bot.rotary_motion(
                request.xbot_id,
                target_pos[5],  # target_rz in radians
                request.max_rz_speed,
                request.max_accel_rz,
                0,  # cmd_lb
                rot_mode
            )

            timeout = max((travel_time * 1.5 + 2.0) if travel_time else 4.0, 4.0)
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config['six_d_tolerance'], timeout
            )

            rot_mode_names = {0: "direct", 1: "CCW", 2: "CW"}
            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Rotary: {motion_result.value} (mode: {rot_mode_names.get(rot_mode)})"

        except InvalidParameterError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Rotary motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_arc_motion_si(self, request, response):
        """
        Execute an arc motion with SI units.

        Service: /mover_node/arc_motion_si
        """
        try:
            target_pos = self._process_motion_input(request, motion_type="arc_si")

            # Convert units
            target_x_m = self.mover_utils.mm_to_m(request.target_x)
            target_y_m = self.mover_utils.mm_to_m(request.target_y)
            radius_m = self.mover_utils.mm_to_m(request.radius)
            max_speed_ms = self.mover_utils.mm_to_m(request.max_speed)
            max_accel_ms2 = self.mover_utils.mm_to_m(request.max_accel)
            final_speed_ms = self.mover_utils.mm_to_m(request.final_speed)
            angle_rad = self.mover_utils.deg_to_rad(request.angle_degrees)

            travel_time = self.pmc.bot.arc_motion_si(
                request.xbot_id,
                target_x_m, target_y_m, radius_m,
                max_speed_ms, max_accel_ms2,
                0,  # cmd_lb
                request.arc_mode, request.arc_type,
                request.arc_direction, request.pos_mode,
                final_speed_ms, angle_rad
            )

            timeout = max((travel_time * 1.8 + 5.0) if travel_time else 8.0, 8.0)
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config['xy_tolerance'], timeout
            )

            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Arc motion: {motion_result.value}"

        except (InvalidParameterError, PositionOutOfBoundsError) as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Arc motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response
