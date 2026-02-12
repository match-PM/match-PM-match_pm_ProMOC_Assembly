# SimulatedXBot class represents a virtual XBot with position and orientation attributes
from enum import IntEnum
import threading
import time
import math

# Global logger instance
logger = None

LINEAR_MIN_TRAVEL_TIME_S = 0.2
SIX_D_TRAVEL_TIME_S = 1.5
ARC_TRAVEL_FACTOR = 1.5
ARC_MIN_TRAVEL_TIME_S = 0.5
ARC_FALLBACK_TRAVEL_TIME_S = 2.0
ROTARY_MIN_TRAVEL_TIME_S = 0.3
ROTARY_FALLBACK_TRAVEL_TIME_S = 0.8
STOP_DELAY_S = 0.2


def _schedule_motion_completion(xbot, travel_time_s, updates, completion_message=None):
    """Finalize simulated motion asynchronously after `travel_time_s`."""

    def complete_motion():
        time.sleep(travel_time_s)
        for attr_name, attr_value in updates.items():
            setattr(xbot, attr_name, attr_value)
        xbot.is_moving = False
        xbot.xbot_state = XbotState.XBOT_IDLE
        if completion_message:
            log_msg(completion_message)

    threading.Thread(target=complete_motion, daemon=True).start()


def set_logger(log_instance):
    """Set the logger to use for output instead of print."""
    global logger
    logger = log_instance

def log_msg(msg):
    """Log a message using the configured logger or print as fallback."""
    if logger:
        logger.info(msg)
    else:
        print(msg)

class SimulatedXBot:
    def __init__(self):
        # Initialize default position and orientation values
        self.x_pos = 120.0  # X position in mm
        self.y_pos = 120.0  # Y position in mm
        self.z_pos = 1.5    # Z position in mm
        self.rx_pos = 0.0   # Rotation around X-axis in radians
        self.ry_pos = 0.0   # Rotation around Y-axis in radians
        self.rz_pos = 0.0   # Rotation around Z-axis in radians
        self.xbot_state = None  # Will be set to default state after creation
        self.is_moving = False


# Global dictionary to store multiple simulated XBots
simulated_xbots = {}

def get_or_create_xbot(xbot_id):
    """Get or create a simulated XBot for the given ID"""
    if xbot_id not in simulated_xbots:
        xbot = SimulatedXBot()
        xbot.xbot_state = XbotState.XBOT_IDLE  # Set default state
        simulated_xbots[xbot_id] = xbot
    return simulated_xbots[xbot_id]

# system_commands class simulates system-level PMC commands



class XbotState(IntEnum):
    """XBot state enum for mock implementation"""
    XBOT_PREVIEW = -2
    XBOT_UNKNOWN = -1
    XBOT_UNDETECTED = 0
    XBOT_DISCOVERING = 1
    XBOT_LANDED = 2
    XBOT_IDLE = 3
    XBOT_DISABLED = 4
    XBOT_MOTION = 5
    XBOT_WAIT = 6
    XBOT_STOPPING = 7
    XBOT_OBSTACLE_DETECTED = 8
    XBOT_HOLDPOSITION = 9
    XBOT_STOPPED = 10
    XBOT_RESERVED = 11
    XBOT_RESERVED1 = 12
    XBOT_RESERVED2 = 13
    XBOT_ERROR = 14
    XBOT_UNINSTALLED = 15


class XbotType(IntEnum):
    """XBot type enum for mock implementation"""
    XBOT_TYPE_UNKNOWN = 0
    XBOT_TYPE_STANDARD = 1
    XBOT_TYPE_ROTARY = 2


class XbotStatus:
    """Mock XBot status class that mimics the real PMCLib XbotStatus"""
    def __init__(self, xbot_info, state=None):
        self.x_pos = xbot_info.x_pos
        self.y_pos = xbot_info.y_pos
        self.z_pos = xbot_info.z_pos
        self.rx_pos = xbot_info.rx_pos
        self.ry_pos = xbot_info.ry_pos
        self.rz_pos = xbot_info.rz_pos
        self.xbot_state = state if state is not None else XbotState.XBOT_IDLE
        self.xbot_id = 0
        self.xbot_type = XbotType.XBOT_TYPE_STANDARD
        self.cmd_label = 0
        self.force_mode = False
        self.motion_buffer_blocked = False
        self.buffered_motion_count = 0
        self.connected_to_group = False
        self.connected_group_id = -1


class FeedbackType(IntEnum):
    """Feedback type enum for mock implementation"""
    POSITION = 0
    FORCE = 1


class LevitateOptions(IntEnum):
    """Levitation options enum for mock implementation"""
    LAND = 0
    LEVITATE = 1


class LEVITATIONOPTIONS(IntEnum):
    """PMCLib style levitation options enum"""
    LAND = 0
    LEVITATE = 1


# Mock PMCLIB module to mimic the real PMCLib structure
class PMCLIB:
    class LEVITATIONOPTIONS(IntEnum):
        LAND = 0
        LEVITATE = 1
    
    class FEEDBACKOPTION(IntEnum):
        POSITION = 0
        FORCE = 1


# Mock pmc_types module structure
class pm:
    class LevitateOptions(IntEnum):
        LAND = 0
        LEVITATE = 1
    
    class FeedbackType(IntEnum):
        POSITION = 0
        FORCE = 1
    
    class PmcError(Exception):
        """PMC Error exception"""
        pass


def assert_type(value, expected_type, name):
    """Mock assert_type function"""
    if not isinstance(value, expected_type):
        raise TypeError(f"{name} must be of type {expected_type.__name__}")


# Initialize default xbot_state (will be applied to each XBot as they're created)
default_xbot_state = XbotState.XBOT_IDLE

class system_commands:
    @staticmethod
    def connect_to_pmc(ip):
        # Simulate connecting to the PMC system
        log_msg(f"Mock: Connecting to PMC at {ip}")
        return True  # Always return success in mock version

    @staticmethod
    def get_pmc_status():
        # Simulate getting PMC status, always return full control
        return pmc_types.PmcStatus.PMC_FULLCTRL

# xbot_commands class simulates XBot-specific commands


class xbot_commands:
    @staticmethod
    def get_all_xbot_info(xbot_id):
        # Return information about the specific XBot or all XBots
        if xbot_id == 0:
            # Return all XBots
            return list(simulated_xbots.values()) if simulated_xbots else []
        else:
            # Return specific XBot
            xbot = get_or_create_xbot(xbot_id)
            return [xbot]

    @staticmethod
    def get_xbot_status(xbot_id, feedback_type=FeedbackType.POSITION):
        """Get XBot status including state information"""
        # If xbot_id is 0, return status for first available XBot
        if xbot_id == 0 and simulated_xbots:
            xbot_id = next(iter(simulated_xbots.keys()))
        
        xbot = get_or_create_xbot(xbot_id)
        status = XbotStatus(xbot, xbot.xbot_state)
        status.xbot_id = xbot_id
        return status

    @staticmethod
    def activate_xbots():
        # Simulate activating all XBots
        log_msg("Mock: Activating XBots")

    @staticmethod
    def deactivate_xbots():
        # Simulate deactivating all XBots
        log_msg("Mock: Deactivating XBots")

    @staticmethod
    def levitation_command(xbot_id, lev_mode):
        """Levitate or land Xbot(s) - Mock implementation
        
        Parameters
        ----------
        xbot_id : int
            0 = all XBots, otherwise, XBot ID of a single XBot
        lev_mode : pm.LevitateOptions or int
            land or levitate option
        """
        # Handle both enum and integer inputs
        if hasattr(lev_mode, 'value'):
            lev_mode_int = lev_mode.value
        else:
            lev_mode_int = int(lev_mode)
        
        action = "levitate" if lev_mode_int == 1 else "land"
        
        if xbot_id == 0:
            log_msg(f"Mock: {action.capitalize()} all XBots (xbot_id: {xbot_id}, mode: {lev_mode_int})")
            # Apply to all existing XBots
            for xbot in simulated_xbots.values():
                if lev_mode_int == 1:  # LEVITATE
                    xbot.xbot_state = XbotState.XBOT_IDLE
                else:  # LAND
                    xbot.xbot_state = XbotState.XBOT_LANDED
        else:
            log_msg(f"Mock: {action.capitalize()} XBot {xbot_id} (mode: {lev_mode_int})")
            xbot = get_or_create_xbot(xbot_id)
            # Update XBot state based on levitation command
            if lev_mode_int == 1:  # LEVITATE
                xbot.xbot_state = XbotState.XBOT_IDLE
            else:  # LAND
                xbot.xbot_state = XbotState.XBOT_LANDED

    @staticmethod
    def linear_motion_si(xbot_id, x_pos, y_pos, xy_max_speed, xy_max_accl):
        # Simulate linear motion by updating XBot position
        log_msg(f"Mock: Linear motion for XBot {xbot_id}")
        xbot = get_or_create_xbot(xbot_id)
        xbot.is_moving = True
        xbot.xbot_state = XbotState.XBOT_MOTION
        
        # Calculate realistic travel time based on distance and speed
        current_x = xbot.x_pos
        current_y = xbot.y_pos
        distance = math.sqrt((x_pos - current_x)**2 + (y_pos - current_y)**2)
        travel_time = max(distance / xy_max_speed, LINEAR_MIN_TRAVEL_TIME_S)  # Minimum 200ms
        
        _schedule_motion_completion(
            xbot=xbot,
            travel_time_s=travel_time,
            updates={"x_pos": x_pos, "y_pos": y_pos},
            completion_message=f"Mock: Linear motion completed for XBot {xbot_id}",
        )
        return travel_time

    @staticmethod
    def six_d_of_motion_si(xbot_id, x_pos, y_pos, z_pos, rx_pos, ry_pos, rz_pos,
                           xy_max_speed, xy_max_accl, z_max_speed, rx_max_speed, ry_max_speed, rz_max_speed):
        # Simulate 6-degree-of-freedom motion by updating all position and orientation values
        log_msg(f"Mock: 6D motion for XBot {xbot_id}")
        xbot = get_or_create_xbot(xbot_id)
        xbot.is_moving = True
        xbot.xbot_state = XbotState.XBOT_MOTION
        
        _schedule_motion_completion(
            xbot=xbot,
            travel_time_s=SIX_D_TRAVEL_TIME_S,
            updates={
                "x_pos": x_pos,
                "y_pos": y_pos,
                "z_pos": z_pos,
                "rx_pos": rx_pos,
                "ry_pos": ry_pos,
                "rz_pos": rz_pos,
            },
        )
        return SIX_D_TRAVEL_TIME_S  # Return estimated travel time

    @staticmethod
    def arc_motion_target_radius(xbot_id, x_pos, y_pos, arc_type, postion_mode, arc_dir,
                                 radius_meters, xy_max_speed, xy_max_accl, final_speed):
        # Simulate arc motion by updating final XBot position
        log_msg(f"Mock: Arc motion for XBot {xbot_id}")
        xbot = get_or_create_xbot(xbot_id)
        xbot.is_moving = True
        xbot.xbot_state = XbotState.XBOT_MOTION
        
        # Calculate realistic travel time based on arc distance
        current_x = xbot.x_pos
        current_y = xbot.y_pos
        distance = math.sqrt((x_pos - current_x)**2 + (y_pos - current_y)**2)
        travel_time = (
            max((distance * ARC_TRAVEL_FACTOR) / xy_max_speed, ARC_MIN_TRAVEL_TIME_S)
            if xy_max_speed > 0 else ARC_FALLBACK_TRAVEL_TIME_S
        )
        
        _schedule_motion_completion(
            xbot=xbot,
            travel_time_s=travel_time,
            updates={"x_pos": x_pos, "y_pos": y_pos},
            completion_message=f"Mock: Arc motion completed for XBot {xbot_id}",
        )
        return travel_time

    @staticmethod
    def rotary_motion(xbot_id, target_rz, max_speed, max_accel):
        # Simulate rotary motion by updating Z-rotation
        log_msg(f"Mock: Rotary motion for XBot {xbot_id}")
        xbot = get_or_create_xbot(xbot_id)
        xbot.is_moving = True
        xbot.xbot_state = XbotState.XBOT_MOTION
        
        # Calculate realistic travel time based on rotation angle and speed
        current_rz = xbot.rz_pos
        rotation_angle = abs(target_rz - current_rz)
        travel_time = (
            max(rotation_angle / max_speed, ROTARY_MIN_TRAVEL_TIME_S)
            if max_speed > 0 else ROTARY_FALLBACK_TRAVEL_TIME_S
        )
        
        _schedule_motion_completion(
            xbot=xbot,
            travel_time_s=travel_time,
            updates={"rz_pos": target_rz},
            completion_message=f"Mock: Rotary motion completed for XBot {xbot_id}",
        )
        return travel_time

    @staticmethod
    def stop_motion(xbot_id):
        # Simulate stopping XBot motion
        log_msg(f"Mock: Stop motion for XBot {xbot_id}")
        if xbot_id == 0:
            # Stop all XBots
            for xbot in simulated_xbots.values():
                xbot.is_moving = False
                xbot.xbot_state = XbotState.XBOT_STOPPING
            
            def complete_stop():
                time.sleep(STOP_DELAY_S)  # Realistic stop delay
                for xbot in simulated_xbots.values():
                    xbot.xbot_state = XbotState.XBOT_IDLE
                log_msg(f"Mock: All XBots stopped and are now IDLE")
            
            threading.Thread(target=complete_stop, daemon=True).start()
        else:
            xbot = get_or_create_xbot(xbot_id)
            xbot.is_moving = False
            xbot.xbot_state = XbotState.XBOT_STOPPING
            
            def complete_stop():
                time.sleep(STOP_DELAY_S)  # Realistic stop delay
                xbot.xbot_state = XbotState.XBOT_IDLE
                log_msg(f"Mock: XBot {xbot_id} stopped and is now IDLE")
            
            threading.Thread(target=complete_stop, daemon=True).start()

# pmc_types class simulates PMC-specific data types
class pmc_types:
    class PmcStatus:
        # Enum-like class for PMC status
        PMC_FULLCTRL = "FULL_CONTROL"
    
    # Re-export the enums for compatibility
    XbotState = XbotState
    XbotType = XbotType
    FeedbackType = FeedbackType
    LevitateOptions = LevitateOptions
    
    class PmcError(Exception):
        """PMC Error exception for mock implementation"""
        pass


# MockPMCLib class provides a unified interface for testing
class MockPMCLib:
    """Mock PMCLib for testing and development without hardware dependencies"""

    def __init__(self):
        """Initialize the mock PMC library"""
        self.connected = False

    def connect(self, ip_address="192.168.1.100"):
        """Mock connection to PMC system"""
        self.connected = system_commands.connect_to_pmc(ip_address)
        return self.connected

    def get_status(self):
        """Get mock PMC status"""
        return system_commands.get_pmc_status()

    def create_xbot(self, xbot_id=1):
        """Create a mock XBot instance"""
        return get_or_create_xbot(xbot_id)

    def get_xbot_info(self, xbot_id=1):
        """Get XBot information"""
        return xbot_commands.get_all_xbot_info(xbot_id)

    def move_linear(self, xbot_id, x, y, z):
        """Mock linear motion"""
        xbot_commands.linear_motion_si(xbot_id, x, y, z)

    def move_rotary(self, xbot_id, rz):
        """Mock rotary motion"""
        xbot_commands.rotary_motion(xbot_id, rz)

    def stop_motion(self, xbot_id):
        """Mock stop motion"""
        xbot_commands.stop_motion(xbot_id)
