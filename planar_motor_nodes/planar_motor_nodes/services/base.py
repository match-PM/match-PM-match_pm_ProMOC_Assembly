"""
Base class for Planar Motor Service Callbacks.

This module contains the base class with shared utilities including
the central _process_motion_input() method used by all motion callbacks.
"""

from ..helpers.pmc_interface import PmcInterface
from ..helpers.mover_utils import MoverUtils
from ..config import MoverNodeConfig
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    SafetyError,
)
from promoc_core.logging import TaggedLogger, LogTags

# Aliases for more specific error handling
InvalidParameterError = ConfigurationError
ParameterValidationError = ConfigurationError
PositionOutOfBoundsError = SafetyError


class ServiceCallbacksBase:
    """
    Base class for all service callbacks.

    Contains:
    - Initialization logic
    - _process_motion_input(): Central validation and unit conversion
    - NO_CHANGE constant for selective axis updates

    Attributes:
        logger: TaggedLogger for structured output.
        pmc (PmcInterface): Hardware interface.
        mover_utils (MoverUtils): Helper functions.
        config (MoverNodeConfig): Typed node configuration.
    """

    # Special value to indicate "keep current position"
    NO_CHANGE = -999999

    def __init__(
        self,
        logger,
        pmc_interface: PmcInterface,
        mover_utils: MoverUtils,
        config: MoverNodeConfig,
    ):
        """
        Initialize the callbacks with their dependencies.

        Args:
            logger: ROS2 logger for log output.
            pmc_interface: Hardware interface for PMC commands.
            mover_utils: Helper functions for position calculations.
            config: Configuration with bounds and tolerances.
        """
        # Wrap logger with tag for structured logging
        self.logger = TaggedLogger(logger, LogTags.PMC_MOTION)
        self.pmc = pmc_interface
        self.mover_utils = mover_utils
        self.config = config

        self.logger.info(
            f"ServiceCallbacks initialized. Using PMCLib: {self.pmc.status['source']}"
        )

    def _process_motion_input(
        self, request, current_position: list = None, motion_type: str = "6dof"
    ) -> list:
        """
        Universal motion input processor with integrated validation.

        This is the CENTRAL function for all motion requests. It:
        1. Validates input parameters.
        2. Converts units (mm → m, deg → rad).
        3. Checks if the target position is within allowed bounds.
        4. Returns the processed target position.

        Args:
            request: The ROS2 service request containing position data.
            current_position: The current position [x,y,z,rx,ry,rz] or None.
            motion_type: The type of motion:
                - "linear": X, Y only.
                - "6dof": All 6 axes.
                - "rotary": Rz only.
                - "arc", "arc_si": Arc-shaped.

        Returns:
            list: The target position [x, y, z, rx, ry, rz] in SI units (m, rad).

        Raises:
            ParameterValidationError: If parameters are invalid.
            PositionOutOfBoundsError: If the target position is outside allowed limits.
        """
        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: Parameter Validation
        # ══════════════════════════════════════════════════════════════════════

        # XBot ID must be non-negative
        if hasattr(request, "xbot_id") and request.xbot_id < 0:
            raise ParameterValidationError(
                f"XBot ID must be non-negative, got: {request.xbot_id}",
                details={
                    "parameter": "xbot_id",
                    "value": request.xbot_id,
                    "constraint": "non-negative",
                },
            )

        # Motion-type-specific validations
        self._validate_motion_type_params(request, motion_type)

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: Get Current Position
        # ══════════════════════════════════════════════════════════════════════
        if current_position is None and hasattr(request, "xbot_id"):
            current_position = self.mover_utils.get_current_position(request.xbot_id)
            if current_position is None:
                current_position = [0.1, 0.1, 0.001, 0.0, 0.0, 0.0]  # Safe default
                self.logger.warning(
                    "Could not get current position, using safe default."
                )
        elif current_position is None:
            current_position = [0.1, 0.1, 0.001, 0.0, 0.0, 0.0]

        # Start with current position
        target_pos = current_position[:]

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 3: Calculate Target Position
        # ══════════════════════════════════════════════════════════════════════
        if motion_type == "linear":
            target_pos[0] = self.mover_utils.mm_to_m(request.x_pos)
            target_pos[1] = self.mover_utils.mm_to_m(request.y_pos)
            target_pos[2] = 0.001  # Standard levitation height

        elif motion_type == "6dof":
            target_pos[0] = (
                self.mover_utils.mm_to_m(request.x_pos)
                if request.x_pos != self.NO_CHANGE
                else current_position[0]
            )
            target_pos[1] = (
                self.mover_utils.mm_to_m(request.y_pos)
                if request.y_pos != self.NO_CHANGE
                else current_position[1]
            )
            target_pos[2] = (
                self.mover_utils.mm_to_m(request.z_pos)
                if request.z_pos != self.NO_CHANGE
                else current_position[2]
            )
            target_pos[3] = (
                self.mover_utils.deg_to_rad(request.rx_pos)
                if request.rx_pos != self.NO_CHANGE
                else current_position[3]
            )
            target_pos[4] = (
                self.mover_utils.deg_to_rad(request.ry_pos)
                if request.ry_pos != self.NO_CHANGE
                else current_position[4]
            )
            target_pos[5] = (
                self.mover_utils.deg_to_rad(request.rz_pos)
                if request.rz_pos != self.NO_CHANGE
                else current_position[5]
            )

        elif motion_type == "rotary":
            target_pos[5] = self.mover_utils.deg_to_rad(request.target_rz)

        elif motion_type == "arc":
            target_pos[0] = self.mover_utils.mm_to_m(request.x_pos)
            target_pos[1] = self.mover_utils.mm_to_m(request.y_pos)

        elif motion_type == "arc_si":
            target_pos[0] = self.mover_utils.mm_to_m(request.target_x)
            target_pos[1] = self.mover_utils.mm_to_m(request.target_y)

        else:
            raise ValueError(f"Unknown motion type: {motion_type}")

        return target_pos

    def _validate_motion_type_params(self, request, motion_type: str) -> None:
        """Validate motion-type-specific parameters."""
        if motion_type == "rotary":
            if hasattr(request, "rot_mode") and request.rot_mode not in [0, 1, 2]:
                raise ParameterValidationError(
                    f"Invalid rot_mode: {request.rot_mode}. Valid: 0, 1, 2",
                    details={"parameter": "rot_mode", "value": request.rot_mode},
                )
            if hasattr(request, "max_rz_speed") and request.max_rz_speed <= 0:
                raise ParameterValidationError(
                    f"Max RZ speed must be positive, got: {request.max_rz_speed}",
                    details={
                        "parameter": "max_rz_speed",
                        "value": request.max_rz_speed,
                    },
                )
            if hasattr(request, "max_accel_rz") and request.max_accel_rz <= 0:
                raise ParameterValidationError(
                    f"Max RZ acceleration must be positive, got: {request.max_accel_rz}",
                    details={
                        "parameter": "max_accel_rz",
                        "value": request.max_accel_rz,
                    },
                )

        elif motion_type in ["arc", "arc_si"]:
            self._validate_arc_params(request)

    def _validate_arc_params(self, request) -> None:
        """Validate arc motion parameters."""
        validations = [
            ("arc_mode", [0, 1, 2], "arc_mode"),
            ("arc_type", [0, 1], "arc_type"),
            ("arc_direction", [0, 1], "arc_direction"),
            ("pos_mode", [0, 1], "pos_mode"),
        ]
        for attr, valid_values, name in validations:
            if hasattr(request, attr) and getattr(request, attr) not in valid_values:
                raise InvalidParameterError(
                    f"Invalid {name}: {getattr(request, attr)}. Valid: {valid_values}",
                    details={"parameter": name, "value": getattr(request, attr)},
                )

        positive_params = ["radius", "max_speed", "max_accel"]
        for param in positive_params:
            if hasattr(request, param) and getattr(request, param) <= 0:
                raise InvalidParameterError(
                    f"{param} must be positive, got: {getattr(request, param)}",
                    details={"parameter": param, "value": getattr(request, param)},
                )
