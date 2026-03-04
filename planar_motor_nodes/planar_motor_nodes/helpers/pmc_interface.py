"""
PMC Interface - Hardware abstraction for the Planar Motor Controller.

This module encapsulates all interactions with PMCLib and provides a unified
interface regardless of whether real hardware or a mock is being used.

How it works (Library Loading Priority):
========================================
    ┌─────────────────────────────────────────────────────────────┐
    │  0. Force Mock (if use_mock=True)                           │
    │     └── Uses mock immediately, skips all other options      │
    │                                                             │
    │  1. Local Developer Version                                 │
    │     └── ./drivers/match_pm_xBot/                            │
    │     └── For development with local modifications            │
    │                                                             │
    │  2. System-installed Version                                │
    │     └── import pmclib (via pip/apt installed)               │
    │     └── For production                                      │
    │                                                             │
    │  3. Mock Version (Fallback)                                 │
    │     └── ./drivers/mock_pmclib.py                            │
    │     └── For testing and simulation without hardware         │
    └─────────────────────────────────────────────────────────────┘

Components after loading:
=========================
- bot (xbot_commands): Motion commands (linear_motion, arc_motion, etc.)
- sys_cmd (system_commands): System commands (connect_to_pmc, disconnect)
- pmc_types: Constants and enums for PMC communication

Usage:
======
    # Normal (tries real hardware first):
    pmc = PmcInterface(logger)
    
    # Force simulation:
    pmc = PmcInterface(logger, use_mock=True)
    
    # Connect:
    pmc.connect("192.168.10.100")
    
    # Execute motion:
    pmc.bot.linear_motion_si(xbot_id=0, x=0.1, y=0.05)
"""

from promoc_core.promoc_exceptions import ConnectionError
from promoc_core.logging import TaggedLogger, LogTags


class PmcInterface:
    """
    Central interface for PMC controller communication.

    This class abstracts the hardware layer and enables:
    - Seamless switching between real hardware and simulation
    - Unified API for all motion commands
    - Clear error handling for connection issues

    Attributes:
        bot: XBot commands (motion, activation)
        sys_cmd: System commands (connection, configuration)
        pmc_types: Constants for PMC communication
        status (dict): Current status {'source': str, 'is_mock': bool}

    Example:
        >>> pmc = PmcInterface(logger, use_mock=False)
        >>> pmc.connect("192.168.10.100")
        >>> pmc.bot.activate_xbots()
        >>> pmc.bot.linear_motion_si(0, 0.1, 0.05, ...)
    """

    def __init__(self, logger, use_mock: bool = False):
        """
        Initialize the interface and load the appropriate PMCLib.

        Flow:
        -----
        1. Initialize logger and status
        2. Call _load_pmclib() → loads real or mock library

        Args:
            logger: ROS2 logger for log output
            use_mock: True = force mock, False = prefer real hardware
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
        Load PMCLib by priority (Mock → Local → Installed → Fallback).

        Step-by-step:
        --------------
        1. If force_mock=True → load mock, done
        2. Try local version (drivers/match_pm_xBot/)
        3. Try installed version (import pmclib)
        4. Fallback: load mock version

        After successful loading, bot, sys_cmd, and pmc_types are available.
        """
        # Step 0: Force mock if requested
        if self.force_mock:
            self._load_mock_lib()
            self.logger.warning(
                "Forcing MOCK PMCLib as per launch configuration.")
            return

        # Step 1: Local developer version
        try:
            from ..drivers.match_pm_xBot import (
                xbot_commands,
                system_commands,
                pmc_types,
            )
            self.bot, self.sys_cmd, self.pmc_types = xbot_commands, system_commands, pmc_types
            self.status = {'source': 'local_driver', 'is_mock': False}
            self.logger.info(
                "Loaded local PMCLib driver from 'drivers/match_pm_xBot'.")
            return
        except ImportError:
            self.logger.debug(
                "Local PMCLib driver not found, trying system-installed version.")

        # Step 2: System-installed version
        if self._load_installed_lib():
            return

        # Step 3: Fallback to mock
        self.logger.warning(
            "Real PMCLib not found. Falling back to MOCK implementation.")
        self._load_mock_lib()

    def _load_installed_lib(self) -> bool:
        """
        Try to load the system-installed PMCLib.

        Returns:
            True if successful, False if not installed
        """
        try:
            from pmclib import xbot_commands, system_commands, pmc_types
            self.bot, self.sys_cmd, self.pmc_types = xbot_commands, system_commands, pmc_types
            self.status = {'source': 'installed_pmclib', 'is_mock': False}
            self.logger.info("Loaded system-installed PMCLib.")
            return True
        except ImportError:
            return False

    def _load_mock_lib(self) -> None:
        """
        Load the mock library for simulation without hardware.

        The mock library simulates all movements and returns realistic positions.
        """
        from ..drivers import mock_pmclib
        # Create a specific logger for the mock library
        mock_lib_logger = TaggedLogger(self.logger._logger, LogTags.MOCK)
        mock_pmclib.set_logger(mock_lib_logger)
        
        self.bot, self.sys_cmd, self.pmc_types = \
            mock_pmclib.xbot_commands, mock_pmclib.system_commands, mock_pmclib.pmc_types
        self.status = {'source': 'mock', 'is_mock': True}
        self.logger.info("Loaded MOCK PMCLib for simulation.")

    def connect(self, ip_address: str) -> bool:
        """
        Establish connection to the PMC controller.

        Args:
            ip_address: IP address of PMC controller (e.g., "192.168.10.100")

        Returns:
            True on successful connection

        Raises:
            ConnectionError: If connection fails
        """
        success = self.sys_cmd.connect_to_pmc(ip_address)
        if not success:
            raise ConnectionError(
                message=f"Failed to connect to PMC at {ip_address}",
                details={'ip_address': ip_address}
            )
        return True
