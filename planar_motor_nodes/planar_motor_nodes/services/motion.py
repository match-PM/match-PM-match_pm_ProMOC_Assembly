"""
Motion Callbacks for Planar Motor Node.

Contains callbacks for all motion-related services:
- Linear motion (XY)
- 6-DOF motion (X, Y, Z, Rx, Ry, Rz)
- Rotary motion (Rz only)
- Arc motion
"""

from .base import ServiceCallbacksBase, PositionOutOfBoundsError
from promoc_core.motion import MotionStatus
from promoc_core.error_handling import handle_service_errors

LINEAR_TIMEOUT_MULTIPLIER = 1.5
LINEAR_TIMEOUT_BUFFER_S = 3.0
LINEAR_TIMEOUT_MIN_S = 5.0

SIX_D_TIMEOUT_MULTIPLIER = 1.5
SIX_D_TIMEOUT_BUFFER_S = 5.0
SIX_D_TIMEOUT_MIN_S = 8.0
SIX_D_TIMEOUT_FALLBACK_S = 10.0

ROTARY_TIMEOUT_MULTIPLIER = 1.5
ROTARY_TIMEOUT_BUFFER_S = 2.0
ROTARY_TIMEOUT_MIN_S = 4.0

ARC_TIMEOUT_MULTIPLIER = 1.8
ARC_TIMEOUT_BUFFER_S = 5.0
ARC_TIMEOUT_MIN_S = 8.0


def _motion_timeout(
    travel_time: float | None,
    multiplier: float = 1.5,
    buffer_s: float = 3.0,
    min_s: float = 5.0,
    fallback_s: float | None = None,
) -> float:
    """Compute motion timeout with consistent formula and fallback."""
    if travel_time:
        return max((travel_time * multiplier) + buffer_s, min_s)
    return float(min_s if fallback_s is None else fallback_s)


class MotionCallbacks(ServiceCallbacksBase):
    """Callbacks for motion-related services."""

    @handle_service_errors()
    def callback_linear_motion_si(self, request, response):
        """
        Execute a linear XY motion.

        Service: /promoc/mover/linear_motion_si (legacy: /mover_node/linear_motion_si)

        Args:
            request: LinearMotionSi with xbot_id, x_pos, y_pos (in mm).
            response: Response with success and status_message.
        """
        # Step 1: Process Input (mm → m)
        target_pos = self._process_motion_input(request, motion_type="linear")

        # Step 2: Bounds Check
        if not self.mover_utils.is_position_in_bounds(
            target_pos[0], target_pos[1], target_pos[2]
        ):
            raise PositionOutOfBoundsError(
                "Target position outside valid bounds",
                details={"target": target_pos[:3], "xbot_id": request.xbot_id},
            )

        # Step 3: Execute Motion
        speed_params = self.mover_utils.get_speed_params(request.xbot_id)
        travel_time = self.pmc.bot.linear_motion_si(
            request.xbot_id,
            target_pos[0],
            target_pos[1],
            speed_params["xy_vel"],
            speed_params["xy_max_accel"],
        )

        # Step 4: Wait for Completion
        timeout = _motion_timeout(
            travel_time=travel_time,
            multiplier=LINEAR_TIMEOUT_MULTIPLIER,
            buffer_s=LINEAR_TIMEOUT_BUFFER_S,
            min_s=LINEAR_TIMEOUT_MIN_S,
        )
        motion_result = self.mover_utils.wait_for_motion_completion(
            request.xbot_id, target_pos, self.config.xy_tolerance, timeout
        )

        # Step 5: Return Result
        response.success = motion_result == MotionStatus.COMPLETED
        response.status_message = f"Motion status: {motion_result.value}"

        return response

    @handle_service_errors()
    def callback_six_d_motion(self, request, response):
        """
        Execute a 6-DOF motion (X, Y, Z, Rx, Ry, Rz).

        Service: /promoc/mover/six_dof_motion (legacy: /mover_node/six_dof_motion)

        Use NO_CHANGE (-999999) for any axis to keep its current position.
        """
        target_pos = self._process_motion_input(request, motion_type="6dof")

        if not self.mover_utils.is_position_in_bounds(
            target_pos[0], target_pos[1], target_pos[2]
        ):
            raise PositionOutOfBoundsError(
                "Target position outside valid bounds",
                details={"target": target_pos, "xbot_id": request.xbot_id},
            )

        speed_params = self.mover_utils.get_speed_params(request.xbot_id)
        travel_time = self.pmc.bot.six_d_of_motion_si(
            request.xbot_id,
            target_pos[0],
            target_pos[1],
            target_pos[2],
            target_pos[3],
            target_pos[4],
            target_pos[5],
            speed_params["xy_vel"],
            speed_params["xy_max_accel"],
            speed_params["z_vel"],
            speed_params["rx_vel"],
            speed_params["ry_vel"],
            speed_params["rz_vel"],
        )

        timeout = _motion_timeout(
            travel_time=travel_time,
            multiplier=SIX_D_TIMEOUT_MULTIPLIER,
            buffer_s=SIX_D_TIMEOUT_BUFFER_S,
            min_s=SIX_D_TIMEOUT_MIN_S,
            fallback_s=SIX_D_TIMEOUT_FALLBACK_S,
        )
        motion_result = self.mover_utils.wait_for_motion_completion(
            request.xbot_id, target_pos, self.config.six_d_tolerance, timeout
        )

        response.success = motion_result == MotionStatus.COMPLETED
        response.status_message = f"Motion status: {motion_result.value}"

        return response

    @handle_service_errors()
    def callback_rotary_motion(self, request, response):
        """
        Execute a rotational motion around the Z-axis.

        Service: /promoc/mover/rotary_motion (legacy: /mover_node/rotary_motion)

        rot_mode: 0=direct, 1=CCW, 2=CW
        """
        target_pos = self._process_motion_input(request, motion_type="rotary")
        rot_mode = request.rot_mode

        travel_time = self.pmc.bot.rotary_motion(
            request.xbot_id,
            target_pos[5],  # target_rz in radians
            request.max_rz_speed,
            request.max_accel_rz,
            0,  # cmd_lb
            rot_mode,
        )

        timeout = _motion_timeout(
            travel_time=travel_time,
            multiplier=ROTARY_TIMEOUT_MULTIPLIER,
            buffer_s=ROTARY_TIMEOUT_BUFFER_S,
            min_s=ROTARY_TIMEOUT_MIN_S,
        )
        motion_result = self.mover_utils.wait_for_motion_completion(
            request.xbot_id, target_pos, self.config.six_d_tolerance, timeout
        )

        rot_mode_names = {0: "direct", 1: "CCW", 2: "CW"}
        response.success = motion_result == MotionStatus.COMPLETED
        response.status_message = (
            f"Rotary: {motion_result.value} (mode: {rot_mode_names.get(rot_mode)})"
        )

        return response

    @handle_service_errors()
    def callback_arc_motion_si(self, request, response):
        """
        Execute an arc motion with SI units.

        Service: /promoc/mover/arc_motion_si (legacy: /mover_node/arc_motion_si)
        """
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
            target_x_m,
            target_y_m,
            radius_m,
            max_speed_ms,
            max_accel_ms2,
            0,  # cmd_lb
            request.arc_mode,
            request.arc_type,
            request.arc_direction,
            request.pos_mode,
            final_speed_ms,
            angle_rad,
        )

        timeout = _motion_timeout(
            travel_time=travel_time,
            multiplier=ARC_TIMEOUT_MULTIPLIER,
            buffer_s=ARC_TIMEOUT_BUFFER_S,
            min_s=ARC_TIMEOUT_MIN_S,
        )
        motion_result = self.mover_utils.wait_for_motion_completion(
            request.xbot_id, target_pos, self.config.xy_tolerance, timeout
        )

        response.success = motion_result == MotionStatus.COMPLETED
        response.status_message = f"Arc motion: {motion_result.value}"

        return response
