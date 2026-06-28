"""Single ROS 2 entry point for planar-motor control."""

from __future__ import annotations

from dataclasses import asdict

from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import (
    ActivateXbots,
    ArcMotionSi,
    LevitationXbots,
    LinearMotionSi,
    RotaryMotion,
    SetVelocityAcceleration,
    SixDofMotion,
    StopMotion,
)
from promoc_core.logging import LogTags, TaggedLogger
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from .config import DEFAULT_MOVER_NODE_PARAMETERS, MoverNodeConfig
from .drivers.hardware import HardwarePlanarMotorDriver
from .drivers.mock import MockPlanarMotorDriver
from .services.control import ControlCallbacks
from .services.motion import MotionCallbacks
from .services.status import MoverUtils


class MoverServiceNode(Node):
    """ROS node that wires services, status publishing, and the selected driver."""

    def __init__(self):
        super().__init__("mover_node")
        self.log = TaggedLogger(self.get_logger(), LogTags.PMC)
        # Lade Konfiguration via ROS-Parameter (declare + get -> MoverNodeConfig)
        self.config = self._load_config()
        # Erstelle den Treiber je nach Konfiguration (hardware/mock)
        self.driver = self._create_driver()
        # MoverUtils verwaltet den Laufzeitzustand (Verbindung, Positionen,
        # Geschwindigkeitsprofile, Motion-Lock, Motion-Polling)
        self.runtime = MoverUtils(self.get_logger(), self.driver, self.config)
        # Callback-Klassen für Bewegungs- und Steuerungsservices
        self.motion_callbacks = MotionCallbacks(
            self.get_logger(), self.driver, self.runtime, self.config
        )
        self.control_callbacks = ControlCallbacks(
            self.get_logger(), self.driver, self.runtime, self.config
        )
        # Separate ReentrantCallbackGroups erlauben parallele Verarbeitung von
        # Motion-, Control- und Publisher-Callbacks in verschiedenen Threads
        self._motion_group = ReentrantCallbackGroup()
        self._control_group = ReentrantCallbackGroup()
        self._publisher_group = ReentrantCallbackGroup()
        # Publisher sendet regelmässig XBot-Status (Position, Zustand) auf /promoc/mover/xbot_info
        self.xbot_info_publisher = self.create_publisher(
            XBotInfo, "/promoc/mover/xbot_info", 10
        )
        # Registriere alle ROS2-Services (Motion + Control)
        self._create_services()
        # Verbinde zum Planarmotor-Controller und aktiviere ggf. XBots (auto_activate)
        try:
            self.runtime.connect_and_prepare()
        except Exception as exc:
            self.log.error(f"Startup connection failed: {exc}")
        # Periodischer Timer für XBot-Status-Publishing (1/publish_rate Sekunden)
        self.create_timer(
            1.0 / self.config.publish_rate,
            self._publish_xbot_info,
            callback_group=self._publisher_group,
        )
        self.log.info(f"Planar motor configuration: {asdict(self.config)}")

    def _load_config(self) -> MoverNodeConfig:
        # Deklariere alle Parameter beim ROS-Node mit ihren Default-Werten,
        # lese sie dann aus (überschreibbar via YAML/Launch-File) und
        # baue daraus das typisierte MoverNodeConfig-Objekt.
        for name, value in DEFAULT_MOVER_NODE_PARAMETERS.items():
            self.declare_parameter(name, value)
        values = {
            name: self.get_parameter(name).value
            for name in DEFAULT_MOVER_NODE_PARAMETERS
        }
        return MoverNodeConfig.from_mapping(values)

    def _create_driver(self):
        # Wähle Treiber basierend auf driver_mode:
        # "mock"  -> in-process Mock-Treiber für Entwicklung/Tests ohne echte Hardware
        # "hardware" -> Echter Treiber der über PMCLib mit dem Controller kommuniziert
        if self.config.driver_mode == "mock":
            return MockPlanarMotorDriver(
                self.log,
                mock_xbot_count=self.config.mock_xbot_count,
            )
        if self.config.driver_mode == "hardware":
            return HardwarePlanarMotorDriver(self.log)
        raise ValueError(
            f"Unsupported driver_mode '{self.config.driver_mode}'. Use 'hardware' or 'mock'."
        )

    def _create_services(self) -> None:
        self.create_service(
            LinearMotionSi,
            "/promoc/mover/linear_motion_si",
            self.motion_callbacks.callback_linear_motion_si,
            callback_group=self._motion_group,
        )
        self.create_service(
            SixDofMotion,
            "/promoc/mover/six_dof_motion",
            self.motion_callbacks.callback_six_d_motion,
            callback_group=self._motion_group,
        )
        self.create_service(
            ArcMotionSi,
            "/promoc/mover/arc_motion_si",
            self.motion_callbacks.callback_arc_motion_si,
            callback_group=self._motion_group,
        )
        self.create_service(
            RotaryMotion,
            "/promoc/mover/rotary_motion",
            self.motion_callbacks.callback_rotary_motion,
            callback_group=self._motion_group,
        )
        self.create_service(
            ActivateXbots,
            "/promoc/mover/activate_xbots",
            self.control_callbacks.callback_activate_xbot,
            callback_group=self._control_group,
        )
        self.create_service(
            LevitationXbots,
            "/promoc/mover/levitation_xbots",
            self.control_callbacks.callback_levitation_xbot,
            callback_group=self._control_group,
        )
        self.create_service(
            SetVelocityAcceleration,
            "/promoc/mover/set_velocity_acceleration",
            self.control_callbacks.callback_set_velocity_acceleration,
            callback_group=self._control_group,
        )
        self.create_service(
            StopMotion,
            "/promoc/mover/stop_motion",
            self.control_callbacks.callback_stop_motion,
            callback_group=self._control_group,
        )

    def _publish_xbot_info(self) -> None:
        # Baut periodisch eine XBotInfo-Nachricht mit aktueller Pose und Status,
        # stempelt sie mit dem aktuellen ROS-Zeitstempel und publiziert sie.
        try:
            message = self.runtime.build_info_message(self.config.xbot_id)
        except Exception as exc:
            self.log.debug(f"Skipping XBot info publish: {exc}")
            return
        if message is not None:
            message.device_status.stamp = self.get_clock().now().to_msg()
            self.xbot_info_publisher.publish(message)

    def destroy_node(self):
        # Beim Herunterfahren: Stoppe alle XBots und trenne die Verbindung sauber.
        self.runtime.shutdown()
        super().destroy_node()


def main(args=None):
    # Einstiegspunkt: Initialisiert ROS, erstellt den Mover-Knoten und
    # fuehrt ihn in einem MultiThreadedExecutor (4 Threads) aus, damit
    # Motion-, Control- und Publisher-Callbacks parallel arbeiten koennen.
    rclpy.init(args=args)
    node = MoverServiceNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
