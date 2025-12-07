"""
Simulierter Kamera-Treiber für Tests ohne Hardware.

Dieser Treiber generiert synthetische Bilder mit steuerbarer
Unschärfe basierend auf einer simulierten Fokusebene.

Funktionsweise:
===============
    ┌─────────────────────────────────────────────────────────┐
    │  SimulatedCameraDriver                                   │
    │                                                         │
    │  focal_plane = 15.0mm (feste Fokusebene)               │
    │  current_position = variable (von set_focus_position)   │
    │                                                         │
    │  Unschärfe = |current_position - focal_plane|           │
    │                                                         │
    │  ┌─────────────────────────────────────────────────────┐│
    │  │  Generiertes Bild (640x480):                        ││
    │  │                                                     ││
    │  │         ┌─────────────┐                            ││
    │  │         │▓▓▓▓▓▓▓▓▓▓▓▓▓│  ← Weißes Rechteck        ││
    │  │         │▓▓▓▓▓▓▓▓▓▓▓▓▓│    5° rotiert             ││
    │  │         │▓▓▓▓▓▓▓▓▓▓▓▓▓│    (Slanted Edge)         ││
    │  │         └─────────────┘                            ││
    │  │                                                     ││
    │  └─────────────────────────────────────────────────────┘│
    │                                                         │
    │  Gausscher Blur basierend auf Abstand zur Fokusebene   │
    └─────────────────────────────────────────────────────────┘

Slanted Edge für MTF:
=====================
Das 5°-rotierte Rechteck erzeugt eine schräge Kante,
die für die MTF-Berechnung nach ISO 12233 genutzt wird.

Fokus-Simulation:
=================
    Position  →  Unschärfe  →  Bild
    ─────────────────────────────────────
    15.0 mm   →  0          →  Scharf
    14.0 mm   →  1          →  Leicht unscharf
    10.0 mm   →  5          →  Unscharf
    5.0 mm    →  10 (max)   →  Sehr unscharf

Verwendung:
===========
    driver = SimulatedCameraDriver(logger)
    driver.connect()
    
    # Fokusposition setzen (simuliert Achsenbewegung):
    driver.set_focus_position(15.0)  # → scharfes Bild
    driver.set_focus_position(10.0)  # → unscharfes Bild
    
    image = driver.capture_image()
"""

from typing import Optional
import numpy as np
import cv2

from .camera_driver import CameraDriver


class SimulatedCameraDriver(CameraDriver):
    """
    Simulierter Kamera-Treiber für Tests ohne Hardware.

    Generiert synthetische Bilder mit einer Slanted Edge
    und steuerbarer Unschärfe für Autofokus-Tests.

    Attribute:
        _focal_plane: Simulierte Fokusebene in mm
        _current_position: Aktuelle simulierte Z-Position
        _exposure: Simulierte Belichtungszeit (hat keinen Effekt)
        _image_size: Bildgröße (width, height)
    """

    # ── Konstanten ──
    DEFAULT_FOCAL_PLANE = 15.0      # mm
    DEFAULT_IMAGE_WIDTH = 640       # px
    DEFAULT_IMAGE_HEIGHT = 480      # px
    MAX_BLUR = 10                   # Maximum Blur-Kernel-Größe
    EDGE_ANGLE = 5                  # Grad (für Slanted Edge)

    def __init__(self, logger):
        """
        Initialisiert den Simulator-Treiber.

        Args:
            logger: Logger für Ausgaben
        """
        super().__init__(logger)

        # ── Fokus-Simulation ──
        self._focal_plane = self.DEFAULT_FOCAL_PLANE
        self._current_position = 0.0

        # ── Kamera-Einstellungen ──
        self._exposure = 10000.0  # µs (hat keinen visuellen Effekt)
        self._image_size = (self.DEFAULT_IMAGE_WIDTH,
                            self.DEFAULT_IMAGE_HEIGHT)

        # ── Bild-Cache ──
        self._latest_image: Optional[np.ndarray] = None

    # ══════════════════════════════════════════════════════════════════════════
    # VERBINDUNG
    # ══════════════════════════════════════════════════════════════════════════

    def connect(self, camera_name: str = None) -> bool:
        """
        Simuliert Kamera-Verbindung.

        Generiert direkt das erste Bild.

        Returns:
            bool: Immer True (Simulator kann nicht fehlschlagen)
        """
        self._connected = True
        self._logger.info("📷 Kamera-Simulator verbunden")
        self._logger.info(f"   Fokusebene bei Z = {self._focal_plane} mm")

        # Erstes Bild generieren
        self._update_image()
        return True

    def disconnect(self):
        """Trennt den Simulator."""
        self._connected = False
        self._latest_image = None
        self._logger.info("Kamera-Simulator getrennt")

    # ══════════════════════════════════════════════════════════════════════════
    # BILDAUFNAHME
    # ══════════════════════════════════════════════════════════════════════════

    def capture_image(self) -> Optional[np.ndarray]:
        """
        Generiert ein neues Bild mit aktueller Unschärfe.

        Returns:
            np.ndarray: BGR-Bild (640x480)
        """
        self._update_image()
        return self._latest_image

    def get_latest_image(self) -> Optional[np.ndarray]:
        """
        Gibt das zuletzt generierte Bild zurück.

        Returns:
            np.ndarray: BGR-Bild oder None
        """
        if self._latest_image is None:
            self._update_image()
        return self._latest_image

    def _update_image(self):
        """
        Generiert ein neues Bild basierend auf aktuellem Fokus.

        Ablauf:
        -------
        1. Unschärfe aus Abstand zur Fokusebene berechnen
        2. Slanted Edge Bild generieren
        3. Gausschen Blur anwenden
        """
        # ── Unschärfe berechnen ──
        blur_amount = abs(self._current_position - self._focal_plane)
        blur_amount = min(blur_amount, self.MAX_BLUR)

        # ── Bild generieren ──
        width, height = self._image_size
        self._latest_image = self._generate_slanted_edge_image(
            width, height, blur_amount
        )

    def _generate_slanted_edge_image(
        self,
        width: int,
        height: int,
        blur_amount: float
    ) -> np.ndarray:
        """
        Generiert ein Testbild mit schräger Kante (Slanted Edge).

        Das Bild enthält ein weißes Rechteck, das um 5° rotiert ist.
        Diese schräge Kante ermöglicht MTF-Berechnung nach ISO 12233.

        Args:
            width: Bildbreite in Pixeln
            height: Bildhöhe in Pixeln
            blur_amount: Unschärfe (0=scharf, 10=max. unscharf)

        Returns:
            np.ndarray: BGR-Bild
        """
        # ── Schwarzes Bild erstellen ──
        image = np.zeros((height, width), dtype=np.uint8)

        # ── Rechteck-Koordinaten (zentriert bei 0,0) ──
        rect_width, rect_height = 200, 400
        box_coords = np.array([
            [-rect_width / 2, -rect_height / 2],
            [rect_width / 2, -rect_height / 2],
            [rect_width / 2, rect_height / 2],
            [-rect_width / 2, rect_height / 2]
        ])

        # ── Um 5° rotieren ──
        center_x, center_y = width // 2, height // 2
        M = cv2.getRotationMatrix2D((0, 0), self.EDGE_ANGLE, 1.0)
        rotated_coords = box_coords @ M[:, :2].T

        # ── Ins Bildzentrum verschieben ──
        rotated_coords[:, 0] += center_x
        rotated_coords[:, 1] += center_y

        # ── Rechteck weiß füllen ──
        cv2.fillConvexPoly(image, np.int32(rotated_coords), 255)

        # ── Gaussche Unschärfe anwenden ──
        if blur_amount > 0:
            kernel_size = int(blur_amount) * 2 + 1
            image = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

        # ── In BGR konvertieren (ROS-Kompatibilität) ──
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    # ══════════════════════════════════════════════════════════════════════════
    # KAMERA-EINSTELLUNGEN
    # ══════════════════════════════════════════════════════════════════════════

    async def set_exposure(self, exposure_time: float) -> bool:
        """
        Simuliert Belichtungszeit-Änderung.

        Hinweis: Hat keinen visuellen Effekt auf das Bild,
        aber der Wert wird gespeichert.

        Args:
            exposure_time: Belichtungszeit in µs

        Returns:
            bool: Immer True
        """
        self._exposure = exposure_time
        self._logger.debug(f"Simulierte Belichtung: {exposure_time} µs")
        return True

    def get_exposure(self) -> Optional[float]:
        """
        Gibt die simulierte Belichtungszeit zurück.

        Returns:
            float: Belichtungszeit in µs
        """
        return self._exposure

    def set_roi(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Ändert die Bildgröße (simuliert ROI).

        Args:
            x, y: Werden ignoriert (immer zentriert)
            width, height: Neue Bildgröße

        Returns:
            bool: True
        """
        self._image_size = (width, height)
        self._logger.info(f"Simulierte Bildgröße: {width}x{height}")
        self._update_image()
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # SIMULATOR-SPEZIFISCH
    # ══════════════════════════════════════════════════════════════════════════

    def set_focus_position(self, position: float):
        """
        Setzt die simulierte Fokusposition.

        Die Unschärfe des Bildes wird basierend auf dem Abstand
        zwischen dieser Position und der Fokusebene berechnet.

        Args:
            position: Z-Position in mm

        Beispiel:
            driver.set_focus_position(15.0)  # → scharfes Bild
            driver.set_focus_position(10.0)  # → unscharfes Bild
        """
        self._current_position = position
        self._update_image()

    def set_focal_plane(self, focal_plane: float):
        """
        Setzt die Fokusebene (wo das Bild scharf ist).

        Args:
            focal_plane: Z-Position der Fokusebene in mm
        """
        self._focal_plane = focal_plane
        self._logger.info(f"Fokusebene geändert auf Z = {focal_plane} mm")
        self._update_image()
