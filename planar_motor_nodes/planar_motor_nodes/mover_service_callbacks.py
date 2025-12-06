import math
import sys
import os
from .mover_pmc_interface import PmcInterface
from .mover_utils import MoverUtils, MotionStatus
from .mover_node_config import NodeConfig
from promoc_core.promoc_exceptions import (
    MovementTimeoutError,
    HardwareError,
    ConnectionError,
    CommunicationError,
    InvalidParameterError,
    ParameterValidationError,
    SafetyViolation,
    PositionOutOfBoundsError
)


class ServiceCallbacks:
    """
    It contains the business logic for motion commands and other services.
    """

    # Constants
    NO_CHANGE = -999999  # Special value indicating "keep current position"

    def __init__(self, logger, pmc_interface: PmcInterface, mover_utils: MoverUtils, config: NodeConfig):
        """
        Initializes the callbacks with explicit dependencies.

        Args:
            logger: The ROS 2 logger instance.
            pmc_interface: The interface to the hardware library.
            mover_utils: The utility class for position calculations and general utilities.
            config: The dataclass holding all node parameters.
        """
        self.logger = logger
        self.pmc = pmc_interface
        self.mover_utils = mover_utils
        self.config = config

        self.logger.info(
            f"ServiceCallbacks initialized. Using PMCLib: {self.pmc.status['source']}")

    def _process_motion_input(self, request, current_position: list = None, motion_type: str = "6dof") -> list:
        """
        Universal motion input processor with integrated validation for different motion types.

        Args:
            request: Service request with position data
            current_position: Current 6DOF position [x, y, z, rx, ry, rz]
            motion_type: Type of motion ("linear", "6dof", "rotary", "arc", "arc_si")

        Returns:
            list: Processed target position in SI units [x, y, z, rx, ry, rz]

        Raises:
            ParameterValidationError: If parameters are invalid
        """
        # === VALIDATION (integrated) ===
        # Common validations for all motion types
        if hasattr(request, 'xbot_id') and request.xbot_id < 0:
            raise ParameterValidationError(
                f"XBot ID must be non-negative, got: {request.xbot_id}",
                details={
                    'parameter': 'xbot_id',
                    'value': request.xbot_id,
                    'constraint': 'non-negative'
                }
            )

        # Motion type specific validations
        if motion_type == "rotary":
            if hasattr(request, 'rot_mode') and request.rot_mode not in [0, 1, 2]:
                raise ParameterValidationError(
                    f"Invalid rot_mode: {request.rot_mode}. Valid values are 0 (NO_ANGLE_WRAP), 1 (WRAP_TO_2PI_CCW), 2 (WRAP_TO_2PI_CW)",
                    details={
                        'parameter': 'rot_mode',
                        'value': request.rot_mode,
                        'valid_values': [0, 1, 2]
                    }
                )
            if hasattr(request, 'max_rz_speed') and request.max_rz_speed <= 0:
                raise ParameterValidationError(
                    f"Max RZ speed must be positive, got: {request.max_rz_speed}",
                    details={
                        'parameter': 'max_rz_speed',
                        'value': request.max_rz_speed,
                        'constraint': 'positive'
                    }
                )
            if hasattr(request, 'max_accel_rz') and request.max_accel_rz <= 0:
                raise ParameterValidationError(
                    f"Max RZ acceleration must be positive, got: {request.max_accel_rz}",
                    details={
                        'parameter': 'max_accel_rz',
                        'value': request.max_accel_rz,
                        'constraint': 'positive'
                    }
                )

        elif motion_type in ["arc", "arc_si"]:
            if hasattr(request, 'arc_mode') and request.arc_mode not in [0, 1, 2]:
                raise InvalidParameterError(
                    f"Invalid arc_mode: {request.arc_mode}. Valid values are 0, 1, 2",
                    details={
                        'parameter': 'arc_mode',
                        'value': request.arc_mode,
                        'valid_values': [0, 1, 2]
                    }
                )
            if hasattr(request, 'arc_type') and request.arc_type not in [0, 1]:
                raise InvalidParameterError(
                    f"Invalid arc_type: {request.arc_type}. Valid values are 0 (MINOR), 1 (MAJOR)",
                    details={
                        'parameter': 'arc_type',
                        'value': request.arc_type,
                        'valid_values': [0, 1]
                    }
                )
            if hasattr(request, 'arc_direction') and request.arc_direction not in [0, 1]:
                raise InvalidParameterError(
                    f"Invalid arc_direction: {request.arc_direction}. Valid values are 0 (CW), 1 (CCW)",
                    details={
                        'parameter': 'arc_direction',
                        'value': request.arc_direction,
                        'valid_values': [0, 1]
                    }
                )
            if hasattr(request, 'pos_mode') and request.pos_mode not in [0, 1]:
                raise InvalidParameterError(
                    f"Invalid pos_mode: {request.pos_mode}. Valid values are 0 (ABSOLUTE), 1 (RELATIVE)",
                    details={
                        'parameter': 'pos_mode',
                        'value': request.pos_mode,
                        'valid_values': [0, 1]
                    }
                )
            if hasattr(request, 'radius') and request.radius <= 0:
                raise InvalidParameterError(
                    f"Radius must be positive, got: {request.radius}",
                    details={
                        'parameter': 'radius',
                        'value': request.radius,
                        'constraint': 'positive'
                    }
                )
            if hasattr(request, 'max_speed') and request.max_speed <= 0:
                raise InvalidParameterError(
                    f"Max speed must be positive, got: {request.max_speed}",
                    details={
                        'parameter': 'max_speed',
                        'value': request.max_speed,
                        'constraint': 'positive'
                    }
                )
            if hasattr(request, 'max_accel') and request.max_accel <= 0:
                raise InvalidParameterError(
                    f"Max acceleration must be positive, got: {request.max_accel}",
                    details={
                        'parameter': 'max_accel',
                        'value': request.max_accel,
                        'constraint': 'positive'
                    }
                )

        # === PROCESSING ===
        # Get current position if not provided
        if current_position is None and hasattr(request, 'xbot_id'):
            current_position = self.mover_utils.get_current_position(
                request.xbot_id)
            if current_position is None:
                current_position = [0.1, 0.1, 0.001,
                                    0.0, 0.0, 0.0]  # Safe default
                self.logger.warning(
                    "Could not get current position, using safe default.")
        elif current_position is None:
            current_position = [0.1, 0.1, 0.001, 0.0, 0.0, 0.0]

        # Start with current position
        target_pos = current_position[:]

        # Process based on motion type
        if motion_type == "linear":
            # Linear motion: only X, Y change, keep Z at levitation height
            target_pos[0] = self.mover_utils.mm_to_m(request.x_pos)
            target_pos[1] = self.mover_utils.mm_to_m(request.y_pos)
            target_pos[2] = 0.001  # Standard levitation height

        elif motion_type == "6dof":
            # 6DOF motion: process all axes with NO_CHANGE support
            target_pos[0] = self.mover_utils.mm_to_m(
                request.x_pos) if request.x_pos != self.NO_CHANGE else current_position[0]
            target_pos[1] = self.mover_utils.mm_to_m(
                request.y_pos) if request.y_pos != self.NO_CHANGE else current_position[1]
            target_pos[2] = self.mover_utils.mm_to_m(
                request.z_pos) if request.z_pos != self.NO_CHANGE else current_position[2]
            target_pos[3] = self.mover_utils.deg_to_rad(
                request.rx_pos) if request.rx_pos != self.NO_CHANGE else current_position[3]
            target_pos[4] = self.mover_utils.deg_to_rad(
                request.ry_pos) if request.ry_pos != self.NO_CHANGE else current_position[4]
            target_pos[5] = self.mover_utils.deg_to_rad(
                request.rz_pos) if request.rz_pos != self.NO_CHANGE else current_position[5]

        elif motion_type == "rotary":
            # Rotary motion: only RZ changes
            target_pos[5] = self.mover_utils.deg_to_rad(request.target_rz)

        elif motion_type == "arc":
            # Arc motion: X, Y target, keep Z and rotations
            target_pos[0] = self.mover_utils.mm_to_m(request.x_pos)
            target_pos[1] = self.mover_utils.mm_to_m(request.y_pos)

        elif motion_type == "arc_si":
            # Arc motion SI: X, Y target, keep Z and rotations
            target_pos[0] = self.mover_utils.mm_to_m(request.target_x)
            target_pos[1] = self.mover_utils.mm_to_m(request.target_y)

        else:
            raise ValueError(f"Unknown motion type: {motion_type}")

        return target_pos

    # --- Service Callback Implementations ---

    def callback_linear_motion_si(self, request, response):
        """Handle linear motion requests with XBot status monitoring."""
        try:
            # Use universal motion processor
            target_pos = self._process_motion_input(
                request, motion_type="linear")

            if not self.mover_utils.is_position_in_bounds(target_pos[0], target_pos[1], target_pos[2]):
                raise PositionOutOfBoundsError(
                    "Target position outside valid bounds",
                    details={
                        'target_x': target_pos[0],
                        'target_y': target_pos[1],
                        'target_z': target_pos[2],
                        'xbot_id': request.xbot_id
                    }
                )

            speed_params = self.mover_utils.get_speed_params(request.xbot_id)
            travel_time = self.pmc.bot.linear_motion_si(
                request.xbot_id, target_pos[0], target_pos[1],
                speed_params['xy_vel'], speed_params['xy_max_accel']
            )

            timeout = max((travel_time * 1.5 + 3.0)
                          if travel_time else 5.0, 5.0)
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config.xy_tolerance, timeout
            )

            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Motion status: {motion_result.value}"

        except InvalidParameterError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Parameter validation details: {e.details}")

        except PositionOutOfBoundsError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Position bounds violation: {e.details}")

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Linear motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_six_d_motion(self, request, response):
        """Handle 6-DOF motion requests."""
        try:
            # Use universal motion processor
            target_pos = self._process_motion_input(
                request, motion_type="6dof")

            if not self.mover_utils.is_position_in_bounds(target_pos[0], target_pos[1], target_pos[2]):
                raise PositionOutOfBoundsError(
                    "Target position outside valid bounds",
                    details={
                        'target_x': target_pos[0],
                        'target_y': target_pos[1],
                        'target_z': target_pos[2],
                        'target_rx': target_pos[3],
                        'target_ry': target_pos[4],
                        'target_rz': target_pos[5],
                        'xbot_id': request.xbot_id
                    }
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

            timeout = max(travel_time * 1.5 + 5.0,
                          8.0) if travel_time else 10.0
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config.six_d_tolerance, timeout
            )

            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Motion status: {motion_result.value}"

        except InvalidParameterError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Parameter validation details: {e.details}")

        except PositionOutOfBoundsError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Position bounds violation: {e.details}")

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ 6DOF motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_activate_xbot(self, request, response):
        """Handle XBot activation/deactivation."""
        try:
            if request.activation_status:
                self.pmc.bot.activate_xbots()
                response.status_message = "XBots successfully activated"
            else:
                self.pmc.bot.deactivate_xbots()
                response.status_message = "XBots successfully deactivated"
            response.success = True

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")

        except CommunicationError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Communication error details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ XBot activation failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_levitation_xbot(self, request, response):
        """Handle XBot levitation."""
        try:
            command = 1 if request.levitation else 0
            self.logger.debug(f"Calling levitation_command(0, {command})")

            self.pmc.bot.levitation_command(0, command)  # 0 = alle XBots

            response.status_message = f"Levitation command sent: {'enable' if request.levitation else 'disable'}"
            response.success = True
            self.logger.info(
                f"Levitation {'enabled' if request.levitation else 'disabled'} globally")

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")

        except CommunicationError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Communication error details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Levitation command failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_rotary_motion(self, request, response):
        """Handle rotary motion requests."""
        try:
            # Use universal motion processor (includes validation)
            target_pos = self._process_motion_input(
                request, motion_type="rotary")

            # Get rotation mode from request
            rot_mode = request.rot_mode

            travel_time = self.pmc.bot.rotary_motion(
                request.xbot_id,
                target_pos[5],  # target_rz in radians
                request.max_rz_speed,
                request.max_accel_rz,
                0,  # cmd_lb (command label)
                rot_mode  # rotation mode
            )

            timeout = max((travel_time * 1.5 + 2.0)
                          if travel_time else 4.0, 4.0)
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config.six_d_tolerance, timeout)

            # Create descriptive status message
            rot_mode_names = {
                0: "NO_ANGLE_WRAP (direct)",
                1: "WRAP_TO_2PI_CCW (counter-clockwise)",
                2: "WRAP_TO_2PI_CW (clockwise)"
            }

            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = f"Rotary motion status: {motion_result.value} (mode: {rot_mode_names.get(rot_mode, 'unknown')})"

            self.logger.info(
                f"🔄 Rotary motion completed: target={self.mover_utils.rad_to_deg(target_pos[5]):.1f}°, mode={rot_mode_names.get(rot_mode)}, travel_time={travel_time:.2f}s")

        except InvalidParameterError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Parameter validation details: {e.details}")

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Rotary motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_stop_motion(self, request, response):
        """Handle stop motion requests."""
        try:
            self.pmc.bot.stop_motion(request.xbot_id)
            # For simplicity, we assume the command is successful.
            # A more robust version could poll the state until it's IDLE.
            response.success = True
            response.status_message = f"Stop command sent to XBot {request.xbot_id}."

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")

        except ConnectionError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Communication error details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Stop motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_set_velocity_acceleration(self, request, response):
        """Handle velocity/acceleration parameter setting."""
        try:
            # Validate XBot ID
            if request.xbot_id < 0:
                raise InvalidParameterError(
                    f"XBot ID must be non-negative, got: {request.xbot_id}",
                    details={
                        'parameter': 'xbot_id',
                        'value': request.xbot_id,
                        'constraint': 'non-negative'
                    }
                )

            # Validate all velocity/acceleration parameters are positive
            params_to_validate = {
                'xy_vel': request.xy_vel,
                'z_vel': request.z_vel,
                'rx_vel': request.rx_vel,
                'ry_vel': request.ry_vel,
                'rz_vel': request.rz_vel,
                'xy_max_accel': request.xy_max_accel,
                'z_max_accel': request.z_max_accel
            }

            for param_name, param_value in params_to_validate.items():
                if param_value <= 0:
                    raise InvalidParameterError(
                        f"{param_name} must be positive, got: {param_value}",
                        details={
                            'parameter': param_name,
                            'value': param_value,
                            'constraint': 'positive'
                        }
                    )

            # Set parameters
            self.mover_utils.velocity_params[request.xbot_id] = {
                'xy_vel': request.xy_vel, 'z_vel': request.z_vel,
                'rx_vel': request.rx_vel, 'ry_vel': request.ry_vel,
                'rz_vel': request.rz_vel, 'xy_max_accel': request.xy_max_accel,
                'z_max_accel': request.z_max_accel
            }

            self.logger.info(f"Velocity/acceleration parameters set for XBot {request.xbot_id}: "
                             f"xy_vel={request.xy_vel:.3f}m/s, xy_accel={request.xy_max_accel:.3f}m/s², "
                             f"z_vel={request.z_vel:.3f}m/s, z_accel={request.z_max_accel:.3f}m/s²")
            response.success = True
            response.status_message = "Parameters set successfully"

        except InvalidParameterError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Parameter validation details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Setting velocity/acceleration parameters failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response

    def callback_arc_motion_si(self, request, response):
        """Handle arc motion requests with SI units and comprehensive parameters."""
        try:
            # Use universal motion processor (includes validation)
            target_pos = self._process_motion_input(
                request, motion_type="arc_si")

            # Convert units: mm -> m, degrees -> radians, mm/s -> m/s
            target_x_m = self.mover_utils.mm_to_m(request.target_x)
            target_y_m = self.mover_utils.mm_to_m(request.target_y)
            radius_m = self.mover_utils.mm_to_m(request.radius)
            max_speed_ms = self.mover_utils.mm_to_m(
                request.max_speed)  # mm/s -> m/s
            max_accel_ms2 = self.mover_utils.mm_to_m(
                request.max_accel)  # mm/s² -> m/s²
            final_speed_ms = self.mover_utils.mm_to_m(
                request.final_speed)  # mm/s -> m/s
            angle_rad = self.mover_utils.deg_to_rad(request.angle_degrees)

            # Call the arc_motion_si function
            travel_time = self.pmc.bot.arc_motion_si(
                request.xbot_id,
                target_x_m,
                target_y_m,
                radius_m,
                max_speed_ms,
                max_accel_ms2,
                0,  # cmd_lb (command label)
                request.arc_mode,
                request.arc_type,
                request.arc_direction,
                request.pos_mode,
                final_speed_ms,
                angle_rad
            )

            # Wait for completion with extended timeout for arc motions
            timeout = max((travel_time * 1.8 + 5.0)
                          if travel_time else 8.0, 8.0)
            motion_result = self.mover_utils.wait_for_motion_completion(
                request.xbot_id, target_pos, self.config.xy_tolerance, timeout
            )

            # Create descriptive status message
            arc_mode_names = {
                0: "TARGETRADIUS", 1: "CENTERANGLE"
            }
            arc_type_names = {0: "MINOR_ARC", 1: "MAJOR_ARC"}
            arc_dir_names = {0: "CLOCKWISE", 1: "COUNTERCLOCKWISE"}
            pos_mode_names = {0: "ABSOLUTE", 1: "RELATIVE"}

            response.success = (motion_result == MotionStatus.COMPLETED)
            response.status_message = (
                f"Arc motion status: {motion_result.value} "
                f"(mode: {arc_mode_names.get(request.arc_mode, 'unknown')}, "
                f"type: {arc_type_names.get(request.arc_type, 'unknown')}, "
                f"dir: {arc_dir_names.get(request.arc_direction, 'unknown')}, "
                f"pos: {pos_mode_names.get(request.pos_mode, 'unknown')})"
            )

            self.logger.info(f"🌀 Arc motion completed: "
                             f"target=({request.target_x:.1f}, {request.target_y:.1f})mm, "
                             f"radius={request.radius:.1f}mm, "
                             f"travel_time={travel_time:.2f}s")

        except InvalidParameterError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Parameter validation details: {e.details}")

        except PositionOutOfBoundsError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.warn(response.status_message)
            self.logger.debug(f"Position bounds violation: {e.details}")

        except HardwareError as e:
            response.success = False
            response.status_message = f"⚠️ {str(e)}"
            self.logger.error(response.status_message)
            self.logger.debug(f"Hardware error details: {e.details}")

        except Exception as e:
            response.success = False
            response.status_message = f"❌ Arc motion failed: {str(e)}"
            self.logger.error(response.status_message, exc_info=True)

        return response
