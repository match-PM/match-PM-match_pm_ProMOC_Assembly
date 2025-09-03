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
        """Connects to the device."""
        try:
            self.logger.info(f"🔗 Connecting to device with S/N {self.config.serial_number} on port {self.config.serial_port}...")
            
            if self.config.use_sim_time:
                # Simulation mode
                connected = self.driver.connect()
                if connected:
                    self.logger.info("🎮 Connected in simulation mode.")
            else:
                # Hardware mode - übergebe port als Parameter
                connected = self.driver.connect(port=self.config.serial_port)
                if connected:
                    # Prüfe, ob die Seriennummer übereinstimmt
                    device_serial = self.driver.get_serial_number()
                    if device_serial != self.config.serial_number:
                        self.logger.warning(f"⚠️ Expected S/N {self.config.serial_number}, but device reports {device_serial}")
                    self.logger.info(f"🔌 Connected to Thorlabs LTS300 (S/N: {device_serial})")
                    
            self._is_connected = connected
            return connected
            
        except Exception as e:
            self.logger.error(f"❌ Connection failed: {e}")
            self._is_connected = False
            return False
            
    def disconnect(self):
        """Disconnects from the device."""
        if self.driver and self.is_connected:
            self.driver.disconnect()
            self.is_connected = False
            self.logger.info("✅ Device disconnected.")