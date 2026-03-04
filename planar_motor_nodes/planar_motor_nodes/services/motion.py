"""Motion callbacks for planar motor services."""

from __future__ import annotations

from promoc_core.error_handling import handle_service_errors
from promoc_core.motion import MotionStatus
from promoc_core.motion_interface import compute_motion_timeout

from .base import PositionOutOfBoundsError, ServiceCallbacksBase
from .motion_input import (
    MotionInputConverters,
    MotionInputOptions,
    process_motion_input,
)

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


class MotionCallbacks(ServiceCallbacksBase):
    """Callbacks for motion-related services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._input_converters = MotionInputConverters(
            mm_to_m=self.mover_utils.mm_to_m,
            deg_to_rad=self.mover_utils.deg_to_rad,
        )
        self._input_options = MotionInputOptions(no_change=float(self.NO_CHANGE))

    def _process(self, request, *, motion_type: str):
        return process_motion_input(
            request,
            motion_type=motion_type,
            converters=self._input_converters,
            options=self._input_options,
            get_current_position=self.mover_utils.get_current_position,
        )

    @staticmethod
    def _timeout(
        travel_time: float | None,
        *,
        multiplier: float,
        buffer_s: float,
        min_s: float,
        fallback_s: float | None = None,
    ) -> float:
        return compute_motion_timeout(
            travel_time,
            multiplier=multiplier,
            buffer_s=buffer_s,
            min_s=min_s,
            fallback_s=fallback_s,
        )

    @handle_service_errors()
    def callback_linear_motion_si(self, request, response):
        """Execute a linear XY motion."""
        xbot_id = int(request.xbot_id)
        processed = self._process(request, motion_type="linear")
        target_pos = processed.target_position

        if not self.mover_utils.is_position_in_bounds(
            target_pos[0], target_pos[1], target_pos[2]
        ):
            raise PositionOutOfBoundsError(
                "Target position outside valid bounds",
                details={"target": target_pos[:3], "xbot_id": xbot_id},
            )

        speed_params = self.mover_utils.get_speed_params(xbot_id)
        travel_time = self.pmc.bot.linear_motion_si(
            xbot_id,
            target_pos[0],
            target_pos[1],
            speed_params["xy_vel"],
            speed_params["xy_max_accel"],
        )

        timeout = self._timeout(
            travel_time,
            multiplier=LINEAR_TIMEOUT_MULTIPLIER,
            buffer_s=LINEAR_TIMEOUT_BUFFER_S,
            min_s=LINEAR_TIMEOUT_MIN_S,
        )
        motion_status = self.mover_utils.wait_for_motion_completion(
            xbot_id,
            target_pos,
            self.config.xy_tolerance,
            timeout,
        )

        response.success = motion_status == MotionStatus.COMPLETED
        response.status_message = f"Motion status: {motion_status.name.lower()}"
        return response

    @handle_service_errors()
    def callback_six_d_motion(self, request, response):
        """Execute a 6-DOF motion (X, Y, Z, Rx, Ry, Rz)."""
        xbot_id = int(request.xbot_id)
        processed = self._process(request, motion_type="6dof")
        target_pos = processed.target_position

        if not self.mover_utils.is_position_in_bounds(
            target_pos[0], target_pos[1], target_pos[2]
        ):
            raise PositionOutOfBoundsError(
                "Target position outside valid bounds",
                details={"target": target_pos, "xbot_id": xbot_id},
            )

        speed_params = self.mover_utils.get_speed_params(xbot_id)
        travel_time = self.pmc.bot.six_d_of_motion_si(
            xbot_id,
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

        timeout = self._timeout(
            travel_time,
            multiplier=SIX_D_TIMEOUT_MULTIPLIER,
            buffer_s=SIX_D_TIMEOUT_BUFFER_S,
            min_s=SIX_D_TIMEOUT_MIN_S,
            fallback_s=SIX_D_TIMEOUT_FALLBACK_S,
        )
        motion_status = self.mover_utils.wait_for_motion_completion(
            xbot_id,
            target_pos,
            self.config.six_d_tolerance,
            timeout,
        )

        response.success = motion_status == MotionStatus.COMPLETED
        response.status_message = f"Motion status: {motion_status.name.lower()}"
        return response

    @handle_service_errors()
    def callback_rotary_motion(self, request, response):
        """Execute rotational motion around the Z axis."""
        xbot_id = int(request.xbot_id)
        processed = self._process(request, motion_type="rotary")
        target_pos = processed.target_position
        rot_mode = int(request.rot_mode)

        travel_time = self.pmc.bot.rotary_motion(
            xbot_id,
            target_pos[5],
            float(request.max_rz_speed),
            float(request.max_accel_rz),
            0,
            rot_mode,
        )

        timeout = self._timeout(
            travel_time,
            multiplier=ROTARY_TIMEOUT_MULTIPLIER,
            buffer_s=ROTARY_TIMEOUT_BUFFER_S,
            min_s=ROTARY_TIMEOUT_MIN_S,
        )
        motion_status = self.mover_utils.wait_for_motion_completion(
            xbot_id,
            target_pos,
            self.config.six_d_tolerance,
            timeout,
        )

        rot_mode_names = {0: "direct", 1: "CCW", 2: "CW"}
        response.success = motion_status == MotionStatus.COMPLETED
        response.status_message = (
            f"Rotary: {motion_status.name.lower()} "
            f"(mode: {rot_mode_names.get(rot_mode)})"
        )
        return response

    @handle_service_errors()
    def callback_arc_motion_si(self, request, response):
        """Execute arc motion with SI inputs from ROS service request."""
        xbot_id = int(request.xbot_id)
        processed = self._process(request, motion_type="arc_si")
        target_pos = processed.target_position

        target_x_m = self.mover_utils.mm_to_m(request.target_x)
        target_y_m = self.mover_utils.mm_to_m(request.target_y)
        radius_m = self.mover_utils.mm_to_m(request.radius)
        max_speed_ms = self.mover_utils.mm_to_m(request.max_speed)
        max_accel_ms2 = self.mover_utils.mm_to_m(request.max_accel)
        final_speed_ms = self.mover_utils.mm_to_m(request.final_speed)
        angle_rad = self.mover_utils.deg_to_rad(request.angle_degrees)

        travel_time = self.pmc.bot.arc_motion_si(
            xbot_id,
            target_x_m,
            target_y_m,
            radius_m,
            max_speed_ms,
            max_accel_ms2,
            0,
            int(request.arc_mode),
            int(request.arc_type),
            int(request.arc_direction),
            int(request.pos_mode),
            final_speed_ms,
            angle_rad,
        )

        timeout = self._timeout(
            travel_time,
            multiplier=ARC_TIMEOUT_MULTIPLIER,
            buffer_s=ARC_TIMEOUT_BUFFER_S,
            min_s=ARC_TIMEOUT_MIN_S,
        )
        motion_status = self.mover_utils.wait_for_motion_completion(
            xbot_id,
            target_pos,
            self.config.xy_tolerance,
            timeout,
        )

        response.success = motion_status == MotionStatus.COMPLETED
        response.status_message = f"Arc motion: {motion_status.name.lower()}"
        return response
