"""
Control Callbacks for Planar Motor Node.

Contains callbacks for control-related services:
- Activate/Deactivate XBots
- Levitation control
- Stop motion
- Velocity/acceleration parameters
"""

from .base import ServiceCallbacksBase, InvalidParameterError
from promoc_core.promoc_exceptions import HardwareError, ConnectionError


class ControlCallbacks(ServiceCallbacksBase):
    """Callbacks for control-related services."""

    def callback_activate_xbot(self, request, response):
        """
        Activate or deactivate the XBots.

        Service: /mover_node/activate_xbots

        Args:
            request.activation_status: True to activate, False to deactivate.
        """
        try:
            if request.activation_status:
                self.pmc.bot.activate_xbots()
                response.status_message = "XBots successfully activated"
            else:
                self.pmc.bot.deactivate_xbots()
                response.status_message = "XBots successfully deactivated"
            response.success = True

        except (HardwareError, ConnectionError) as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ XBot activation failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_levitation_xbot(self, request, response):
        """
        Start or stop levitation (floating above the stator).

        Service: /mover_node/levitation_xbots

        IMPORTANT: XBot must be activated first.

        Args:
            request.levitation: True to start, False to stop.
        """
        try:
            command = 1 if request.levitation else 0
            self.pmc.bot.levitation_command(0, command)  # 0 = all XBots

            action = 'enabled' if request.levitation else 'disabled'
            response.status_message = f"Levitation {action} globally"
            response.success = True
            self.logger.info(response.status_message)

        except (HardwareError, ConnectionError) as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Levitation command failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_stop_motion(self, request, response):
        """
        Stop the current motion of an XBot immediately.

        Service: /mover_node/stop_motion

        EMERGENCY FUNCTION: Stops motion instantly.

        Args:
            request.xbot_id: ID of the XBot to stop.
        """
        try:
            self.pmc.bot.stop_motion(request.xbot_id)
            response.success = True
            response.status_message = f"Stop command sent to XBot {request.xbot_id}"

        except (HardwareError, ConnectionError) as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Stop motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_set_velocity_acceleration(self, request, response):
        """
        Set velocity and acceleration parameters for an XBot.

        Service: /mover_node/set_velocity_acceleration
        """
        try:
            # Validate XBot ID
            if request.xbot_id < 0:
                raise InvalidParameterError(
                    f"XBot ID must be non-negative, got: {request.xbot_id}",
                    details={'parameter': 'xbot_id', 'value': request.xbot_id}
                )

            # Validate all parameters are positive
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
                if value <= 0:
                    raise InvalidParameterError(
                        f"{name} must be positive, got: {value}",
                        details={'parameter': name, 'value': value}
                    )

            # Set parameters
            self.mover_utils.set_speed_params(request.xbot_id, params)

            self.logger.info(
                f"Velocity params set for XBot {request.xbot_id}: "
                f"xy_vel={request.xy_vel:.3f}m/s, xy_accel={request.xy_max_accel:.3f}m/s²"
            )
            response.success = True
            response.status_message = "Parameters set successfully"

        except InvalidParameterError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Setting parameters failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response
