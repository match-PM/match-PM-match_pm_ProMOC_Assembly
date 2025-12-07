"""
Aravis Kamera-Treiber für echte Hardware.

Dieser Treiber kommuniziert mit dem camera_aravis2 ROS2-Treiber,
der GigE Vision Kameras über die Aravis-Bibliothek steuert.

Architektur:
============
    ┌─────────────────────────────────────────────────────────┐
    │  AravisCameraDriver                                      │
    │                                                         │
    │  ┌─────────────────┐       ┌─────────────────────────┐ │
    │  │ capture_image() │──────▶│ Image Subscriber        │ │
    │  └─────────────────┘       │ /assembly_camera/image  │ │
    │                            └─────────────────────────┘ │
    │                                                         │
    │  ┌─────────────────┐       ┌─────────────────────────┐ │
    │  │ set_exposure()  │──────▶│ Service Client          │ │
    │  └─────────────────┘       │ .../set_exposure_time   │ │
    │                            └─────────────────────────┘ │
    └─────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────┐
    │  camera_aravis2 Node (externer ROS2 Treiber)            │
    │  - Aravis GigE Vision Interface                         │
    │  - Publiziert Bilder, bietet Services                   │
    └─────────────────────────────────────────────────────────┘

Abhängigkeiten:
===============
    - camera_aravis2: Muss als separate Node laufen
    - pm_genicam_controller_interfaces: Service-Definitionen

Verwendung:
===========
    driver = AravisCameraDriver(node, logger)
    
    if driver.connect():
        await driver.set_exposure(10000.0)  # 10ms
        image = driver.get_latest_image()
        driver.disconnect()
"""

from typing import Optional
import numpy as np

from .camera_driver import CameraDriver
from promoc_core.promoc_exceptions import (
    HardwareError,
    CommunicationError,
    DriverNotAvailableError
)


class AravisCameraDriver(CameraDriver):
    """
    Kamera-Treiber für echte Hardware via camera_aravis2.

    Dieser Treiber ist ein Wrapper um ROS2 Services und Topics,
    die vom camera_aravis2 Treiber bereitgestellt werden.

    Attribute:
        _node: Parent ROS2-Node für Service-Clients
        _exposure_client: Service-Client für Belichtungssteuerung
        _latest_image: Zuletzt empfangenes Bild (von Subscriber)
        _current_exposure: Aktuelle Belichtungszeit
    """

    def __init__(self, node, logger):
        """
        Initialisiert den Aravis-Treiber.

        Args:
            node: Parent ROS2-Node (für Service-Clients)
            logger: Logger für Ausgaben
        """
        super().__init__(logger)
        self._node = node

        # ── Service-Client für Belichtung ──
        self._exposure_client = None
        self._SetExposureTime = None

        # ── Bild-Cache ──
        self._latest_image: Optional[np.ndarray] = None
        self._current_exposure: float = 10000.0  # Default: 10ms

    # ══════════════════════════════════════════════════════════════════════════
    # VERBINDUNG
    # ══════════════════════════════════════════════════════════════════════════

    def connect(self, camera_name: str = None) -> bool:
        """
        Initialisiert die Verbindung zum camera_aravis2 Treiber.

        Ablauf:
        -------
        1. Service-Definitionen importieren
        2. Service-Client erstellen
        3. Auf Service warten (optional)

        Args:
            camera_name: Wird ignoriert (Kamera durch Treiber definiert)

        Returns:
            bool: True wenn Service-Client erstellt wurde

        Raises:
            DriverNotAvailableError: Interface-Package fehlt
        """
        self._logger.info("Verbinde zu camera_aravis2 Treiber...")

        try:
            # ── Service-Typ importieren ──
            from pm_genicam_controller_interfaces.srv import SetExposureTime
            self._SetExposureTime = SetExposureTime

            # ── Service-Client erstellen ──
            self._exposure_client = self._node.create_client(
                self._SetExposureTime,
                '/promoc/assembly_camera_controller/set_exposure_time'
            )

            self._connected = True
            self._logger.info("✓ Aravis-Treiber verbunden")
            return True

        except ImportError as e:
            raise DriverNotAvailableError(
                message="pm_genicam_controller_interfaces nicht verfügbar",
                details={'error': str(e), 'driver': 'camera_aravis2'}
            )

    def disconnect(self):
        """
        Trennt die Verbindung (gibt Ressourcen frei).
        """
        self._connected = False
        self._exposure_client = None
        self._latest_image = None
        self._logger.info("Aravis-Treiber getrennt")

    # ══════════════════════════════════════════════════════════════════════════
    # BILDAUFNAHME
    # ══════════════════════════════════════════════════════════════════════════

    def capture_image(self) -> Optional[np.ndarray]:
        """
        Gibt das aktuelle Kamerabild zurück.

        Hinweis: Da camera_aravis2 kontinuierlich streamt,
        ist dies identisch mit get_latest_image().

        Returns:
            np.ndarray: BGR-Bild oder None
        """
        return self.get_latest_image()

    def get_latest_image(self) -> Optional[np.ndarray]:
        """
        Gibt das zuletzt empfangene Bild zurück.

        Das Bild wird vom Image-Subscriber in camera_node.py gesetzt.

        Returns:
            np.ndarray: BGR-Bild oder None wenn kein Bild
        """
        return self._latest_image

    def set_latest_image(self, image: np.ndarray):
        """
        Setzt das neueste Bild (von Subscriber aufgerufen).

        Args:
            image: BGR-Bild als NumPy-Array
        """
        self._latest_image = image

    # ══════════════════════════════════════════════════════════════════════════
    # KAMERA-EINSTELLUNGEN
    # ══════════════════════════════════════════════════════════════════════════

    async def set_exposure(self, exposure_time: float) -> bool:
        """
        Setzt die Belichtungszeit über den camera_aravis2 Service.

        Args:
            exposure_time: Belichtungszeit in µs

        Returns:
            bool: True wenn erfolgreich

        Raises:
            CommunicationError: Service nicht verfügbar
            HardwareError: Kamera-Fehler
        """
        if self._exposure_client is None:
            raise CommunicationError("Belichtungs-Service nicht initialisiert")

        if not self._exposure_client.service_is_ready():
            raise CommunicationError(
                "camera_aravis2 Service nicht bereit. "
                "Ist der Treiber gestartet?"
            )

        # ── Service aufrufen ──
        request = self._SetExposureTime.Request()
        request.exposure_time = exposure_time

        try:
            future = self._exposure_client.call_async(request)
            response = await future

            if not response.success:
                raise HardwareError(
                    message=f"Belichtung setzen fehlgeschlagen: {response.error}",
                    details={'exposure_time': exposure_time}
                )

            self._current_exposure = exposure_time
            return True

        except Exception as e:
            if isinstance(e, (HardwareError, CommunicationError)):
                raise
            raise HardwareError(
                message=f"Fehler beim Setzen der Belichtung: {e}",
                details={'exposure_time': exposure_time}
            )

    def get_exposure(self) -> Optional[float]:
        """
        Gibt die aktuell gesetzte Belichtungszeit zurück.

        Returns:
            float: Belichtungszeit in µs
        """
        return self._current_exposure

    def set_roi(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Setzt die Region of Interest.

        Hinweis: Aktuell nicht implementiert für camera_aravis2.
        ROI wird über den Treiber-Launch konfiguriert.

        Returns:
            bool: False (nicht unterstützt)
        """
        self._logger.warning(
            "ROI-Änderung zur Laufzeit nicht unterstützt. "
            "Konfiguriere ROI über camera_aravis2 Launch-Parameter."
        )
        return False
