import time
import math
from typing import List, Optional
from enum import Enum

# Explizite Importe für eine saubere Architektur
from .pmc_interface import PmcInterface
from .node_config import NodeConfig
# Wir importieren die Enums sicherheitshalber aus dem Mock, da sie dort garantiert vorhanden sind.
from .drivers.mock_pmclib import XbotState


class MotionStatus(Enum):
    """Status of motion based on XBot controller status"""
    UNKNOWN = "unknown"
    IDLE = "idle"
    MOVING = "moving"
    ERROR = "error"
    COMPLETED = "completed"
    TIMEOUT = "timeout"


class PositionUtils:
    """Utility class for position management, decoupled from the ROS node."""

    def __init__(self, logger, pmc_interface: PmcInterface, config: NodeConfig):
        """Initializes the class with explicit dependencies."""
        self.logger = logger
        self.pmc = pmc_interface
        self.config = config
        self.is_mock = self.pmc.status['is_mock']
        self._logged_warnings = set()

    def get_current_position(self, xbot_id: int = 0) -> Optional[List[float]]:
        """Gets the current XBot position via the PmcInterface."""
        try:
            xbot_data_list = self.pmc.bot.get_all_xbot_info(0)
            
            if not xbot_data_list:
                if not self.is_mock:
                    self.logger.error("❌ No XBot data returned from PMCLib")
                return None
            
            if xbot_id >= len(xbot_data_list):
                warning_key = f"xbot_{xbot_id}_unavailable"
                if warning_key not in self._logged_warnings:
                    self.logger.warning(
                        f"⚠️ XBot {xbot_id} not available. Available: {len(xbot_data_list)}. "
                        f"Using XBot 0 as fallback.")
                    self._logged_warnings.add(warning_key)
                xbot_id = 0
            
            xbot_data = xbot_data_list[xbot_id]
            position = [
                float(xbot_data.x_pos), float(xbot_data.y_pos), float(xbot_data.z_pos),
                float(xbot_data.rx_pos), float(xbot_data.ry_pos), float(xbot_data.rz_pos)
            ]
            return position
            
        except Exception as e:
            if not self.is_mock:
                self.logger.error(f"❌ Error in get_current_position for XBot {xbot_id}: {e}")
            return None

    def get_xbot_status_info(self, xbot_id: int = 0) -> Optional[dict]:
        """Gets comprehensive XBot status information."""
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
                    self.logger.warning(f"⚠️ Could not get status for XBot {xbot_id}: {e}")
                xbot_state_enum = XbotState.XBOT_UNKNOWN
                xbot_state_str = "UNKNOWN"

            return {
                'position': current_pos,
                'xbot_state': xbot_state_enum,
                'xbot_state_string': xbot_state_str,
            }
        except Exception as e:
            if not self.is_mock:
                self.logger.error(f"❌ Error getting XBot status info: {e}")
            return None
            
    def get_xbot_state_string(self, xbot_id: int = 0) -> str:
        """Gets the xBot Status as a string."""
        try:
            xbot_status = self.pmc.bot.get_xbot_status(xbot_id)
            return self._xbot_state_to_string(xbot_status.xbot_state)
        except Exception:
            return "IDLE"

    def _xbot_state_to_string(self, xbot_state) -> str:
        """Converts the XbotState enum to a readable string."""
        try:
            if hasattr(xbot_state, 'name'):
                return xbot_state.name
            else:
                state_map = {v.value: v.name for v in XbotState}
                return state_map.get(int(xbot_state), "UNKNOWN")
        except:
            return "UNKNOWN"

    def wait_for_motion_completion(self, xbot_id: int, target_position: List[float],
                                   position_tolerance: float, max_wait_time: float = 10.0) -> MotionStatus:
        """Waits for the completion of a motion."""
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            state_str = self.get_xbot_state_string(xbot_id)

            if state_str in ["XBOT_IDLE", "IDLE"]:
                self.logger.info(f"✅ Motion completed for XBot {xbot_id}.")
                # Optional: Position am Ende verifizieren
                return MotionStatus.COMPLETED

            if state_str in ["XBOT_ERROR", "ERROR", "XBOT_STOPPED"]:
                self.logger.error(f"❌ Motion error for XBot {xbot_id} - State: {state_str}")
                return MotionStatus.ERROR
            
            time.sleep(0.1)

        self.logger.warning(f"⚠️ Motion timeout for XBot {xbot_id} after {max_wait_time:.1f}s")
        return MotionStatus.TIMEOUT

    def is_position_in_bounds(self, x: float, y: float, z: float) -> bool:
        """Checks if a position is within defined bounds."""
        return (self.config.x_min <= x <= self.config.x_max and
                self.config.y_min <= y <= self.config.y_max and
                self.config.z_min <= z <= self.config.z_max)

    def validate_xbot_id(self, xbot_id: int) -> bool:
        """Validates the XBot ID."""
        if not (0 <= xbot_id <= 15):
            self.logger.error(f"❌ Invalid XBot ID: {xbot_id} (must be 0-15)")
            return False
        return True

    def diagnose_xbot_availability(self) -> dict:
        """Diagnoses which XBots are available and responding."""
        diagnosis = {'available_xbots': [], 'total_from_get_all': 0}
        try:
            data_list = self.pmc.bot.get_all_xbot_info(0)
            diagnosis['total_from_get_all'] = len(data_list) if data_list else 0
            
            for xbot_id in range(4): # Teste die ersten 4 IDs
                try:
                    status = self.pmc.bot.get_xbot_status(xbot_id)
                    diagnosis['available_xbots'].append({
                        'id': xbot_id, 'status': 'available',
                        'state': self._xbot_state_to_string(status.xbot_state)
                    })
                except Exception as e:
                    diagnosis['available_xbots'].append({'id': xbot_id, 'status': 'error', 'error': str(e)})
        except Exception as e:
            self.logger.error(f"General diagnosis error: {e}")
        return diagnosis