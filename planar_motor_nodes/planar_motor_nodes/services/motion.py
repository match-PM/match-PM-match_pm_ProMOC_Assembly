"""Motion callbacks for planar motor services."""

from __future__ import annotations

from promoc_core import error_codes
from promoc_core.promoc_exceptions import PositionOutOfBoundsError

from ..models import XBotPose
from .base import ServiceCallbacksBase, handle_service_errors
from .motion_input import (
    process_arc_request,
    process_linear_request,
    process_rotary_request,
    process_six_dof_request,
)


class MotionCallbacks(ServiceCallbacksBase):
    """Callbacks for motion-related services."""

    @handle_service_errors()
    def callback_linear_motion_si(self, request, response):
        processed = process_linear_request(request)
        self.mover_utils.ensure_xbot_active(processed.xbot_id)
        current = self.mover_utils.get_current_position(processed.xbot_id)
        target = XBotPose(
            x=processed.absolute_target.x,
            y=processed.absolute_target.y,
            z=current.z,
            rx=current.rx,
            ry=current.ry,
            rz=current.rz,
        )
        if not self.mover_utils.is_position_in_bounds(target):
            raise PositionOutOfBoundsError(
                "Target position outside configured bounds",
                error_code=error_codes.TARGET_OUT_OF_RANGE,
                details={"xbot_id": processed.xbot_id},
            )
        speed = self.mover_utils.get_speed_profile(processed.xbot_id)
        with self._operation_guard(processed.xbot_id):
            travel_time = self.driver.move_linear_absolute(
                processed.xbot_id,
                target.x,
                target.y,
                speed,
            )
            self.mover_utils.wait_for_motion_completion(
                processed.xbot_id,
                target,
                self.config.xy_tolerance,
                travel_time,
                buffer_s=3.0,
                multiplier=1.5,
                minimum_timeout=5.0,
            )
        return self._success(response, f"Linear motion completed for XBot {processed.xbot_id}")

    @handle_service_errors()
    def callback_six_d_motion(self, request, response):
        xbot_id = int(request.xbot_id)
        current = self.mover_utils.get_current_position(xbot_id)
        processed = process_six_dof_request(request, current, self.NO_CHANGE)
        self.mover_utils.ensure_xbot_active(processed.xbot_id)
        if not self.mover_utils.is_position_in_bounds(processed.absolute_target):
            raise PositionOutOfBoundsError(
                "Target position outside configured bounds",
                error_code=error_codes.TARGET_OUT_OF_RANGE,
                details={"xbot_id": processed.xbot_id},
            )
        speed = self.mover_utils.get_speed_profile(processed.xbot_id)
        with self._operation_guard(processed.xbot_id):
            travel_time = self.driver.move_six_dof_absolute(
                processed.xbot_id,
                processed.absolute_target,
                speed,
            )
            self.mover_utils.wait_for_motion_completion(
                processed.xbot_id,
                processed.absolute_target,
                self.config.six_d_tolerance,
                travel_time,
                buffer_s=5.0,
                multiplier=1.5,
                minimum_timeout=8.0,
            )
        return self._success(response, f"6-DOF motion completed for XBot {processed.xbot_id}")

    @handle_service_errors()
    def callback_arc_motion_si(self, request, response):
        xbot_id = int(request.xbot_id)
        current = self.mover_utils.get_current_position(xbot_id)
        processed = process_arc_request(request, current)
        self.mover_utils.ensure_xbot_active(processed.xbot_id)
        if not self.mover_utils.is_position_in_bounds(processed.absolute_target):
            raise PositionOutOfBoundsError(
                "Target position outside configured bounds",
                error_code=error_codes.TARGET_OUT_OF_RANGE,
                details={"xbot_id": processed.xbot_id},
            )
        with self._operation_guard(processed.xbot_id):
            travel_time = self.driver.arc_move(
                processed.xbot_id,
                processed.absolute_target.x if processed.relative_target is None else processed.relative_target.x,
                processed.absolute_target.y if processed.relative_target is None else processed.relative_target.y,
                self._require_finite(request.radius, "radius") / 1000.0,
                self._require_finite(request.max_speed, "max_speed") / 1000.0,
                self._require_finite(request.max_accel, "max_accel") / 1000.0,
                relative=processed.relative_target is not None,
                final_speed=self._require_finite(request.final_speed, "final_speed") / 1000.0,
                arc_mode=int(request.arc_mode),
                arc_type=int(request.arc_type),
                arc_direction=int(request.arc_direction),
                angle_rad=self._require_finite(request.angle_degrees, "angle_degrees")
                * 3.141592653589793
                / 180.0,
            )
            self.mover_utils.wait_for_motion_completion(
                processed.xbot_id,
                processed.absolute_target,
                self.config.xy_tolerance,
                travel_time,
                buffer_s=5.0,
                multiplier=1.8,
                minimum_timeout=8.0,
            )
        mode = "relative" if processed.relative_target is not None else "absolute"
        return self._success(response, f"Arc motion ({mode}) completed for XBot {processed.xbot_id}")

    @handle_service_errors()
    def callback_rotary_motion(self, request, response):
        current = self.mover_utils.get_current_position(int(request.xbot_id))
        processed = process_rotary_request(request, current)
        self.mover_utils.ensure_xbot_active(processed.xbot_id)
        with self._operation_guard(processed.xbot_id):
            travel_time = self.driver.rotate(
                processed.xbot_id,
                processed.absolute_target.rz,
                self._require_finite(request.max_rz_speed, "max_rz_speed") * 3.141592653589793 / 180.0,
                self._require_finite(request.max_accel_rz, "max_accel_rz") * 3.141592653589793 / 180.0,
                int(request.rot_mode),
            )
            self.mover_utils.wait_for_motion_completion(
                processed.xbot_id,
                processed.absolute_target,
                self.config.six_d_tolerance,
                travel_time,
                buffer_s=2.0,
                multiplier=1.5,
                minimum_timeout=4.0,
            )
        return self._success(response, f"Rotary motion completed for XBot {processed.xbot_id}")
