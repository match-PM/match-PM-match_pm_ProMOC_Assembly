"""
Mover Utilities - Helper functions for XBot position management.

This module contains the MoverUtils class, which provides helper functions
for position queries, motion monitoring, and unit conversion.

Function Overview:
==================

Position & Status:
------------------
- get_current_position(xbot_id) → [x, y, z, rx, ry, rz] in SI units
- get_xbot_status_info(xbot_id) → dict with position and state
- get_xbot_state_string(xbot_id) → "IDLE", "MOVING", etc.

Motion Monitoring:
--------------------
- wait_for_motion_completion() → MotionStatus (COMPLETED, TIMEOUT, ERROR)
- is_position_in_bounds(x, y, z) → True/False

Unit Conversion:
----------------------
- mm_to_m(value) → value / 1000
- m_to_mm(value) → value * 1000
- deg_to_rad(value) → value * π/180
- rad_to_deg(value) → value * 180/π

Configuration:
--------------
- get_speed_params(xbot_id) → dict with velocities/accelerations

Usage Example:
==================
    utils = MoverUtils(logger, pmc_interface, config)

    # Get position
    pos = utils.get_current_position(0)
    print(f"XBot is at x={pos[0]*1000:.1f}mm, y={pos[1]*1000:.1f}mm")

    # Monitor motion
    result = utils.wait_for_motion_completion(
        xbot_id=0,
        target_pos=[0.1, 0.05, 0.001, 0, 0, 0],
        tolerance=0.001,
        timeout=10.0
    )
    if result == MotionStatus.COMPLETED:
        print("Target reached!")
"""

import time
import math
from typing import Dict, List, Optional

# Explicit imports for a clean architecture
from .mover_pmc_interface import PmcInterface
from .config import MoverNodeConfig

# XbotState from Mock (guaranteed to be available)
from .drivers.mock_pmclib import XbotState

# Common utilities from promoc_core
from promoc_core.motion import MotionStatus
from promoc_core.validation import is_in_range, validate_id_range
from promoc_core.conversions import rad_to_deg, mm_to_m, m_to_mm


class MoverUtils:
    """
    Helper functions for XBot position management and motion monitoring.

    This class is decoupled from ROS2 and can be tested independently.
    It is used by the MoverServiceNode and ServiceCallbacks.

    Main Functions:
    ---------------
    1. Get position: get_current_position()
    2. Monitor motion: wait_for_motion_completion()
    3. Check boundaries: is_position_in_bounds()
    4. Convert units: mm_to_m(), deg_to_rad(), etc.

    Attributes:
        logger: ROS2 logger for output.
        pmc (PmcInterface): Hardware interface.
        config (MoverNodeConfig): Typed node configuration with bounds.
        is_mock (bool): True if mock mode is active.
        velocity_params (dict): Velocity parameters per XBot.
    """

    def __init__(self, logger, pmc_interface: PmcInterface, config: MoverNodeConfig):
        """
        Initializes the utilities with dependencies.

        Args:
            logger: ROS2 logger.
            pmc_interface: Hardware interface.
            config: Configuration with bounds and tolerances.
        """
        self.logger = logger
        self.pmc = pmc_interface
        self.config = config
        self.is_mock = self.pmc.status["is_mock"]
        self._logged_no_data = False
        self._logged_warnings = set()

        # Velocity/acceleration parameters per XBot.
        #
        # Why this lives here:
        # - Callbacks should not own mutable runtime tuning state.
        # - We want a single place that defines defaults and validation.
        #
        # Units:
        # - velocities: m/s (rotational: rad/s)
        # - accelerations: m/s²
        self.velocity_params: Dict[int, Dict[str, float]] = {}

    # ══════════════════════════════════════════════════════════════════════════
    # UNIT CONVERSION
    # ══════════════════════════════════════════════════════════════════════════

    def mm_to_m(self, value_mm: float) -> float:
        """Converts millimeters to meters."""
        return mm_to_m(value_mm)

    def m_to_mm(self, value_m: float) -> float:
        """Converts meters to millimeters."""
        return m_to_mm(value_m)

    def deg_to_rad(self, value_deg: float) -> float:
        """Converts degrees to radians."""
        return math.radians(value_deg)

    def rad_to_deg(self, value_rad: float) -> float:
        """Converts radians to degrees."""
        return rad_to_deg(value_rad)

    # ══════════════════════════════════════════════════════════════════════════
    # SPEED / ACCELERATION PARAMETERS
    # ══════════════════════════════════════════════════════════════════════════

    def get_speed_params(self, xbot_id: int = 0) -> Dict[str, float]:
        """Return velocity/acceleration parameters for an XBot.

        The ServiceCallbacks expect these keys:
        - xy_vel
        - xy_max_accel
        - z_vel
        - z_max_accel
        - rx_vel
        - ry_vel
        - rz_vel

        If no parameters were set via service calls, sensible defaults are
        returned.

        Args:
            xbot_id: XBot ID

        Returns:
            Dict[str, float]: Parameters in SI units.
        """
        # Don't hard-fail here; callbacks already validate and we want robust
        # defaults even in mock.
        if xbot_id not in self.velocity_params:
            # Defaults are conservative. They can be tuned via
            # callback_set_velocity_acceleration.
            self.velocity_params[xbot_id] = {
                "xy_vel": 0.05,
                "xy_max_accel": 0.2,
                "z_vel": 0.01,
                "z_max_accel": 0.05,
                "rx_vel": self.deg_to_rad(10.0),
                "ry_vel": self.deg_to_rad(10.0),
                "rz_vel": self.deg_to_rad(15.0),
            }

        # Return a copy to avoid accidental external mutation.
        return dict(self.velocity_params[xbot_id])

    def set_speed_params(self, xbot_id: int, params: Dict[str, float]) -> None:
        """Set velocity/acceleration parameters for an XBot.

        Args:
            xbot_id: XBot ID
            params: Dict with same keys as get_speed_params()
        """
        self.velocity_params[xbot_id] = dict(params)

    # ══════════════════════════════════════════════════════════════════════════
    # POSITION QUERIES
    # ══════════════════════════════════════════════════════════════════════════

    def get_current_position(self, xbot_id: int = 0) -> Optional[List[float]]:
        """
        Queries the current XBot position from the PMC controller.

        Args:
            xbot_id: ID of the XBot (default: 0).

        Returns:
            A list [x, y, z, rx, ry, rz] in SI units (m, rad), or
            None if no data is available.

        Flow:
        -----
        1. Fetch XBot data from the PMC.
        2. Check if the requested ID is available.
        3. Return the position as a list.
        """
        try:
            xbot_data_list = self.pmc.bot.get_xbot_data()

            if not xbot_data_list:
                if not self._logged_no_data:
                    self.logger.error("No XBot data returned from PMCLib")
                    self._logged_no_data = True
                return None

            if xbot_id >= len(xbot_data_list):
                warning_key = f"xbot_{xbot_id}_unavailable"
                if warning_key not in self._logged_warnings:
                    self.logger.warning(
                        f"XBot {xbot_id} not available. Available: {len(xbot_data_list)}. "
                        f"Using XBot 0 as fallback."
                    )
                    self._logged_warnings.add(warning_key)
                xbot_id = 0

            xbot_data = xbot_data_list[xbot_id]
            position = [
                float(xbot_data.x_pos),
                float(xbot_data.y_pos),
                float(xbot_data.z_pos),
                float(xbot_data.rx_pos),
                float(xbot_data.ry_pos),
                float(xbot_data.rz_pos),
            ]
            return position

        except Exception as e:
            if not self.is_mock:
                self.logger.error(
                    f"Error in get_current_position for XBot {xbot_id}: {e}",
                    exc_info=True,
                )
            return None

    def get_xbot_status_info(self, xbot_id: int = 0) -> Optional[dict]:
        """
        Fetches comprehensive status information for an XBot.

        Args:
            xbot_id: ID of the XBot.

        Returns:
            A dictionary containing:
            - 'position': [x, y, z, rx, ry, rz]
            - 'xbot_state': XbotState Enum
            - 'xbot_state_string': "IDLE", "MOVING", etc.
        """
        try:
            current_pos = self.get_current_position(xbot_id)
            if not current_pos:
                current_pos = [0.0] * 6  # Fallback

            try:
                xbot_status = self.pmc.bot.get_xbot_status(xbot_id)
                xbot_state_enum = xbot_status.xbot_state
                xbot_state_str = self._xbot_state_to_string(xbot_state_enum)
            except Exception as e:
                if not self.is_mock:
                    self.logger.warning(f"Could not get status for XBot {xbot_id}: {e}")
                xbot_state_enum = XbotState.XBOT_UNKNOWN
                xbot_state_str = "UNKNOWN"

            return {
                "position": current_pos,
                "xbot_state": xbot_state_enum,
                "xbot_state_string": xbot_state_str,
            }
        except Exception as e:
            if not self.is_mock:
                self.logger.error(f"Error getting XBot status info: {e}", exc_info=True)
            return None

    def get_xbot_state_string(self, xbot_id: int = 0) -> str:
        """
        Returns the XBot status as a human-readable string.

        Possible return values:
        - "IDLE": Ready for commands.
        - "MOVING": In motion.
        - "ERROR": An error has occurred.
        - "STOPPED": Halted.
        - "UNKNOWN": Status cannot be determined.
        """
        try:
            xbot_status = self.pmc.bot.get_xbot_status(xbot_id)
            return self._xbot_state_to_string(xbot_status.xbot_state)
        except Exception:
            return "IDLE"

    def _xbot_state_to_string(self, xbot_state) -> str:
        """Converts an XbotState enum to a readable string."""
        try:
            if hasattr(xbot_state, "name"):
                return xbot_state.name
            else:
                state_map = {v.value: v.name for v in XbotState}
                return state_map.get(int(xbot_state), "UNKNOWN")
        except Exception:
            return "UNKNOWN"

    # ══════════════════════════════════════════════════════════════════════════
    # MOTION MONITORING
    # ══════════════════════════════════════════════════════════════════════════

    def wait_for_motion_completion(
        self,
        xbot_id: int,
        target_position: List[float],
        position_tolerance: float,
        max_wait_time: float = 10.0,
    ) -> MotionStatus:
        """
        Waits for a motion to complete.

        This is a polling loop that checks the XBot status every 100ms.

        Args:
            xbot_id: ID of the XBot to monitor.
            target_position: Target position [x, y, z, rx, ry, rz] (currently for logging only).
            position_tolerance: Tolerance in meters (currently not used).
            max_wait_time: Maximum wait time in seconds.

        Returns:
            MotionStatus:
            - COMPLETED: Motion finished successfully (State = IDLE).
            - TIMEOUT: `max_wait_time` was exceeded.
            - ERROR: An error occurred during motion (State = ERROR).

        Flow:
        -----
        1. Poll the status at 100ms intervals.
        2. If IDLE → return COMPLETED.
        3. If ERROR → return ERROR.
        4. If timeout → return TIMEOUT.
        """
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            state_str = self.get_xbot_state_string(xbot_id)

            if state_str in ["XBOT_IDLE", "IDLE"]:
                self.logger.info(f"Motion completed for XBot {xbot_id}.")
                return MotionStatus.COMPLETED

            if state_str in ["XBOT_ERROR", "ERROR", "XBOT_STOPPED"]:
                self.logger.error(
                    f"Motion error for XBot {xbot_id} - State: {state_str}"
                )
                return MotionStatus.ERROR

            time.sleep(0.1)

        self.logger.warning(
            f"Motion timeout for XBot {xbot_id} after {max_wait_time:.1f}s"
        )
        return MotionStatus.TIMEOUT

    # ══════════════════════════════════════════════════════════════════════════
    # BOUNDS AND VALIDATION
    # ══════════════════════════════════════════════════════════════════════════

    def is_position_in_bounds(self, x: float, y: float, z: float) -> bool:
        """
        Checks if a position is within the configured software limits.

        Args:
            x, y, z: Position in meters.

        Returns:
            True if all coordinates are within bounds, False otherwise.

        Bounds from config:
            x: [x_min, x_max] (Default: 0.055 - 0.420 m)
            y: [y_min, y_max] (Default: 0.055 - 0.180 m)
            z: [z_min, z_max] (Default: 0.000 - 0.004 m)
        """
        return (
            is_in_range(x, self.config.x_min, self.config.x_max)
            and is_in_range(y, self.config.y_min, self.config.y_max)
            and is_in_range(z, self.config.z_min, self.config.z_max)
        )

    def validate_xbot_id(self, xbot_id: int) -> bool:
        """
        Validates the XBot ID (must be between 0 and 15).

        Args:
            xbot_id: The ID to check.

        Returns:
            True if valid, False otherwise.
        """
        valid, error_msg = validate_id_range(
            xbot_id, min_id=0, max_id=15, name="XBot ID"
        )
        if not valid:
            self.logger.error(error_msg)
        return valid

    def diagnose_xbot_availability(self) -> dict:
        """Diagnoses which XBots are available and responding."""
        diagnosis = {"available_xbots": [], "total_from_get_all": 0}
        try:
            data_list = self.pmc.bot.get_all_xbot_info(0)
            diagnosis["total_from_get_all"] = len(data_list) if data_list else 0

            for xbot_id in range(4):  # Test the first 4 IDs
                try:
                    status = self.pmc.bot.get_xbot_status(xbot_id)
                    diagnosis["available_xbots"].append(
                        {
                            "id": xbot_id,
                            "status": "available",
                            "state": self._xbot_state_to_string(status.xbot_state),
                        }
                    )
                except Exception as e:
                    diagnosis["available_xbots"].append(
                        {"id": xbot_id, "status": "error", "error": str(e)}
                    )
        except Exception as e:
            self.logger.error(f"General diagnosis error: {e}")
        return diagnosis
