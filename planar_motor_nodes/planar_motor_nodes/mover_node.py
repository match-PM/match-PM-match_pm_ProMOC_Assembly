"""
ROS2 Node für XBot Mover Control (Planar Motor).

Dieses Modul implementiert den MoverServiceNode - den zentralen Orchestrator
für die Steuerung von XBot Planar-Motoren via PMC-Controller.

Architektur-Übersicht:
======================
Der Node folgt einem Dependency-Injection-Pattern für bessere Testbarkeit:

    MoverServiceNode (Orchestrator)
        │
        ├── NodeConfig          → Konfiguration (Bounds, Toleranzen, Mock-Modus)
        ├── PmcInterface        → Hardware-Abstraktion (PMCLib-Wrapper)
        ├── MoverUtils          → Hilfsfunktionen (Position, Umrechnungen)
        └── ServiceCallbacks    → Geschäftslogik (Motion-Verarbeitung)

Ablauf beim Start:
==================
1. Node-Initialisierung
   └── ROS2-Node erstellen, Logger konfigurieren

2. Konfiguration laden
   └── Parameter von ROS2-Parametern lesen (use_mock, xbot_id, bounds...)

3. Komponenten erstellen
   ├── PmcInterface  → Versucht PMCLib zu laden (lokal → installiert → mock)
   ├── MoverUtils    → Position-Tracking und Umrechnungen
   └── ServiceCallbacks → Callback-Logik für alle Services

4. ROS2-Services registrieren
   └── linear_motion, six_dof_motion, activate, stop, etc.

5. PMC-Verbindung herstellen
   └── Versucht Verbindung mit Retries (oder Mock-Modus)

6. System aktivieren
   └── XBot-Aktivierung und Levitation starten

7. Timer starten
   └── Regelmäßige Position-Updates publizieren

Verwendung:
===========
    # Als ROS2-Node starten:
    ros2 run planar_motor_nodes mover_node

    # Mit Mock-Modus (ohne Hardware):
    ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true

Beispiel-Service-Calls:
=======================
    # XBot linear bewegen (in mm):
    ros2 service call /mover/linear_motion_si promoc_assembly_interfaces/srv/LinearMotionSI \\
        "{xbot_id: 0, target_x: 100.0, target_y: 50.0}"

    # Bewegung stoppen:
    ros2 service call /mover/stop_motion promoc_assembly_interfaces/srv/StopMotion \\
        "{xbot_id: 0}"
"""

import rclpy
import time
import math
from rclpy.node import Node
from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import (
    ActivateXbots, ArcMotionSi, LevitationXbots,
    LinearMotionSi, RotaryMotion, SetVelocityAcceleration,
    SixDofMotion, StopMotion
)

# Importiere unsere neuen, sauberen Bausteine
from .mover_pmc_interface import PmcInterface
from .mover_utils import MoverUtils
from .mover_service_callbacks import ServiceCallbacks
from .mover_node_config import NodeConfig
from promoc_core.conversions import m_to_mm, mm_to_m, rad_to_deg, deg_to_rad
from promoc_core.promoc_exceptions import ConnectionError


class MoverServiceNode(Node):
    """
    Zentraler ROS2-Node für die Planar-Motor-Steuerung.

    Diese Klasse ist der "Dirigent" - sie erstellt und koordiniert alle
    anderen Komponenten, verarbeitet aber keine Geschäftslogik selbst.

    Funktionsweise:
    ---------------
    Der Node durchläuft beim Start folgende Phasen:

    1. INIT-PHASE:
       - ROS2-Node wird initialisiert
       - Konfiguration wird aus ROS-Parametern geladen
       - Komponenten werden erstellt (PmcInterface, MoverUtils, ServiceCallbacks)

    2. SETUP-PHASE:
       - ROS2-Services werden registriert (linear_motion, activate, stop, etc.)
       - Position-Publisher wird erstellt

    3. CONNECT-PHASE:
       - Verbindung zum PMC-Controller wird hergestellt
       - Bei Fehlern: Retries mit exponential backoff
       - Mock-Modus: Nutzt simulierte Bewegungen

    4. ACTIVATE-PHASE:
       - XBot wird aktiviert
       - Levitation wird gestartet (Motor schwebt über Stator)

    5. RUN-PHASE:
       - Position-Timer publiziert regelmäßig XBot-Position
       - Services warten auf eingehende Anfragen

    Attribute:
        config (NodeConfig): Konfiguration (Bounds, Toleranzen, XBot-ID)
        pmc (PmcInterface): Hardware-Abstraktion für PMC-Controller
        mover_utils (MoverUtils): Hilfsfunktionen für Positionsberechnung
        service_callbacks (ServiceCallbacks): Callback-Logik für Services
        xbot_info_publisher: ROS2-Publisher für Position-Updates

    Beispiel:
        # Automatischer Start via ROS2-Launch oder direkt:
        node = MoverServiceNode()
        rclpy.spin(node)
    """

    def __init__(self):
        """
        Initialisiert den MoverServiceNode.

        Ablauf (Schritt für Schritt):
        -----------------------------
        1. ROS2-Node erstellen mit Namen "mover_node"
        2. Konfiguration aus ROS-Parametern laden → NodeConfig
        3. Komponenten erstellen:
           - PmcInterface: Hardware-Verbindung
           - MoverUtils: Hilfsfunktionen  
           - ServiceCallbacks: Callback-Logik
        4. ROS2-Services registrieren
        5. Verbindungs-Timer starten (versucht PMC-Verbindung)
        """
        super().__init__("mover_node")

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: Konfiguration laden
        # ══════════════════════════════════════════════════════════════════════
        # Lädt alle Parameter (use_mock, xbot_id, bounds) aus ROS-Parametern
        self.config = self._load_config()
        self.is_connected = False

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: Komponenten erstellen (Dependency Injection)
        # ══════════════════════════════════════════════════════════════════════
        # Jede Komponente bekommt ihre Abhängigkeiten explizit übergeben.
        # Das macht das System testbar und die Abhängigkeiten klar.
        self.pmc = PmcInterface(
            self.get_logger(), use_mock=self.config.use_mock)
        self.mover_utils = MoverUtils(self.get_logger(), self.pmc, self.config)
        self.callbacks = ServiceCallbacks(
            self.get_logger(), self.pmc, self.mover_utils, self.config)
        self.xbot_pos_publisher = self.create_publisher(
            XBotInfo, "xbot_info", 10)

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 3: ROS2-Services registrieren
        # ══════════════════════════════════════════════════════════════════════
        self._setup_services()

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 4: Verbindungs-Timer starten
        # ══════════════════════════════════════════════════════════════════════
        # Timer versucht alle 100ms eine Verbindung zum PMC-Controller.
        # Bei Erfolg stoppt er sich selbst und aktiviert das System.
        self.get_logger().info(f"Connecting to PMC at {self.config.pmc_ip}...")
        self.connection_timer = self.create_timer(0.1, self._try_connect)

        self.get_logger().info("Mover Service Node initialized. Waiting for PMC connection...")

    def _try_connect(self):
        """
        Versucht eine Verbindung zum PMC-Controller herzustellen.

        Wird vom connection_timer alle 100ms aufgerufen bis die Verbindung steht.
        Bei Erfolg wird der Timer gestoppt und das System aktiviert.

        Ablauf:
        -------
        1. Verbindung versuchen via PmcInterface.connect()
        2. Bei Erfolg:
           - Timer stoppen
           - System aktivieren (_activate_system)
        3. Bei Fehler:
           - Debug-Log (um Console nicht zu überfluten)
           - Nächster Versuch in 100ms
        """
        try:
            self.pmc.connect(self.config.pmc_ip)

            self.get_logger().info("PMC Connected! Activating system.")
            self.is_connected = True

            # Timer stoppen - Verbindung steht
            self.connection_timer.cancel()

            # System aktivieren (XBots + Publisher)
            self._activate_system()

        except Exception as e:
            # Debug-Level um Spam während Startup zu vermeiden
            self.get_logger().debug(f"Connection attempt failed: {e}")

    def _activate_system(self):
        """
        Aktiviert das XBot-System nach erfolgreicher PMC-Verbindung.

        Ablauf:
        -------
        1. XBots aktivieren (Hardware in Bereitschaft)
        2. Position-Publisher starten (regelmäßige Updates)
        """
        try:
            self.pmc.bot.activate_xbots()
            self.get_logger().info("XBot Activated")
            self._start_publisher_timer()
        except Exception as e:
            self.get_logger().error(
                f"Failed to activate XBots after connection: {e}")

    def _load_config(self) -> NodeConfig:
        """
        Lädt Konfiguration aus ROS-Parametern und erstellt NodeConfig.

        Parameter werden mit Defaults deklariert und können per Launch-File
        oder Kommandozeile überschrieben werden.

        Returns:
            NodeConfig: Dataclass mit allen Konfigurationswerten

        Parameter-Kategorien:
        ---------------------
        1. Allgemein:
           - use_mock: True für Simulation ohne Hardware
           - xbot_id: ID des zu steuernden XBots
           - pmc_ip: IP-Adresse des PMC-Controllers

        2. Bewegungsgrenzen (in Metern):
           - x_min/x_max: X-Achsen-Grenzen
           - y_min/y_max: Y-Achsen-Grenzen
           - z_min/z_max: Z-Achsen-Grenzen (Levitation)

        3. Toleranzen (in Metern):
           - xy_tolerance: Genauigkeit für XY-Positionierung
           - six_d_tolerance: Genauigkeit für 6DOF-Bewegungen
        """
        # Declare all parameters with their default values
        self.declare_parameter('use_mock', False)
        self.declare_parameter('xbot_id', 0)
        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('pmc_ip', '192.168.10.100')

        # Movement boundaries and tolerances
        self.declare_parameter('xy_tolerance', 0.001)
        self.declare_parameter('six_d_tolerance', 0.001)
        self.declare_parameter('x_min', 0.055)
        self.declare_parameter('x_max', 0.420)
        self.declare_parameter('y_min', 0.055)
        self.declare_parameter('y_max', 0.180)
        self.declare_parameter('z_min', 0.000)
        self.declare_parameter('z_max', 0.004)

        # Create config object from declared parameters
        config = NodeConfig(
            use_mock=self.get_parameter('use_mock').value,
            xbot_id=self.get_parameter('xbot_id').value,
            publish_rate=self.get_parameter('publish_rate').value,
            pmc_ip=self.get_parameter('pmc_ip').value,
            xy_tolerance=self.get_parameter('xy_tolerance').value,
            six_d_tolerance=self.get_parameter('six_d_tolerance').value,
            x_min=self.get_parameter('x_min').value,
            x_max=self.get_parameter('x_max').value,
            y_min=self.get_parameter('y_min').value,
            y_max=self.get_parameter('y_max').value,
            z_min=self.get_parameter('z_min').value,
            z_max=self.get_parameter('z_max').value,
        )

        self.get_logger().info(f"Configuration loaded: {config}")
        return config

    def _setup_services(self):
        """
        Registriert alle ROS2-Services für die Mover-Steuerung.

        Verfügbare Services:
        --------------------
        - linear_motion_si: Lineare XY-Bewegung (mm)
        - six_dof_motion: 6-DOF Bewegung (X,Y,Z,Rx,Ry,Rz)
        - activate_xbots: XBot aktivieren
        - levitation_xbots: Levitation starten/stoppen
        - arc_motion_si: Bogenförmige Bewegung
        - stop_motion: Bewegung stoppen
        - rotary_motion: Rotationsbewegung (Rz)
        - set_velocity_acceleration: Geschwindigkeit/Beschleunigung setzen

        Jeder Service wird mit dem Node-Namen als Präfix erstellt:
        z.B. /mover_node/linear_motion_si
        """
        services = [
            ('linear_motion_si', LinearMotionSi,
             self.callbacks.callback_linear_motion_si),
            ('six_dof_motion', SixDofMotion, self.callbacks.callback_six_d_motion),
            ('activate_xbots', ActivateXbots,
             self.callbacks.callback_activate_xbot),
            ('levitation_xbots', LevitationXbots,
             self.callbacks.callback_levitation_xbot),
            ('arc_motion_si', ArcMotionSi, self.callbacks.callback_arc_motion_si),
            ('stop_motion', StopMotion, self.callbacks.callback_stop_motion),
            ('rotary_motion', RotaryMotion, self.callbacks.callback_rotary_motion),
            ('set_velocity_acceleration', SetVelocityAcceleration,
             self.callbacks.callback_set_velocity_acceleration)
        ]
        for name, srv_type, callback in services:
            self.create_service(
                srv_type, f"{self.get_name()}/{name}", callback)
        self.get_logger().info("All services are created.")

    def _start_publisher_timer(self):
        """
        Startet Timer für periodische Position-Updates.

        Wird erst nach erfolgreicher PMC-Verbindung aufgerufen.

        Timer:
        ------
        1. Position-Timer: Publiziert XBot-Position (Standard: 10 Hz)
        2. Diagnose-Timer: Prüft XBot-Verfügbarkeit alle 5s (nur bei echter Hardware)
        """
        publish_interval = 1.0 / self.config.publish_rate
        self.xbot_position_timer = self.create_timer(
            publish_interval, self._publish_xbot_position)
        if not self.pmc.status['is_mock']:
            self.xbot_diagnosis_timer = self.create_timer(
                5.0, self.mover_utils.diagnose_xbot_availability)
        self.get_logger().info("Timers started.")

    def _publish_xbot_position(self):
        """
        Publiziert die aktuelle XBot-Position als XBotInfo-Message.

        Konvertiert interne SI-Einheiten zu benutzerfreundlichen Einheiten:
        - Position: Meter → Millimeter
        - Winkel: Radiant → Grad
        """
        if not self.is_connected:
            return

        msg = XBotInfo()
        try:
            current_pos = self.mover_utils.get_current_position(0)
            if current_pos:
                # Konvertiere: m → mm, rad → deg
                msg.x_pos = m_to_mm(current_pos[0])
                msg.y_pos = m_to_mm(current_pos[1])
                msg.z_pos = m_to_mm(current_pos[2])
                msg.rx_pos = rad_to_deg(current_pos[3])
                msg.ry_pos = rad_to_deg(current_pos[4])
                msg.rz_pos = rad_to_deg(current_pos[5])

            msg.xbot_state = self.mover_utils.get_xbot_state_string(0)
            self.xbot_pos_publisher.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Position publishing error: {e}")

    def destroy_node(self):
        """Sauberes Herunterfahren."""
        self.get_logger().info("Shutting down MoverServiceNode...")
        if self.is_connected:
            try:
                self.pmc.bot.deactivate_xbots()
                self.get_logger().info("XBots deactivated.")
            except Exception as e:
                self.get_logger().error(f"Error during deactivation: {e}")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MoverServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
