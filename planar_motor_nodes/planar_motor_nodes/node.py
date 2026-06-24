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
    """ROS node that wires a small driver boundary to the existing ROS API."""

    def __init__(self):
        super().__init__("mover_node")
        self.log = TaggedLogger(self.get_logger(), LogTags.PMC)
        self.config = self._load_config()
        self.driver = self._create_driver()
        self.runtime = MoverUtils(self.get_logger(), self.driver, self.config)
        self.motion_callbacks = MotionCallbacks(
            self.get_logger(), self.driver, self.runtime, self.config
        )
        self.control_callbacks = ControlCallbacks(
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
        for name, value in DEFAULT_MOVER_NODE_PARAMETERS.items():
            self.declare_parameter(name, value)
        values = {
            name: self.get_parameter(name).value
            for name in DEFAULT_MOVER_NODE_PARAMETERS
        }
        return MoverNodeConfig.from_mapping(values)

    def _create_driver(self):
        if self.config.driver_mode in ("mock", "sim", "simulator"):
            return MockPlanarMotorDriver(
                self.log,
                mock_xbot_count=self.config.mock_xbot_count,
            )
        return HardwarePlanarMotorDriver(self.log)

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
