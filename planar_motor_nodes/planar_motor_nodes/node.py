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

from .config import MoverNodeConfig
from .drivers import create_planar_motor_driver
from .services import ServiceHandlers, MoverUtils


class MoverServiceNode(Node):
    """ROS node that wires a small driver boundary to the existing ROS API."""

    def __init__(self):
        super().__init__("mover_node")
        self.log = TaggedLogger(self.get_logger(), LogTags.PMC)
        self.config = self._load_config()
        self.driver = create_planar_motor_driver(self.log, self.config)
        self.runtime = MoverUtils(self.get_logger(), self.driver, self.config)
        self.callbacks = ServiceHandlers(
            self.get_logger(), self.driver, self.runtime, self.config
        )
        self._motion_group = ReentrantCallbackGroup()
        self._control_group = ReentrantCallbackGroup()
        self._publisher_group = ReentrantCallbackGroup()
        self.xbot_info_publisher = self.create_publisher(
            XBotInfo, "/promoc/mover/xbot_info", 10
        )
        self._create_services()
        try:
            self.runtime.connect_and_prepare()
        except Exception as exc:
            self.log.error(f"Startup connection failed: {exc}")
        self.create_timer(
            1.0 / self.config.publish_rate,
            self._publish_xbot_info,
            callback_group=self._publisher_group,
        )
        self.log.info(f"Planar motor configuration: {asdict(self.config)}")

    def _load_config(self) -> MoverNodeConfig:
        defaults = {
            "use_mock": False,
            "xbot_id": 0,
            "publish_rate": 10.0,
            "pmc_ip": "192.168.10.100",
            "auto_activate": True,
            "movement_timeout": 10.0,
            "mock_xbot_count": 1,
            "xy_tolerance": 0.001,
            "six_d_tolerance": 0.001,
            "x_min": 0.055,
            "x_max": 0.420,
            "y_min": 0.055,
            "y_max": 0.180,
            "z_min": 0.0,
            "z_max": 0.004,
            "default_xy_vel": 0.05,
            "default_xy_max_accel": 0.2,
            "default_z_vel": 0.01,
            "default_z_max_accel": 0.05,
            "default_rx_vel": 0.17453292519943295,
            "default_ry_vel": 0.17453292519943295,
            "default_rz_vel": 0.2617993877991494,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        return MoverNodeConfig(
            use_mock=bool(self.get_parameter("use_mock").value),
            xbot_id=int(self.get_parameter("xbot_id").value),
            publish_rate=float(self.get_parameter("publish_rate").value),
            pmc_ip=str(self.get_parameter("pmc_ip").value),
            auto_activate=bool(self.get_parameter("auto_activate").value),
            movement_timeout=float(self.get_parameter("movement_timeout").value),
            mock_xbot_count=int(self.get_parameter("mock_xbot_count").value),
            xy_tolerance=float(self.get_parameter("xy_tolerance").value),
            six_d_tolerance=float(self.get_parameter("six_d_tolerance").value),
            x_min=float(self.get_parameter("x_min").value),
            x_max=float(self.get_parameter("x_max").value),
            y_min=float(self.get_parameter("y_min").value),
            y_max=float(self.get_parameter("y_max").value),
            z_min=float(self.get_parameter("z_min").value),
            z_max=float(self.get_parameter("z_max").value),
            default_xy_vel=float(self.get_parameter("default_xy_vel").value),
            default_xy_max_accel=float(
                self.get_parameter("default_xy_max_accel").value
            ),
            default_z_vel=float(self.get_parameter("default_z_vel").value),
            default_z_max_accel=float(
                self.get_parameter("default_z_max_accel").value
            ),
            default_rx_vel=float(self.get_parameter("default_rx_vel").value),
            default_ry_vel=float(self.get_parameter("default_ry_vel").value),
            default_rz_vel=float(self.get_parameter("default_rz_vel").value),
        )

    def _create_services(self) -> None:
        service_types = {
            "linear_motion_si": LinearMotionSi,
            "six_dof_motion": SixDofMotion,
            "activate_xbots": ActivateXbots,
            "levitation_xbots": LevitationXbots,
            "arc_motion_si": ArcMotionSi,
            "stop_motion": StopMotion,
            "rotary_motion": RotaryMotion,
            "set_velocity_acceleration": SetVelocityAcceleration,
        }
        for registration in self.callbacks.iter_service_registry():
            group = (
                self._motion_group
                if self.callbacks.get_group(registration.service_name) == "motion"
                else self._control_group
            )
            self.create_service(
                service_types[registration.service_name],
                f"/promoc/mover/{registration.service_name}",
                self.callbacks.get_callback(registration.service_name),
                callback_group=group,
            )

    def _publish_xbot_info(self) -> None:
        try:
            message = self.runtime.build_info_message(self.config.xbot_id)
        except Exception as exc:
            self.log.debug(f"Skipping XBot info publish: {exc}")
            return
        if message is not None:
            message.device_status.stamp = self.get_clock().now().to_msg()
            self.xbot_info_publisher.publish(message)

    def destroy_node(self):
        self.runtime.shutdown()
        super().destroy_node()


def main(args=None):
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
