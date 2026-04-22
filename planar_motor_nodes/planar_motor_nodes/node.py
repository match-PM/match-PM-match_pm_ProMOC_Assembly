"""ROS2 node for planar motor control.

Canonical entry point for the `planar_motor_nodes` runtime package.
"""

import rclpy
from dataclasses import asdict
from rclpy.node import Node
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

from .drivers.hardware import PmcInterface
from .services import MoverUtils, ServiceHandlers
from .config import MoverNodeConfig
from promoc_core.conversions import m_to_mm, rad_to_deg
from promoc_core.logging import TaggedLogger, LogTags


class MoverServiceNode(Node):
    """ROS2 node for planar motor control."""

    def __init__(self):
        super().__init__("mover_node")
        self.log = TaggedLogger(self.get_logger(), LogTags.PMC)
        self.config = self._load_config()
        self.is_connected = False

        self.pmc = PmcInterface(
            TaggedLogger(self.get_logger(), LogTags.PMC_CONN),
            use_mock=self.config.use_mock,
        )
        self.mover_utils = MoverUtils(self.log, self.pmc, self.config)
        self.callbacks = ServiceHandlers(
            self.get_logger(), self.pmc, self.mover_utils, self.config
        )

        self.xbot_pos_publisher = self.create_publisher(
            XBotInfo, "/promoc/mover/xbot_info", 10
        )

        self._setup_services()
        self.log.info(f"Connecting to PMC at {self.config.pmc_ip}...")
        self.connection_timer = self.create_timer(0.1, self._try_connect)
        self.log.info("Mover service node initialized. Waiting for PMC connection...")

    def _try_connect(self):
        if self.is_connected:
            return
        try:
            self.is_connected = self.pmc.connect(self.config.pmc_ip)
        except Exception as exc:
            self.log.debug(f"Connection attempt failed: {exc}")
            return
        if self.is_connected:
            self.log.info("PMC connected. Activating system.")
            self.connection_timer.cancel()
            self._activate_system()

    def _activate_system(self):
        try:
            self.pmc.bot.activate_xbots()
            self.log.info("XBot activated")
            self._start_publisher_timer()
        except Exception as exc:
            self.log.error(f"Failed to activate XBots after connection: {exc}")

    def _load_config(self) -> MoverNodeConfig:
        self.declare_parameter("use_mock", False)
        self.declare_parameter("xbot_id", 0)
        self.declare_parameter("publish_rate", 10.0)
        self.declare_parameter("pmc_ip", "192.168.10.100")
        self.declare_parameter("xy_tolerance", 0.001)
        self.declare_parameter("six_d_tolerance", 0.001)
        self.declare_parameter("x_min", 0.055)
        self.declare_parameter("x_max", 0.420)
        self.declare_parameter("y_min", 0.055)
        self.declare_parameter("y_max", 0.180)
        self.declare_parameter("z_min", 0.000)
        self.declare_parameter("z_max", 0.004)

        config = MoverNodeConfig(
            use_mock=bool(self.get_parameter("use_mock").value),
            xbot_id=int(self.get_parameter("xbot_id").value),
            publish_rate=float(self.get_parameter("publish_rate").value),
            pmc_ip=str(self.get_parameter("pmc_ip").value),
            xy_tolerance=float(self.get_parameter("xy_tolerance").value),
            six_d_tolerance=float(self.get_parameter("six_d_tolerance").value),
            x_min=float(self.get_parameter("x_min").value),
            x_max=float(self.get_parameter("x_max").value),
            y_min=float(self.get_parameter("y_min").value),
            y_max=float(self.get_parameter("y_max").value),
            z_min=float(self.get_parameter("z_min").value),
            z_max=float(self.get_parameter("z_max").value),
        )
        self.log.info(f"Configuration loaded: {asdict(config)}")
        return config

    def _setup_services(self):
        services = [
            ("linear_motion_si", LinearMotionSi),
            ("six_dof_motion", SixDofMotion),
            ("activate_xbots", ActivateXbots),
            ("levitation_xbots", LevitationXbots),
            ("arc_motion_si", ArcMotionSi),
            ("stop_motion", StopMotion),
            ("rotary_motion", RotaryMotion),
            ("set_velocity_acceleration", SetVelocityAcceleration),
        ]
        for name, srv_type in services:
            callback = self.callbacks.get_callback(name)
            self.create_service(srv_type, f"/promoc/mover/{name}", callback)
        self.log.info("All services are created.")

    def _start_publisher_timer(self):
        publish_interval = 1.0 / self.config.publish_rate
        self.xbot_position_timer = self.create_timer(
            publish_interval, self._publish_xbot_position
        )
        if not self.pmc.status["is_mock"]:
            self.xbot_diagnosis_timer = self.create_timer(
                5.0, self.mover_utils.diagnose_xbot_availability
            )
        self.log.info("Timers started.")

    def _publish_xbot_position(self):
        if not self.is_connected:
            return

        msg = XBotInfo()
        xbot_id = self.config.xbot_id
        try:
            current_pos = self.mover_utils.get_current_position(xbot_id)
            if current_pos:
                msg.x_pos = m_to_mm(current_pos[0])
                msg.y_pos = m_to_mm(current_pos[1])
                msg.z_pos = m_to_mm(current_pos[2])
                msg.rx_pos = rad_to_deg(current_pos[3])
                msg.ry_pos = rad_to_deg(current_pos[4])
                msg.rz_pos = rad_to_deg(current_pos[5])

            msg.xbot_state = self.mover_utils.get_xbot_state_string(xbot_id)
            self.xbot_pos_publisher.publish(msg)
        except Exception as exc:
            self.log.error(f"Position publishing error: {exc}")

    def destroy_node(self):
        self.log.info("Shutting down MoverServiceNode...")
        if self.is_connected:
            try:
                self.pmc.bot.deactivate_xbots()
                self.log.info("XBots deactivated.")
            except Exception as exc:
                self.log.error(f"Error during deactivation: {exc}")
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
