"""
Hardware abstraction for Thorlabs LTS300 linear axis.

Encapsulates access to LTS300 behind a stable Python API.
Supports seamless switching between simulation and real hardware.

Configuration via ROS parameters:
- use_sim_time: True → SimulatedLinearAxisDriver
- use_sim_time: False → ThorlabsLTS300Driver
"""

from .drivers.simulated_linear_axis_driver import SimulatedLinearAxisDriver


class Lts300Interface:
    """
    Central interface for LTS300 linear axis communication.

    Abstracts hardware layer and enables:
    - Seamless switching between simulation and real hardware
    - Unified API for all motion commands
    - Clean error handling for connection issues

    Attributes:
        driver: Active driver (simulation or hardware)
        is_connected (bool): True if connected

    Example:
        >>> interface = Lts300Interface(logger, config)
        >>> if interface.connect():
        ...     pos = interface.driver.get_position()
        ...     interface.driver.move_absolute(100.0)
    """

    def __init__(self, logger, config):
        """Initialize interface and select appropriate driver."""
        self.logger = logger
        self.config = config
        self.driver = None
        self.is_connected = False

        if self.config['use_sim_time']:
            self.driver = SimulatedLinearAxisDriver()
            self.logger.info('Using basic simulation driver for LTS300')
        else:
            from .drivers.thorlabs_lts300_driver import ThorlabsLTS300Driver
            self.driver = ThorlabsLTS300Driver(logger)
            self.logger.info('Using Thorlabs LTS300 hardware driver')

    def connect(self) -> bool:
        """
        Connect to device.

        Returns:
            True on success, False otherwise.
        """
        try:
            serial = self.config['serial_number']
            port = self.config['serial_port']
            self.logger.info(
                f'Connecting to device with S/N {serial} on port {port}...'
            )

            if self.config['use_sim_time']:
                connected = self.driver.connect()
                if connected:
                    self.logger.info('Connected in simulation mode')
            else:
                connected = self.driver.connect(port=port)
                if connected:
                    device_serial = self.driver.get_serial_number()
                    if device_serial != serial:
                        self.logger.warn(
                            f'Expected S/N {serial}, but device reports {device_serial}'
                        )
                    self.logger.info(
                        f'Connected to Thorlabs LTS300 (S/N: {device_serial})'
                    )

                    poll_interval = self.config.get('position_poll_interval_s', 0.1)
                    if hasattr(self.driver, 'start_position_polling') and poll_interval and poll_interval > 0:
                        self.driver.start_position_polling(poll_interval)

            self.is_connected = connected
            return connected

        except Exception as e:
            self.logger.error(f'Connection failed: {e}')
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from device cleanly."""
        if self.driver and self.is_connected:
            self.driver.disconnect()
            self.is_connected = False
            self.logger.info('Device disconnected')
