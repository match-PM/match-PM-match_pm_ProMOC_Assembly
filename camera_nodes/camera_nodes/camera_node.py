#!/usr/bin/env python3
"""
ROS2 Node für Kamera-Bildverarbeitung und Autofokus.

Dieses Modul implementiert den CameraNode - den zentralen Orchestrator
für Kamera-Operationen wie Autofokus und MTF-Messung.

Architektur-Übersicht:
======================
Der Node folgt dem gleichen Dependency-Injection-Pattern wie die anderen Nodes:

    CameraNode (Orchestrator)
        │
        ├── CameraDriver (Abstraktion)
        │     ├── AravisCameraDriver  → Echte Kamera via camera_aravis2
        │     └── SimulatedCameraDriver → Simulator für Tests
        │
        ├── CameraImageProcessing  → Bildverarbeitungs-Algorithmen (MTF)
        └── CameraServiceCallbacks → Service-Logik (Autofokus, MTF)

Treiber-Auswahl:
================
    use_simulator = True  → SimulatedCameraDriver
    use_simulator = False → AravisCameraDriver

Hauptfunktionen:
================
1. Autofokus:
   - Hybrid-Algorithmus: Grobe Suche + Golden Section Search
   - Steuert Z-Achse für Fokus-Optimierung
   - Verwendet Schärfe-Metriken (Laplacian Variance, Tenengrad)

2. MTF-Messung:
   - Slanted Edge Method nach ISO 12233
   - ROI-Auswahl für Messbereich
   - Export als CSV

3. Belichtungssteuerung:
   - Manuelles Setzen der Belichtungszeit
   - Kommunikation mit camera_aravis2 Treiber

Ablauf beim Start:
==================
1. Parameter laden (use_simulator, pixel_size_um, mtf_csv_path)
2. Treiber basierend auf use_simulator auswählen
3. Komponenten erstellen:
   - CameraDriver (Simulator oder Aravis)
   - CameraImageProcessing für Algorithmen
   - CameraServiceCallbacks für Services
4. Subscriber für Kamera-Stream erstellen
5. Services registrieren (autofocus, measure_mtf, select_roi)

Verwendung:
===========
    # Mit echter Kamera:
    ros2 run camera_nodes camera_node

    # Mit Simulator:
    ros2 run camera_nodes camera_node --ros-args -p use_simulator:=true

Beispiel-Service-Calls:
=======================
    # Autofokus durchführen:
    ros2 service call /camera_node/autofocus promoc_assembly_interfaces/srv/AutoFocus \\
        "{start_position: 0.0, end_position: 30.0, step_size: 1.0}"

    # MTF messen:
    ros2 service call /camera_node/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

# Lokale Module
from .camera_image_processing import CameraImageProcessing
from .camera_service_callbacks import CameraServiceCallbacks

# Treiber-Abstraktion
from .drivers import CameraDriver, AravisCameraDriver, SimulatedCameraDriver

# Service-Typen
from std_srvs.srv import Trigger
from promoc_assembly_interfaces.srv import SetExposure, AutoFocus, MeasureMTF


class CameraNode(Node):
    """
    Zentraler ROS2-Node für Kamera-Operationen.

    Diese Klasse ist der "Dirigent" - sie erstellt und koordiniert
    alle Bildverarbeitungs- und Kamera-Komponenten.

    Funktionsweise:
    ---------------
    1. INIT-PHASE:
       - Parameter laden
       - Treiber auswählen (Simulator vs. Aravis)

    2. SUBSCRIBE-PHASE:
       - Auf Kamera-Stream subscriben
       - Letztes Bild für Verarbeitung speichern

    3. SERVICE-PHASE:
       - Services registrieren und auf Anfragen warten
       - Autofokus, MTF-Messung, Belichtung

    Attribute:
        bridge (CvBridge): ROS-OpenCV Bridge
        camera_driver (CameraDriver): Kamera-Treiber (abstrakt)
        image_processor (CameraImageProcessing): Bildverarbeitung
        service_callbacks (CameraServiceCallbacks): Service-Logik
        latest_image_msg: Letztes empfangenes Bild
    """

    def __init__(self):
        """
        Initialisiert den CameraNode.

        Ablauf (Schritt für Schritt):
        -----------------------------
        1. ROS2-Node erstellen
        2. Parameter deklarieren und laden
        3. Treiber basierend auf use_simulator auswählen
        4. Komponenten erstellen (ImageProcessing, Callbacks)
        5. Subscriber für Kamera-Stream erstellen
        6. Services registrieren
        """
        super().__init__('camera_node')

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: Parameter deklarieren und laden
        # ══════════════════════════════════════════════════════════════════════
        self.declare_parameter('use_simulator', False)
        self.declare_parameter('mtf_csv_path', '')
        self.declare_parameter('pixel_size_um', 3.45)
        self.declare_parameter('default_roi_width', 200)
        self.declare_parameter('default_roi_height', 200)
        self.declare_parameter('z_axis_node_name', 'lts300_z_axis')  # Name of z-axis node for autofocus

        self.use_simulator = self.get_parameter(
            'use_simulator').get_parameter_value().bool_value

        self.get_logger().info(
            f"Camera Node startet im {'SIMULATOR' if self.use_simulator else 'REAL'} Modus...")

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: Treiber basierend auf Modus auswählen
        # ══════════════════════════════════════════════════════════════════════
        self.bridge = CvBridge()
        self.camera_driver: CameraDriver = self._create_driver()

        # Treiber verbinden
        self.camera_driver.connect()

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 3: Komponenten erstellen
        # ══════════════════════════════════════════════════════════════════════
        self.image_processor = CameraImageProcessing(self.get_logger())
        self.service_callbacks = CameraServiceCallbacks(
            self, self.camera_driver)

        self.latest_image_msg = None

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 4: Subscriber & Publisher
        # ══════════════════════════════════════════════════════════════════════
        self.assembly_image_sub = self.create_subscription(
            Image, '/promoc/assembly_camera/stream0/image_raw', self.assembly_image_callback, 10)

        self.processed_assembly_pub = self.create_publisher(
            Image, '/camera/assembly/processed', 10)

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 5: Services registrieren
        # ══════════════════════════════════════════════════════════════════════
        self.cb_group = ReentrantCallbackGroup()

        self.select_roi_service = self.create_service(
            Trigger, '~/select_roi', self.service_callbacks.select_roi_callback, callback_group=self.cb_group)
        self.autofocus_service = self.create_service(
            AutoFocus, '~/autofocus', self.service_callbacks.autofocus_callback, callback_group=self.cb_group)
        self.mtf_service = self.create_service(
            MeasureMTF, '~/measure_mtf', self.service_callbacks.measure_mtf_callback, callback_group=self.cb_group)

        # Belichtungs-Service nur bei echter Kamera mit verbundenem Treiber
        if not self.use_simulator and self.camera_driver.is_connected:
            self.manual_set_exposure_service = self.create_service(
                SetExposure, '~/set_exposure', self.service_callbacks.manual_set_exposure_callback, callback_group=self.cb_group)

        self.get_logger().info("✓ Camera Node initialisiert")

    # ══════════════════════════════════════════════════════════════════════════
    # TREIBER-ERSTELLUNG
    # ══════════════════════════════════════════════════════════════════════════

    def _create_driver(self) -> CameraDriver:
        """
        Erstellt den passenden Kamera-Treiber basierend auf use_simulator.

        Returns:
            CameraDriver: Simulator oder Aravis-Treiber
        """
        if self.use_simulator:
            self.get_logger().info("📷 Verwende SimulatedCameraDriver")
            return SimulatedCameraDriver(self.get_logger())
        else:
            self.get_logger().info("📷 Verwende AravisCameraDriver")
            return AravisCameraDriver(self, self.get_logger())

    # ══════════════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════

    def assembly_image_callback(self, msg: Image):
        """
        Speichert das letzte empfangene Kamera-Bild.

        Die Verarbeitung wird durch Services ausgelöst, nicht automatisch.
        Das Bild wird nur gespeichert für späteren Zugriff.

        # Bei echtem Treiber: Bild auch an Treiber weiterleiten.
        """
        # self.get_logger().info("Received image") # Uncomment for debugging
        self.latest_image_msg = msg

        # Bei Aravis-Treiber: Bild im Treiber cachen
        if hasattr(self.camera_driver, 'set_latest_image'):
            try:
                cv_image = self.bridge.imgmsg_to_cv2(
                    msg, desired_encoding='bgr8')
                self.camera_driver.set_latest_image(cv_image)
            except Exception as e:
                self.get_logger().warning(
                    f"Bild-Konvertierung fehlgeschlagen: {e}")


def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()
    executor = MultiThreadedExecutor()
    executor.add_node(camera_node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        camera_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
