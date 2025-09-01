import sys
import os

class PmcInterface:
    """
    A dedicated interface for all PMCLib interactions.
    It encapsulates the logic for loading the real or mock library
    and provides a single point of access to its components.
    """
    def __init__(self, logger):
        """
        Initializes the interface and loads the appropriate PMCLib.
        
        Args:
            logger: The ROS 2 logger instance for logging messages.
        """
        self.logger = logger
        self.bot = None
        self.sys_cmd = None
        self.pmc_types = None
        self.status = {'source': 'uninitialized', 'is_mock': True}
        self._load_pmclib()

    def _load_pmclib(self):
        """
        Smartly loads the real or mock PMCLib using a clear priority:
        1. Local developer version (relative import)
        2. System-installed version
        3. Mock version (fallback)
        """
        # 1. Attempt to load local developer version using a robust relative import
        try:
            # This import tells Python exactly where to look within our package
            from .drivers.match_pm_xBot import xbot_commands, system_commands
            
            self.bot, self.sys_cmd = xbot_commands, system_commands
            self.status = {'source': 'local_driver', 'is_mock': False}
            self.logger.info("✅ Loaded local PMCLib driver from 'drivers/match_pm_xBot'.")
            return
        except ImportError as e:
            self.logger.debug(f"Did not load local PMCLib (this is normal if not present): {e}")
            pass # Fallback to next method

        # 2. Attempt to load system-installed PMCLib
        try:
            from pmclib import xbot_commands, system_commands, pmc_types
            self.bot, self.sys_cmd, self.pmc_types = xbot_commands, system_commands, pmc_types
            self.status = {'source': 'installed_pmclib', 'is_mock': False}
            self.logger.info("✅ Loaded system-installed PMCLib.")
            return
        except ImportError:
            pass # Fallback to mock

        # 3. Final fallback: Load mock library
        from .drivers import mock_pmclib
        self.bot, self.sys_cmd, self.pmc_types = \
            mock_pmclib.xbot_commands, mock_pmclib.system_commands, mock_pmclib.pmc_types
        self.status = {'source': 'mock', 'is_mock': True}
        self.logger.warning("⚠️ Using MOCK PMCLib for development. No hardware connection will be made.")

    def connect(self, ip_address: str) -> bool:
        """Tries to connect to the PMC ONCE and returns the status."""
        success = self.sys_cmd.connect_to_pmc(ip_address)
        return success