"""
Abstrakte Basis-Klasse für Kamera-Treiber.

Dieses Modul definiert das Interface, das alle Kamera-Treiber
implementieren müssen. Es bietet eine konsistente API für
Kamerasteuerung unabhängig von der Hardware.

Implementierungen:
==================
    - AravisCameraDriver: Echte Kamera via camera_aravis2
    - SimulatedCameraDriver: Simulator für Tests ohne Hardware

Interface-Übersicht:
====================
    ┌─────────────────────────────────────────────────────────┐
    │  CameraDriver (ABC)                                      │
    │                                                         │
    │  Verbindung:                                            │
    │    connect() → bool                                     │
    │    disconnect()                                         │
    │    is_connected → bool                                  │
    │                                                         │
    │  Bildaufnahme:                                          │
    │    capture_image() → np.ndarray                        │
    │    get_latest_image() → np.ndarray                     │
    │                                                         │
    │  Kamera-Einstellungen:                                  │
    │    set_exposure(time) → bool                           │
    │    get_exposure() → float                              │
    │    set_roi(x, y, width, height) → bool                 │
    └─────────────────────────────────────────────────────────┘

Verwendung:
===========
    # Nie direkt instanziieren - immer konkrete Implementierung:
    driver: CameraDriver = AravisCameraDriver(node, logger)
    
    if driver.connect():
        image = driver.capture_image()
        driver.disconnect()
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np


class CameraDriver(ABC):
    """
    Abstrakte Basis-Klasse für alle Kamera-Treiber.

    Alle konkreten Treiber-Implementierungen müssen von dieser Klasse
    erben und alle abstrakten Methoden implementieren.

    Attribute:
        connected (bool): Verbindungsstatus zur Hardware
        logger: Logger für Ausgaben
    """

    def __init__(self, logger):
        """
        Initialisiert den Basis-Treiber.

        Args:
            logger: Logger-Instanz für Ausgaben
        """
        self._logger = logger
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Gibt zurück ob die Kamera verbunden ist."""
        return self._connected

    # ══════════════════════════════════════════════════════════════════════════
    # VERBINDUNG
    # ══════════════════════════════════════════════════════════════════════════

    @abstractmethod
    def connect(self, camera_name: str = None) -> bool:
        """
        Verbindet zur Kamera.

        Args:
            camera_name: Kamera-Identifikator (z.B. IP-Adresse, Serial)
                         Kann None sein für Simulator.

        Returns:
            bool: True wenn Verbindung erfolgreich

        Raises:
            DeviceNotFoundError: Kamera nicht gefunden
            DriverNotAvailableError: Treiber-Bibliothek fehlt
            HardwareError: Verbindungsfehler
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Trennt die Verbindung und gibt Ressourcen frei.

        Sollte beim Node-Shutdown aufgerufen werden.
        """
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # BILDAUFNAHME
    # ══════════════════════════════════════════════════════════════════════════

    @abstractmethod
    def capture_image(self) -> Optional[np.ndarray]:
        """
        Nimmt ein Bild auf und gibt es zurück.

        Returns:
            np.ndarray: BGR-Bild als NumPy-Array, oder None bei Fehler

        Raises:
            CommunicationError: Keine Verbindung
            HardwareError: Aufnahme-Fehler
        """
        pass

    @abstractmethod
    def get_latest_image(self) -> Optional[np.ndarray]:
        """
        Gibt das zuletzt aufgenommene Bild zurück.

        Im Gegensatz zu capture_image() wird hier kein neues Bild
        aufgenommen, sondern das letzte gecachte Bild.

        Returns:
            np.ndarray: BGR-Bild oder None wenn kein Bild verfügbar
        """
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # KAMERA-EINSTELLUNGEN
    # ══════════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def set_exposure(self, exposure_time: float) -> bool:
        """
        Setzt die Belichtungszeit.

        Args:
            exposure_time: Belichtungszeit in Mikrosekunden (µs)

        Returns:
            bool: True wenn erfolgreich

        Raises:
            CommunicationError: Service nicht verfügbar
            HardwareError: Kamera-Fehler
        """
        pass

    @abstractmethod
    def get_exposure(self) -> Optional[float]:
        """
        Gibt die aktuelle Belichtungszeit zurück.

        Returns:
            float: Belichtungszeit in µs, oder None bei Fehler
        """
        pass

    @abstractmethod
    def set_roi(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Setzt die Region of Interest (ROI).

        Args:
            x: X-Offset in Pixeln
            y: Y-Offset in Pixeln
            width: Breite in Pixeln
            height: Höhe in Pixeln

        Returns:
            bool: True wenn erfolgreich
        """
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # SIMULATOR-SPEZIFISCH
    # ══════════════════════════════════════════════════════════════════════════

    def set_focus_position(self, position: float):
        """
        Setzt die simulierte Fokusposition (nur für Simulator).

        Bei echten Treibern hat diese Methode keine Wirkung.

        Args:
            position: Simulierte Z-Position für Fokus-Berechnung
        """
        pass  # Standard-Implementierung tut nichts
