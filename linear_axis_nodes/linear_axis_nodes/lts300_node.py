"""
ROS2 Node für Thorlabs LTS300 Linearachsen-Steuerung.

Dieses Modul implementiert den LTS300Node - den zentralen Orchestrator
für die Steuerung der Thorlabs LTS300 Linearachse (300mm Verfahrweg).

Architektur-Übersicht:
======================
Der Node folgt dem gleichen Dependency-Injection-Pattern wie der Mover-Node:

    LTS300Node (Orchestrator)
        │
        ├── Lts300Config       → Konfiguration (Seriennummer, Limits, Timeouts)
        ├── Lts300Interface    → Hardware-Abstraktion (Real/Simuliert)
        └── ServiceCallbacks   → Geschäftslogik (Bewegungs-Validierung)

Ablauf beim Start:
==================
1. Node-Initialisierung
   └── ROS2-Node erstellen, Logger konfigurieren

2. Konfiguration laden
   └── Parameter lesen (serial_port, collision_threshold, limits...)

3. Hardware-Interface erstellen
   └── Lts300Interface wählt automatisch: Real-Hardware oder Simulation

4. Verbindung herstellen
   └── Verbindung zur Achse über seriellen Port

5. ROS2-Kommunikation einrichten
   ├── Publisher: Position-Updates (10 Hz)
   ├── Subscriber: Position der anderen Achse (für Kollisionserkennung)
   └── Services: move_absolute, move_relative, home, etc.

6. Position publizieren
   └── Timer publiziert alle 100ms die aktuelle Position

Besonderheiten:
===============
- Kollisionserkennung: Überwacht Position der anderen Achse (X↔Z)
- Asynchrone Bewegungen: Lange Operationen blockieren nicht den Node
- Soft-Limits: Konfigurierbare Bewegungsgrenzen
- Homing: Automatisches Referenzieren mit Timeout

Verwendung:
===========
    # Als ROS2-Node starten:
    ros2 run linear_axis_nodes lts300_node

    # Mit Simulation:
    ros2 run linear_axis_nodes lts300_node --ros-args -p use_sim_time:=true

Beispiel-Service-Calls:
=======================
    # Absolute Bewegung (in mm):
    ros2 service call /lts300_x_axis/move_absolute \\
        promoc_assembly_interfaces/srv/MoveAbsolute "{axis_position: 150.0}"

    # Homing durchführen:
    ros2 service call /lts300_x_axis/home promoc_assembly_interfaces/srv/Home
"""

import rclpy
import traceback
from rclpy.node import Node
from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import (
    MoveAbsolute, MoveRelativ, Home, ShutdownLinearAxis, GetPosition,
    SetVelocityParameters, GetVelocityParameters, GetOperationStatus,
    EmergencyStop, JogAxis
)

from .lts300_node_config import Lts300Config
from .lts300_interface import Lts300Interface
from .lts300_service_callbacks import ServiceCallbacks


class LTS300Node(Node):
    """
    Zentraler ROS2-Node für die Thorlabs LTS300 Linearachsen-Steuerung.

    Diese Klasse ist der "Dirigent" - sie erstellt und koordiniert alle
    anderen Komponenten, verarbeitet aber keine Geschäftslogik selbst.

    Funktionsweise:
    ---------------
    Der Node durchläuft beim Start folgende Phasen:

    1. CONFIG-PHASE:
       - Konfiguration aus ROS-Parametern laden

    2. INTERFACE-PHASE:
       - Hardware-Interface erstellen (wählt Real/Simulation)
       - Verbindung herstellen

    3. COMMUNICATION-PHASE:
       - ROS2-Services registrieren
       - Position-Publisher starten
       - Subscriber für andere Achse einrichten

    Attribute:
        config (Lts300Config): Konfiguration (Limits, Seriennummer)
        interface (Lts300Interface): Hardware-Abstraktion
        callbacks (ServiceCallbacks): Callback-Logik für Services
        other_axis_position: Position der anderen Achse für Kollisionserkennung

    Beispiel:
        >>> node = LTS300Node()
        >>> rclpy.spin(node)
    """

    def __init__(self):
        """
        Initialisiert den LTS300Node.

        Ablauf (Schritt für Schritt):
        -----------------------------
        1. ROS2-Node erstellen mit Namen "lts300_node"
        2. Konfiguration aus ROS-Parametern laden
        3. Hardware-Interface erstellen
        4. Verbindung zur Achse herstellen
        5. ROS2-Kommunikation einrichten
        """
        super().__init__('lts300_node')

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: Konfiguration laden
        # ══════════════════════════════════════════════════════════════════════
        self.config = self._load_config()

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: Komponenten erstellen
        # ══════════════════════════════════════════════════════════════════════
        self.interface = Lts300Interface(self.get_logger(), self.config)
        self.callbacks = ServiceCallbacks(
            self.get_logger(), self.interface, self.config)

        try:
            # ══════════════════════════════════════════════════════════════════
            # PHASE 3: Verbindung herstellen
            # ══════════════════════════════════════════════════════════════════
            if not self.interface.connect():
                self.get_logger().error("Shutting down node due to connection failure.")
                self.get_logger().error("Node initialization failed, exiting...")
                return
            self.get_logger().info("Connection successful, continuing initialization...")

            # ══════════════════════════════════════════════════════════════════
            # PHASE 4: ROS2-Kommunikation einrichten
            # ══════════════════════════════════════════════════════════════════
            self.other_axis_position = None
            self._setup_ros_communication()

            self.get_logger().info(
                f"{self.get_name()} with S/N {self.config.serial_number} is running.")
            self.get_logger().info("Node initialization complete!")

        except Exception as e:
            self.get_logger().error(
                f"Exception during initialization: {e}", exc_info=True)
            self.get_logger().error("Node initialization failed, exiting...")
            import traceback
            traceback.print_exc()

    def _load_config(self) -> Lts300Config:
        """
        Lädt Konfiguration aus ROS-Parametern.

        Parameter-Kategorien:
        ---------------------
        1. Verbindung:
           - serial_port: Serieller Port (z.B. /dev/ttyUSB0)
           - serial_number: Geräte-Seriennummer für Identifikation

        2. Sicherheit:
           - collision_threshold: Ab welcher Position der anderen Achse
             keine Bewegung mehr erlaubt ist (in mm)
           - max_position/min_position: Soft-Limits
           - max_single_move: Maximale Einzelbewegung

        3. Timing:
           - homing_timeout: Maximale Zeit für Homing-Operation

        4. Umrechnung:
           - velocity_unit_factor: Faktor für Geschwindigkeitsumrechnung

        Returns:
            Lts300Config: Dataclass mit allen Konfigurationswerten
        """
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('serial_number', '00000000')
        self.declare_parameter('collision_threshold', 300.0)
        self.declare_parameter('namespace', 'promoc_assembly')
        self.declare_parameter('max_position', 300.0)
        self.declare_parameter('min_position', 0.0)
        self.declare_parameter('max_single_move', 300.0)
        self.declare_parameter('homing_timeout', 180.0)
        self.declare_parameter('velocity_unit_factor', 0.018)

        return Lts300Config(
            use_sim_time=self.get_parameter('use_sim_time').value,
            serial_port=self.get_parameter('serial_port').value,
            serial_number=self.get_parameter('serial_number').value,
            collision_threshold=self.get_parameter(
                'collision_threshold').value,
            namespace=self.get_parameter('namespace').value,
            max_position=self.get_parameter('max_position').value,
            min_position=self.get_parameter('min_position').value,
            max_single_move=self.get_parameter('max_single_move').value,
            homing_timeout=self.get_parameter('homing_timeout').value,
            velocity_conversion_factor=self.get_parameter(
                'velocity_unit_factor').value
        )

    def _setup_ros_communication(self):
        """
        Richtet die ROS2-Kommunikation ein.

        Erstellt:
        ---------
        1. Publisher:
           - /{namespace}/{node_name}/position: Aktuelle Position (10 Hz)

        2. Subscriber:
           - Position der anderen Achse für Kollisionserkennung

        3. Services:
           - move_absolute: Absolute Bewegung zu Position
           - move_relative: Relative Bewegung um Distanz
           - home: Referenzfahrt durchführen
           - get_position: Aktuelle Position abfragen
           - get_operation_status: Status laufender Operation
           - set/get_velocity_parameters: Geschwindigkeit einstellen
           - shutdown: Gerät herunterfahren
           - emergency_stop: Notfall-Stopp
           - jog_axis: Schrittweises Bewegen
        """
        try:
            node_name = self.get_name()
            self.get_logger().info(
                f"Setting up ROS communication for {node_name}...")

            # ── Publisher & Timer ──
            self.position_publisher = self.create_publisher(
                LinearAxisInfo, f"/{self.config.namespace}/{node_name}/position", 10)
            self.create_timer(0.1, self.publish_position)
            self.get_logger().info("Publisher and timer created")

            # ── Subscriber für Kollisionserkennung ──
            # Abonniert Position der jeweils anderen Achse (X↔Z)
            axis_type = self.interface.driver.get_axis_type()
            other_axis = 'z' if axis_type == 'x' else 'x'
            self.create_subscription(
                LinearAxisInfo,
                f"/{self.config.namespace}/lts300_{other_axis}_axis/position",
                self.other_axis_position_callback,
                10)
            self.get_logger().info(f"Subscriber created for {other_axis}-axis")

            # ── Services ──
            # move_absolute/move_relative: Übergeben other_axis_position für Kollisionsprüfung
            self.create_service(MoveAbsolute, f'{node_name}/move_absolute',
                                lambda req, res: self.callbacks.callback_move_absolute(req, res, self.other_axis_position))
            self.create_service(MoveRelativ, f'{node_name}/move_relative',
                                lambda req, res: self.callbacks.callback_move_relative(req, res, self.other_axis_position))
            self.create_service(
                Home, f'{node_name}/home', self.callbacks.callback_home)
            self.create_service(
                GetPosition, f'{node_name}/get_position', self.callbacks.callback_get_position)
            self.create_service(
                GetOperationStatus, f'{node_name}/get_operation_status', self.callbacks.callback_get_operation_status)
            self.create_service(
                SetVelocityParameters, f'{node_name}/set_velocity_parameters', self.callbacks.callback_set_velocity_parameters)
            self.create_service(
                GetVelocityParameters, f'{node_name}/get_velocity_parameters', self.callbacks.callback_get_velocity_parameters)
            self.create_service(
                ShutdownLinearAxis, f'{node_name}/shutdown', self.callbacks.callback_shutdown)
            self.create_service(
                EmergencyStop, f'{node_name}/emergency_stop', self.callbacks.callback_emergency_stop)
            self.create_service(
                JogAxis, f'{node_name}/jog_axis', self.callbacks.callback_jog_axis)
            self.get_logger().info("All services created")

        except Exception as e:
            self.get_logger().error(
                f"Error in _setup_ros_communication: {e}", exc_info=True)
            raise e  # Re-raise to be caught by main try-catch

    def publish_position(self):
        """Publishes the current axis position."""
        if not self.interface.is_connected:
            self.get_logger().debug("Skipping position publish - interface not connected")
            return
        try:
            msg = LinearAxisInfo()
            driver = self.interface.driver

            # Get position (this is usually reliable)
            msg.axis_position = driver.get_position()
            msg.serial_number = driver.get_serial_number()

            # Set axis_type based on node name instead of unreliable driver method
            node_name = self.get_name()
            if 'x_axis' in node_name:
                msg.axis_type = 'x'
            elif 'z_axis' in node_name:
                msg.axis_type = 'z'
            else:
                msg.axis_type = 'unknown'

            # Use our operation status instead of unreliable hardware is_moving()
            operation_status, _ = self.callbacks.get_operation_status()
            msg.operation_status = operation_status.value

            self.position_publisher.publish(msg)
            self.get_logger().debug(
                f"Published position: {msg.axis_position:.2f}mm, status: {operation_status.value}")

        except Exception as e:
            # Reduce error logging frequency to avoid spam
            if not hasattr(self, '_last_publish_error_time'):
                self._last_publish_error_time = 0

            import time
            current_time = time.time()
            if current_time - self._last_publish_error_time > 5.0:  # Log error only every 5 seconds
                self.get_logger().error(f"Error publishing position: {e}")
                self._last_publish_error_time = current_time
            else:
                self.get_logger().debug(
                    f"Position publish error (suppressed): {e}")

    def other_axis_position_callback(self, msg):
        """Speichert die Position der anderen Achse."""
        self.other_axis_position = msg.axis_position

    def shutdown_device(self):
        """Fährt das Gerät sauber herunter."""
        self.get_logger().info("Homing device before shutdown...")
        try:
            self.interface.driver.home()
        except Exception as e:
            self.get_logger().error(f"Error during homing on shutdown: {e}")
        finally:
            self.interface.disconnect()


def main(args=None):
    rclpy.init(args=args)
    node = LTS300Node()

    # Check if the node was initialized successfully
    # GEÄNDERT: Prüfe connected-Property des drivers anstatt interface.is_connected
    try:
        if hasattr(node, 'interface') and hasattr(node.interface, 'driver') and node.interface.driver.connected:
            node.get_logger().info("Node successfully initialized, starting spin...")
            try:
                rclpy.spin(node)
            except KeyboardInterrupt:
                node.get_logger().info("Keyboard interrupt, shutting down...")
            finally:
                node.get_logger().info('Final shutdown procedure...')
                node.shutdown_device()
                node.destroy_node()
                if rclpy.ok():
                    rclpy.shutdown()
        else:
            node.get_logger().error("Node initialization failed, exiting...")
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
    except Exception as e:
        node.get_logger().error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
