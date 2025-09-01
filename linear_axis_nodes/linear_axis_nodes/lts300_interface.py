from .drivers.thorlabs_lts300_driver import ThorlabsLTS300Driver
from .drivers.simulated_linear_axis_driver import SimulatedLinearAxisDriver

class Lts300Interface:
    """
    A dedicated interface for all Thorlabs LTS300 driver interactions.
    It handles the selection between the real and simulated driver and manages the connection.
    """
    def __init__(self, logger, config):
        """
        Initializes the interface and selects the appropriate driver.
        
        Args:
            logger: The ROS 2 logger instance.
            config: The Lts300Config dataclass holding all parameters.
        """
        self.logger = logger
        self.config = config
        self.driver = None
        self.is_connected = False

        if self.config.use_sim_time:
            self.driver = SimulatedLinearAxisDriver()
            self.logger.info("🔧 Using basic simulation driver for LTS300.")
        else:
            self.driver = ThorlabsLTS300Driver()
            self.logger.info("🔌 Using Thorlabs LTS300 hardware driver.")

    def connect(self) -> bool:
        """
        Connects to the physical or simulated device using parameters from the config.
        Returns True on success, False on failure.
        """
        if not self.driver:
            self.logger.error("❌ Driver not initialized.")
            return False

        self.logger.info(f"🔗 Connecting to device with S/N {self.config.serial_number} on port {self.config.serial_port}...")
        
        # NOTE: The driver's connect method needs to be adapted to only take the specific serial number.
        # For now, we pass all known serials, and the driver can pick the right one.
        # A cleaner driver would accept `connect(port, serial_to_find)`.
        connected = self.driver.connect(
            serial_port=self.config.serial_port,
            serial_number=self.config.serial_number,
            debug_mode=self.config.debug_mode
        )

        if connected:
            self.logger.info(f"✅ Successfully connected to {self.driver.get_axis_type()}-axis (S/N: {self.driver.get_serial_number()}).")
            self.is_connected = True
        else:
            self.logger.error(f"❌ Failed to connect to device with S/N {self.config.serial_number}.")
            self.is_connected = False
            
        return self.is_connected
        
    def disconnect(self):
        """Disconnects from the device."""
        if self.driver and self.is_connected:
            self.driver.disconnect()
            self.is_connected = False
            self.logger.info("✅ Device disconnected.")