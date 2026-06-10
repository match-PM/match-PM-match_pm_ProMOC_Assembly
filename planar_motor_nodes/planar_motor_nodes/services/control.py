"""Control callbacks for planar motor services."""

from __future__ import annotations

from promoc_core import error_codes

from .base import InvalidParameterError, ServiceCallbacksBase, handle_service_errors


class ControlCallbacks(ServiceCallbacksBase):
    """Callbacks for control-related services."""

    @handle_service_errors()
    def callback_activate_xbot(self, request, response):
        self.mover_utils.ensure_selected_xbot(self.config.xbot_id)
        if request.activation_status:
            self.driver.activate_xbots([self.config.xbot_id])
            message = f"Activated XBot {self.config.xbot_id}"
        else:
            self.driver.deactivate_xbots([self.config.xbot_id])
            message = f"Deactivated XBot {self.config.xbot_id}"
        if hasattr(response, "activation_status"):
            response.activation_status = bool(request.activation_status)
        return self._success(response, message)

    @handle_service_errors()
    def callback_levitation_xbot(self, request, response):
        self.mover_utils.ensure_selected_xbot(self.config.xbot_id)
        self.driver.set_levitation([self.config.xbot_id], enabled=bool(request.levitation))
        if hasattr(response, "levitation"):
            response.levitation = bool(request.levitation)
        action = "enabled" if request.levitation else "disabled"
        return self._success(
            response,
            f"Levitation {action} for XBot {self.config.xbot_id}",
        )

    @handle_service_errors()
    def callback_stop_motion(self, request, response):
        self.mover_utils.stop_xbot(int(request.xbot_id))
        response.success = True
        response.error_code = error_codes.STOP_REQUESTED
        response.status_message = f"Stop requested for XBot {request.xbot_id}"
        return response

    @handle_service_errors()
    def callback_set_velocity_acceleration(self, request, response):
        xbot_id = int(request.xbot_id)
        self.mover_utils.ensure_selected_xbot(xbot_id)
        values = {
            "xy_vel": self._require_finite(request.xy_vel, "xy_vel"),
            "xy_max_accel": self._require_finite(request.xy_max_accel, "xy_max_accel"),
            "z_vel": self._require_finite(request.z_vel, "z_vel"),
            "z_max_accel": self._require_finite(request.z_max_accel, "z_max_accel"),
            "rx_vel": self._require_finite(request.rx_vel, "rx_vel"),
            "ry_vel": self._require_finite(request.ry_vel, "ry_vel"),
            "rz_vel": self._require_finite(request.rz_vel, "rz_vel"),
        }
        for name, value in values.items():
            if value <= 0.0:
                raise InvalidParameterError(
                    f"{name} must be positive",
                    error_code=error_codes.INVALID_COMMAND,
                    details={"parameter": name, "value": value},
                )
        self.mover_utils.set_speed_profile(xbot_id, **values)
        return self._success(response, f"Updated speed parameters for XBot {xbot_id}")
