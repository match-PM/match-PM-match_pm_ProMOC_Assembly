"""
Mover Utilities - Hilfsfunktionen für XBot Positionsmanagement.

Dieses Modul enthält die MoverUtils-Klasse mit allen Hilfsfunktionen
für Positionsabfragen, Bewegungsüberwachung und Einheitenkonvertierung.

Funktionsübersicht:
==================

Position & Status:
------------------
- get_current_position(xbot_id) → [x, y, z, rx, ry, rz] in SI
- get_xbot_status_info(xbot_id) → dict mit Position und State
- get_xbot_state_string(xbot_id) → "IDLE", "MOVING", etc.

Bewegungsüberwachung:
---------------------
- wait_for_motion_completion() → MotionStatus (COMPLETED, TIMEOUT, ERROR)
- is_position_in_bounds(x, y, z) → True/False

Einheiten-Konvertierung:
------------------------
- mm_to_m(value) → value / 1000
- m_to_mm(value) → value * 1000
- deg_to_rad(value) → value * π/180
- rad_to_deg(value) → value * 180/π

Konfiguration:
--------------
- get_speed_params(xbot_id) → dict mit Geschwindigkeiten/Beschleunigungen

Verwendungsbeispiel:
====================
    utils = MoverUtils(logger, pmc_interface, config)
    
    # Position abfragen
    pos = utils.get_current_position(0)
    print(f"XBot ist bei x={pos[0]*1000:.1f}mm, y={pos[1]*1000:.1f}mm")
    
    # Bewegung überwachen
    result = utils.wait_for_motion_completion(
        xbot_id=0,
        target_pos=[0.1, 0.05, 0.001, 0, 0, 0],
        tolerance=0.001,
        timeout=10.0
    )
    if result == MotionStatus.COMPLETED:
        print("Ziel erreicht!")
"""

import time
import math
from typing import List, Optional
from enum import Enum

# Explizite Importe für saubere Architektur
from .mover_pmc_interface import PmcInterface
from .mover_node_config import NodeConfig
# XbotState aus Mock (garantiert vorhanden)
from .drivers.mock_pmclib import XbotState

# Gemeinsame Utilities aus promoc_core
from promoc_core.motion import MotionStatus, check_position_reached
from promoc_core.validation import is_in_range, validate_id_range
from promoc_core.conversions import rad_to_deg, mm_to_m, m_to_mm


class MoverUtils:
    """
    Hilfsfunktionen für XBot-Positionsmanagement und Bewegungsüberwachung.

    Diese Klasse ist von ROS2 entkoppelt und kann unabhängig getestet werden.
    Sie wird vom MoverServiceNode und ServiceCallbacks verwendet.

    Hauptfunktionen:
    ----------------
    1. Position abfragen: get_current_position()
    2. Bewegung überwachen: wait_for_motion_completion()
    3. Grenzen prüfen: is_position_in_bounds()
    4. Einheiten konvertieren: mm_to_m(), deg_to_rad(), etc.

    Attribute:
        logger: ROS2-Logger für Ausgaben
        pmc (PmcInterface): Hardware-Schnittstelle
        config (NodeConfig): Konfiguration mit Bounds
        is_mock (bool): True wenn Mock-Modus aktiv
        velocity_params (dict): Geschwindigkeitsparameter pro XBot
    """

    def __init__(self, logger, pmc_interface: PmcInterface, config: NodeConfig):
        """
        Initialisiert die Utilities mit Abhängigkeiten.

        Args:
            logger: ROS2-Logger
            pmc_interface: Hardware-Schnittstelle
            config: Konfiguration mit Bounds und Toleranzen
        """
        self.logger = logger
        self.pmc = pmc_interface
        self.config = config
        self.is_mock = self.pmc.status['is_mock']
        self._logged_no_data = False
        self._logged_warnings = set()

    # ══════════════════════════════════════════════════════════════════════════
    # EINHEITEN-KONVERTIERUNG
    # ══════════════════════════════════════════════════════════════════════════

    def mm_to_m(self, value_mm: float) -> float:
        """Konvertiert Millimeter zu Meter."""
        return mm_to_m(value_mm)

    def m_to_mm(self, value_m: float) -> float:
        """Konvertiert Meter zu Millimeter."""
        return m_to_mm(value_m)

    # ══════════════════════════════════════════════════════════════════════════
    # POSITIONS-ABFRAGEN
    # ══════════════════════════════════════════════════════════════════════════

    def get_current_position(self, xbot_id: int = 0) -> Optional[List[float]]:
        """
        Fragt die aktuelle XBot-Position vom PMC-Controller ab.

        Args:
            xbot_id: ID des XBots (Standard: 0)

        Returns:
            Liste [x, y, z, rx, ry, rz] in SI-Einheiten (m, rad)
            None wenn keine Daten verfügbar

        Ablauf:
        -------
        1. XBot-Daten vom PMC holen
        2. Prüfen ob angeforderte ID verfügbar
        3. Position als Liste zurückgeben
        """
        try:
            xbot_data_list = self.pmc.bot.get_xbot_data()

            if not xbot_data_list:
                if not self._logged_no_data:
                    self.logger.error("No XBot data returned from PMCLib")
                    self._logged_no_data = True
                return None

            if xbot_id >= len(xbot_data_list):
                warning_key = f"xbot_{xbot_id}_unavailable"
                if warning_key not in self._logged_warnings:
                    self.logger.warning(
                        f"XBot {xbot_id} not available. Available: {len(xbot_data_list)}. "
                        f"Using XBot 0 as fallback.")
                    self._logged_warnings.add(warning_key)
                xbot_id = 0

            xbot_data = xbot_data_list[xbot_id]
            position = [
                float(xbot_data.x_pos), float(
                    xbot_data.y_pos), float(xbot_data.z_pos),
                float(xbot_data.rx_pos), float(
                    xbot_data.ry_pos), float(xbot_data.rz_pos)
            ]
            return position

        except Exception as e:
            if not self.is_mock:
                self.logger.error(
                    f"Error in get_current_position for XBot {xbot_id}: {e}", exc_info=True)
            return None

    def get_xbot_status_info(self, xbot_id: int = 0) -> Optional[dict]:
        """
        Holt umfassende Status-Informationen für einen XBot.

        Args:
            xbot_id: ID des XBots

        Returns:
            dict mit:
            - 'position': [x, y, z, rx, ry, rz]
            - 'xbot_state': XbotState Enum
            - 'xbot_state_string': "IDLE", "MOVING", etc.
        """
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
                    self.logger.warning(
                        f"Could not get status for XBot {xbot_id}: {e}")
                xbot_state_enum = XbotState.XBOT_UNKNOWN
                xbot_state_str = "UNKNOWN"

            return {
                'position': current_pos,
                'xbot_state': xbot_state_enum,
                'xbot_state_string': xbot_state_str,
            }
        except Exception as e:
            if not self.is_mock:
                self.logger.error(
                    f"Error getting XBot status info: {e}", exc_info=True)
            return None

    def get_xbot_state_string(self, xbot_id: int = 0) -> str:
        """
        Gibt den XBot-Status als lesbaren String zurück.

        Mögliche Rückgabewerte:
        - "IDLE": Bereit für Befehle
        - "MOVING": In Bewegung
        - "ERROR": Fehler aufgetreten
        - "STOPPED": Gestoppt
        - "UNKNOWN": Status unbekannt
        """
        try:
            xbot_status = self.pmc.bot.get_xbot_status(xbot_id)
            return self._xbot_state_to_string(xbot_status.xbot_state)
        except Exception:
            return "IDLE"

    def _xbot_state_to_string(self, xbot_state) -> str:
        """Konvertiert XbotState-Enum zu lesbarem String."""
        try:
            if hasattr(xbot_state, 'name'):
                return xbot_state.name
            else:
                state_map = {v.value: v.name for v in XbotState}
                return state_map.get(int(xbot_state), "UNKNOWN")
        except:
            return "UNKNOWN"

    # ══════════════════════════════════════════════════════════════════════════
    # BEWEGUNGS-ÜBERWACHUNG
    # ══════════════════════════════════════════════════════════════════════════

    def wait_for_motion_completion(self, xbot_id: int, target_position: List[float],
                                   position_tolerance: float, max_wait_time: float = 10.0) -> MotionStatus:
        """
        Wartet auf den Abschluss einer Bewegung.

        Polling-Loop, die alle 100ms den XBot-Status prüft.

        Args:
            xbot_id: ID des zu überwachenden XBots
            target_position: Zielposition [x, y, z, rx, ry, rz] (aktuell nur für Logging)
            position_tolerance: Toleranz in Metern (aktuell nicht verwendet)
            max_wait_time: Maximale Wartezeit in Sekunden

        Returns:
            MotionStatus:
            - COMPLETED: Bewegung erfolgreich beendet (State = IDLE)
            - TIMEOUT: max_wait_time überschritten
            - ERROR: Fehler während Bewegung (State = ERROR)

        Ablauf:
        -------
        1. Status in 100ms-Intervallen abfragen
        2. Bei IDLE → COMPLETED zurückgeben
        3. Bei ERROR → ERROR zurückgeben
        4. Bei Timeout → TIMEOUT zurückgeben
        """
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            state_str = self.get_xbot_state_string(xbot_id)

            if state_str in ["XBOT_IDLE", "IDLE"]:
                self.logger.info(f"Motion completed for XBot {xbot_id}.")
                return MotionStatus.COMPLETED

            if state_str in ["XBOT_ERROR", "ERROR", "XBOT_STOPPED"]:
                self.logger.error(
                    f"Motion error for XBot {xbot_id} - State: {state_str}")
                return MotionStatus.ERROR

            time.sleep(0.1)

        self.logger.warning(
            f"Motion timeout for XBot {xbot_id} after {max_wait_time:.1f}s")
        return MotionStatus.TIMEOUT

    # ══════════════════════════════════════════════════════════════════════════
    # GRENZEN UND VALIDIERUNG
    # ══════════════════════════════════════════════════════════════════════════

    def is_position_in_bounds(self, x: float, y: float, z: float) -> bool:
        """
        Prüft ob eine Position innerhalb der konfigurierten Grenzen liegt.

        Args:
            x, y, z: Position in Metern

        Returns:
            True wenn alle Koordinaten in Grenzen, False sonst

        Grenzen aus config:
            x: [x_min, x_max] (Standard: 0.055 - 0.420 m)
            y: [y_min, y_max] (Standard: 0.055 - 0.180 m)
            z: [z_min, z_max] (Standard: 0.000 - 0.004 m)
        """
        return (is_in_range(x, self.config.x_min, self.config.x_max) and
                is_in_range(y, self.config.y_min, self.config.y_max) and
                is_in_range(z, self.config.z_min, self.config.z_max))

    def validate_xbot_id(self, xbot_id: int) -> bool:
        """
        Validiert die XBot-ID (muss zwischen 0 und 15 liegen).

        Args:
            xbot_id: Zu prüfende ID

        Returns:
            True wenn gültig, False sonst
        """
        valid, error_msg = validate_id_range(
            xbot_id, min_id=0, max_id=15, name="XBot ID")
        if not valid:
            self.logger.error(error_msg)
        return valid

    def diagnose_xbot_availability(self) -> dict:
        """Diagnoses which XBots are available and responding."""
        diagnosis = {'available_xbots': [], 'total_from_get_all': 0}
        try:
            data_list = self.pmc.bot.get_all_xbot_info(0)
            diagnosis['total_from_get_all'] = len(
                data_list) if data_list else 0

            for xbot_id in range(4):  # Teste die ersten 4 IDs
                try:
                    status = self.pmc.bot.get_xbot_status(xbot_id)
                    diagnosis['available_xbots'].append({
                        'id': xbot_id, 'status': 'available',
                        'state': self._xbot_state_to_string(status.xbot_state)
                    })
                except Exception as e:
                    diagnosis['available_xbots'].append(
                        {'id': xbot_id, 'status': 'error', 'error': str(e)})
        except Exception as e:
            self.logger.error(f"General diagnosis error: {e}")
        return diagnosis
