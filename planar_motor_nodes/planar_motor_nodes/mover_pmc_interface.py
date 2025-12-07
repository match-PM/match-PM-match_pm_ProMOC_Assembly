"""
PMC Interface - Hardware-Abstraktion für den Planar Motor Controller.

Dieses Modul kapselt alle Interaktionen mit der PMCLib und bietet
eine einheitliche Schnittstelle, unabhängig davon ob die echte
Hardware oder ein Mock verwendet wird.

Funktionsweise (Library-Loading):
=================================
Das Interface versucht, die PMCLib in folgender Priorität zu laden:

    ┌─────────────────────────────────────────────────────────────┐
    │  0. Force Mock (wenn use_mock=True)                        │
    │     └── Nutzt sofort Mock, überspringt alle anderen        │
    │                                                             │
    │  1. Lokale Developer-Version                                │
    │     └── ./drivers/match_pm_xBot/                           │
    │     └── Für Entwicklung mit lokalen Änderungen             │
    │                                                             │
    │  2. System-installierte Version                             │
    │     └── import pmclib (via pip/apt installiert)            │
    │     └── Für Produktion                                      │
    │                                                             │
    │  3. Mock-Version (Fallback)                                 │
    │     └── ./drivers/mock_pmclib.py                           │
    │     └── Für Tests und Simulation ohne Hardware             │
    └─────────────────────────────────────────────────────────────┘

Komponenten nach dem Laden:
===========================
- bot (xbot_commands): Bewegungsbefehle (linear_motion, arc_motion, etc.)
- sys_cmd (system_commands): Systembefehle (connect_to_pmc, disconnect)
- pmc_types: Konstanten und Enums für PMC-Kommunikation

Verwendung:
===========
    # Normal (versucht echte Hardware):
    pmc = PmcInterface(logger)
    
    # Erzwinge Simulation:
    pmc = PmcInterface(logger, use_mock=True)
    
    # Verbinden:
    pmc.connect("192.168.10.100")
    
    # Bewegung ausführen:
    pmc.bot.linear_motion_si(xbot_id=0, x=0.1, y=0.05)
"""

import sys
import os
from promoc_core.promoc_exceptions import ConnectionError, DriverNotAvailableError


class PmcInterface:
    """
    Zentrale Schnittstelle für PMC-Controller-Kommunikation.

    Diese Klasse abstrahiert die Hardware-Ebene und ermöglicht:
    - Nahtloses Umschalten zwischen echter Hardware und Simulation
    - Einheitliche API für alle Bewegungsbefehle
    - Klare Fehlerbehandlung bei Verbindungsproblemen

    Attribute:
        bot: XBot-Befehle (Bewegungen, Aktivierung)
        sys_cmd: System-Befehle (Verbindung, Konfiguration)
        pmc_types: Konstanten für PMC-Kommunikation
        status (dict): Aktueller Status {'source': str, 'is_mock': bool}

    Beispiel:
        >>> pmc = PmcInterface(logger, use_mock=False)
        >>> pmc.connect("192.168.10.100")
        >>> pmc.bot.activate_xbots()
        >>> pmc.bot.linear_motion_si(0, 0.1, 0.05, ...)
    """

    def __init__(self, logger, use_mock: bool = False):
        """
        Initialisiert das Interface und lädt die passende PMCLib.

        Ablauf:
        -------
        1. Logger und Status initialisieren
        2. _load_pmclib() aufrufen → lädt echte oder Mock-Library

        Args:
            logger: ROS2-Logger für Log-Ausgaben
            use_mock: True = Mock erzwingen, False = echte Hardware bevorzugen
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
        Lädt die PMCLib nach Priorität (Mock → Lokal → Installiert → Fallback).

        Schritt-für-Schritt:
        --------------------
        1. Wenn force_mock=True → Mock laden, fertig
        2. Versuche lokale Version (drivers/match_pm_xBot/)
        3. Versuche installierte Version (import pmclib)
        4. Fallback: Mock-Version laden

        Nach erfolgreichem Laden sind bot, sys_cmd und pmc_types verfügbar.
        """
        # ── Schritt 0: Mock erzwingen falls angefordert ──
        if self.force_mock:
            self._load_mock_lib()
            self.logger.warning(
                "Forcing MOCK PMCLib as per launch configuration.")
            return

        # ── Schritt 1: Lokale Developer-Version ──
        try:
            from .drivers.match_pm_xBot import xbot_commands, system_commands, pmc_types
            self.bot, self.sys_cmd, self.pmc_types = xbot_commands, system_commands, pmc_types
            self.status = {'source': 'local_driver', 'is_mock': False}
            self.logger.info(
                "Loaded local PMCLib driver from 'drivers/match_pm_xBot'.")
            return
        except ImportError:
            self.logger.debug(
                "Local PMCLib driver not found, trying system-installed version.")

        # ── Schritt 2: System-installierte Version ──
        if self._load_installed_lib():
            return

        # ── Schritt 3: Fallback zu Mock ──
        self.logger.warning(
            "Real PMCLib not found. Falling back to MOCK implementation.")
        self._load_mock_lib()

    def _load_installed_lib(self) -> bool:
        """
        Versucht die system-installierte PMCLib zu laden.

        Returns:
            True wenn erfolgreich, False wenn nicht installiert
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
        Lädt die Mock-Library für Simulation ohne Hardware.

        Die Mock-Bibliothek simuliert alle Bewegungen und
        gibt realistische Positionen zurück.
        """
        from .drivers import mock_pmclib
        self.bot, self.sys_cmd, self.pmc_types = \
            mock_pmclib.xbot_commands, mock_pmclib.system_commands, mock_pmclib.pmc_types
        self.status = {'source': 'mock', 'is_mock': True}
        self.logger.info("Loaded MOCK PMCLib for simulation.")

    def connect(self, ip_address: str) -> bool:
        """
        Stellt Verbindung zum PMC-Controller her.

        Args:
            ip_address: IP-Adresse des PMC-Controllers (z.B. "192.168.10.100")

        Returns:
            True bei erfolgreicher Verbindung

        Raises:
            ConnectionError: Wenn Verbindung fehlschlägt
        """
        success = self.sys_cmd.connect_to_pmc(ip_address)
        if not success:
            raise ConnectionError(
                message=f"Failed to connect to PMC at {ip_address}",
                details={'ip_address': ip_address}
            )
        return True
