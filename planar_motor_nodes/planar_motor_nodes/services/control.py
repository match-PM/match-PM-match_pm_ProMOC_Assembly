"""
Control Callbacks for Planar Motor Node.

Contains callbacks for control-related services:
- Activate/Deactivate XBots
- Levitation control
- Stop motion
- Velocity/acceleration parameters
"""

from .base import InvalidParameterError, ServiceCallbacksBase
from promoc_core.error_handling import handle_service_errors


class ControlCallbacks(ServiceCallbacksBase):
    """Callbacks for control-related services."""

    @handle_service_errors()
    def callback_activate_xbot(self, request, response):
        """
        Activate or deactivate the XBots.

        Service: /promoc/mover/activate_xbots

        Args:
            request.activation_status: True to activate, False to deactivate.
        """
        if request.activation_status:
            self.pmc.bot.activate_xbots()
            response.status_message = "XBots successfully activated"
        else:
            self.pmc.bot.deactivate_xbots()
            response.status_message = "XBots successfully deactivated"
        response.success = True
        return response

    @handle_service_errors()
    def callback_levitation_xbot(self, request, response):
        """
        Start or stop levitation (floating above the stator).

        Service: /promoc/mover/levitation_xbots

        IMPORTANT: XBot must be activated first.

        Args:
            request.levitation: True to start, False to stop.
        """
        command = 1 if request.levitation else 0
        self.pmc.bot.levitation_command(0, command)  # 0 = all XBots

        action = "enabled" if request.levitation else "disabled"
        response.status_message = f"Levitation {action} globally"
        response.success = True
        self.logger.info(response.status_message)
        return response

    @handle_service_errors()
    def callback_stop_motion(self, request, response):
        """
        Stop the current motion of an XBot immediately.

        Service: /promoc/mover/stop_motion

        EMERGENCY FUNCTION: Stops motion instantly.

        Args:
            request.xbot_id: ID of the XBot to stop.
        """
        self.pmc.bot.stop_motion(request.xbot_id)
        response.success = True
        response.status_message = f"Stop command sent to XBot {request.xbot_id}"
        return response

    @handle_service_errors()
    def callback_set_velocity_acceleration(self, request, response):
        """
        Set velocity and acceleration parameters for an XBot.

        Service: /promoc/mover/set_velocity_acceleration
        """
        # Validate XBot ID
        if request.xbot_id < 0:
            raise InvalidParameterError(
                f"XBot ID must be non-negative, got: {request.xbot_id}",
                details={"parameter": "xbot_id", "value": request.xbot_id},
            )

        # Validate all parameters are positive
        params = {
            "xy_vel": request.xy_vel,
            "z_vel": request.z_vel,
            "rx_vel": request.rx_vel,
            "ry_vel": request.ry_vel,
            "rz_vel": request.rz_vel,
            "xy_max_accel": request.xy_max_accel,
            "z_max_accel": request.z_max_accel,
        }

        for name, value in params.items():
            if value <= 0:
                raise InvalidParameterError(
                    f"{name} must be positive, got: {value}",
                    details={"parameter": name, "value": value},
                )

        # Set parameters
        self.mover_utils.set_speed_params(request.xbot_id, params)

        self.logger.info(
            f"Velocity params set for XBot {request.xbot_id}: "
            f"xy_vel={request.xy_vel:.3f}m/s, xy_accel={request.xy_max_accel:.3f}m/s²"
        )
        response.success = True
        response.status_message = "Parameters set successfully"
        return response

