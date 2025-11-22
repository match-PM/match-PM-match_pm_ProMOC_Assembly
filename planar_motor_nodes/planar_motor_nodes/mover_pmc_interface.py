
import sys
import os
from promoc_core.promoc_exceptions import ConnectionError, DriverNotAvailableError

class PmcInterface:
    """
    A dedicated interface for all PMCLib interactions.
    It encapsulates the logic for loading the real or mock library
    and provides a single point of access to its components.
    """
    def __init__(self, logger, use_mock: bool = False):
        """
        Initializes the interface and loads the appropriate PMCLib.
        
        Args:
            logger: The ROS 2 logger instance for logging messages.
            use_mock (bool): If True, forces the use of the mock library.
        """
        self.logger = logger
        self.bot = None
        self.force_mock = use_mock
        self.sys_cmd = None
        self.pmc_types = None
        self.status = {'source': 'uninitialized', 'is_mock': True}
        self._load_pmclib()

    def _load_pmclib(self) -> None:
        """
        Smartly loads the real or mock PMCLib using a clear priority:
        0. Force mock if specified via parameter
        1. Local developer version (relative import)
        2. System-installed version
        3. Mock version (fallback)
        """
        if self.force_mock:
            self._load_mock_lib()
            self.logger.warning("Forcing MOCK PMCLib as per launch configuration.")
            return

        # Priority 1: Attempt to load local developer version
        try:
            from .drivers.match_pm_xBot import xbot_commands, system_commands, pmc_types
            self.bot, self.sys_cmd, self.pmc_types = xbot_commands, system_commands, pmc_types
            self.status = {'source': 'local_driver', 'is_mock': False}
            self.logger.info("Loaded local PMCLib driver from 'drivers/match_pm_xBot'.")
            return
        except ImportError:
            self.logger.debug("Local PMCLib driver not found, trying system-installed version.")

        # Priority 2: Attempt to load system-installed version
        if self._load_installed_lib():
            return

        # Priority 3: Fallback to mock library
        self.logger.warning("Real PMCLib not found. Falling back to MOCK implementation.")
        self._load_mock_lib()

    def _load_installed_lib(self) -> bool:
        """Tries to load the system-installed version."""
        try:
            from pmclib import xbot_commands, system_commands, pmc_types
            self.bot, self.sys_cmd, self.pmc_types = xbot_commands, system_commands, pmc_types
            self.status = {'source': 'installed_pmclib', 'is_mock': False}
            self.logger.info("Loaded system-installed PMCLib.")
            return True
        except ImportError:
            return False

    def _load_mock_lib(self) -> None:
        """Loads the mock library."""
        from .drivers import mock_pmclib
        self.bot, self.sys_cmd, self.pmc_types = \
            mock_pmclib.xbot_commands, mock_pmclib.system_commands, mock_pmclib.pmc_types
        self.status = {'source': 'mock', 'is_mock': True}
        self.logger.info("Loaded MOCK PMCLib for simulation.")

    def connect(self, ip_address: str) -> bool:
        """
        Tries to connect to the PMC ONCE.
        Raises ConnectionError if connection fails.
        """
        success = self.sys_cmd.connect_to_pmc(ip_address)
        if not success:
            raise ConnectionError(
                message=f"Failed to connect to PMC at {ip_address}",
                details={'ip_address': ip_address}
            )
        return True
