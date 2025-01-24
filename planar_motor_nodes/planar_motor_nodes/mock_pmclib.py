# SimulatedXBot class represents a virtual XBot with position and orientation attributes
class SimulatedXBot:
    def __init__(self):
        # Initialize default position and orientation values
        self.x_pos = 120.0  # X position in mm
        self.y_pos = 120.0  # Y position in mm
        self.z_pos = 1.5    # Z position in mm
        self.rx_pos = 0.0   # Rotation around X-axis in radians
        self.ry_pos = 0.0   # Rotation around Y-axis in radians
        self.rz_pos = 0.0   # Rotation around Z-axis in radians

# Create a global instance of SimulatedXBot
simulated_xbot = SimulatedXBot()

# system_commands class simulates system-level PMC commands
class system_commands:
    @staticmethod
    def connect_to_pmc(ip):
        # Simulate connecting to the PMC system
        print(f"Mock: Connecting to PMC at {ip}")
        return True  # Always return success in mock version

    @staticmethod
    def get_pmc_status():
        # Simulate getting PMC status, always return full control
        return pmc_types.PmcStatus.PMC_FULLCTRL

# xbot_commands class simulates XBot-specific commands
class xbot_commands:
    @staticmethod
    def get_all_xbot_info(xbot_id):
        # Return information about all XBots (in this case, just one)
        return [simulated_xbot]

    @staticmethod
    def activate_xbots():
        # Simulate activating all XBots
        print("Mock: Activating XBots")

    @staticmethod
    def deactivate_xbots():
        # Simulate deactivating all XBots
        print("Mock: Deactivating XBots")

    @staticmethod
    def levitate_xbot_command(xbot_id, command):
        # Simulate levitation command for a specific XBot
        print(f"Mock: Levitate XBot {xbot_id} command: {command}")

    @staticmethod
    def linear_motion_si(xbot_id, x_pos, y_pos, xy_max_speed, xy_max_accl):
        # Simulate linear motion by updating XBot position
        print(f"Mock: Linear motion for XBot {xbot_id}")
        simulated_xbot.x_pos = x_pos
        simulated_xbot.y_pos = y_pos

    @staticmethod
    def six_d_of_motion_si(xbot_id, x_pos, y_pos, z_pos, rx_pos, ry_pos, rz_pos, 
                           xy_max_speed, xy_max_accl, z_max_speed, rx_max_speed, ry_max_speed, rz_max_speed):
        # Simulate 6-degree-of-freedom motion by updating all position and orientation values
        print(f"Mock: 6D motion for XBot {xbot_id}")
        simulated_xbot.x_pos = x_pos
        simulated_xbot.y_pos = y_pos
        simulated_xbot.z_pos = z_pos
        simulated_xbot.rx_pos = rx_pos
        simulated_xbot.ry_pos = ry_pos
        simulated_xbot.rz_pos = rz_pos

    @staticmethod
    def arc_motion_target_radius(xbot_id, x_pos, y_pos, arc_type, postion_mode, arc_dir,
                                 radius_meters, xy_max_speed, xy_max_accl, final_speed):
        # Simulate arc motion by updating final XBot position
        print(f"Mock: Arc motion for XBot {xbot_id}")
        # For simplicity, just set the final position
        simulated_xbot.x_pos = x_pos
        simulated_xbot.y_pos = y_pos

    @staticmethod
    def rotary_motion(xbot_id, target_rz, max_speed, max_accel):
        # Simulate rotary motion by updating Z-rotation
        print(f"Mock: Rotary motion for XBot {xbot_id}")
        simulated_xbot.rz_pos = target_rz

    @staticmethod
    def stop_motion(xbot_id):
        # Simulate stopping XBot motion
        print(f"Mock: Stop motion for XBot {xbot_id}")

# pmc_types class simulates PMC-specific data types
class pmc_types:
    class PmcStatus:
        # Enum-like class for PMC status
        PMC_FULLCTRL = "FULL_CONTROL"