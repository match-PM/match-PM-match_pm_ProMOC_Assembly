#!/usr/bin/env python3
"""Single camera node for raw image acquisition and status publication."""

from __future__ import annotations

from promoc_assembly_interfaces.msg import DeviceStatus
from promoc_core import error_codes
from promoc_core.promoc_exceptions import ProMocError
from promoc_core.status import DeviceState
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

from .config import CameraNodeConfig
from .drivers.base import CameraDriver
from .drivers.hardware import HardwareCameraDriver
from .drivers.mock import MockCameraDriver


class CameraNode(Node):
    """Connect a camera driver, publish raw images, and publish camera status."""

    def __init__(self, *, parameter_overrides=None):
        super().__init__("camera_node", parameter_overrides=parameter_overrides)
        self.config = self._load_config()

        self.image_publisher = self.create_publisher(Image, self.config.image_topic, 10)
        self.status_publisher = self.create_publisher(
            DeviceStatus, self.config.status_topic, 10
        )

        self._device_state = DeviceState.DISCONNECTED
        self._error_code = error_codes.SUCCESS
        self._status_message = "camera node created"
        self._last_published_stamp: tuple[int, int] | None = None
        self._frame_timer = None

        self.driver: CameraDriver = self._create_driver()
        self.status_timer = self.create_timer(
            1.0 / self.config.status_publish_rate_hz,
            self.publish_status,
        )

        self._set_status(
            DeviceState.CONNECTING,
            error_codes.SUCCESS,
            f"connecting {self.config.camera_name}",
        )
        self._start_runtime()

    def _load_config(self) -> CameraNodeConfig:
        self.declare_parameter("driver_mode", "hardware")
        self.declare_parameter("camera_name", "assembly_camera")
        self.declare_parameter(
            "source_image_topic",
            "/promoc/assembly_camera/stream0/image_raw",
        )
        self.declare_parameter("image_topic", "/promoc/camera/image_raw")
        self.declare_parameter("status_topic", "/promoc/camera/status")
        self.declare_parameter("frame_id", "assembly_camera_frame")
        self.declare_parameter("publish_rate_hz", 15.0)
        self.declare_parameter("frame_timeout_s", 1.0)
        self.declare_parameter("status_publish_rate_hz", 1.0)
        self.declare_parameter("mock.width", 640)
        self.declare_parameter("mock.height", 480)
        self.declare_parameter("mock.encoding", "mono8")

        driver_mode = str(self.get_parameter("driver_mode").value).strip().lower()
        if driver_mode not in {"hardware", "mock"}:
            raise ValueError(
                f"driver_mode must be 'hardware' or 'mock', got '{driver_mode}'"
            )

        publish_rate_hz = self._positive_float_param("publish_rate_hz", 15.0)
        frame_timeout_s = self._positive_float_param("frame_timeout_s", 1.0)
        status_rate_hz = self._positive_float_param("status_publish_rate_hz", 1.0)

        return CameraNodeConfig(
            driver_mode=driver_mode,
            camera_name=str(self.get_parameter("camera_name").value),
            source_image_topic=str(self.get_parameter("source_image_topic").value),
            image_topic=str(self.get_parameter("image_topic").value),
            status_topic=str(self.get_parameter("status_topic").value),
            frame_id=str(self.get_parameter("frame_id").value),
            publish_rate_hz=publish_rate_hz,
            frame_timeout_s=frame_timeout_s,
            status_publish_rate_hz=status_rate_hz,
            mock_width=max(1, self._int_param("mock.width", 640)),
            mock_height=max(1, self._int_param("mock.height", 480)),
            mock_encoding=str(self.get_parameter("mock.encoding").value),
        )

    def _positive_float_param(self, name: str, default: float) -> float:
        try:
            value = float(self.get_parameter(name).value)
        except (TypeError, ValueError):
            return float(default)
        return value if value > 0.0 else float(default)

    def _int_param(self, name: str, default: int) -> int:
        try:
            return int(self.get_parameter(name).value)
        except (TypeError, ValueError):
            return int(default)

    def _create_driver(self) -> CameraDriver:
        if self.config.driver_mode == "mock":
            return MockCameraDriver(self, self.config)
        if self.config.driver_mode == "hardware":
            return HardwareCameraDriver(self, self.config)
        raise ValueError(
            f"driver_mode must be 'hardware' or 'mock', got '{self.config.driver_mode}'"
        )

    def _start_runtime(self) -> None:
        try:
            self.driver.connect()
            self._set_status(
                DeviceState.CONNECTED,
                error_codes.SUCCESS,
                f"connected {self.config.camera_name}",
            )
            self.driver.start_acquisition()
            wait_message = (
                f"publishing mock stream on {self.config.image_topic}"
                if self.config.driver_mode == "mock"
                else f"waiting for frames on {self.config.source_image_topic}"
            )
            self._set_status(DeviceState.CONNECTED, error_codes.SUCCESS, wait_message)
            self._frame_timer = self.create_timer(
                1.0 / self.config.publish_rate_hz,
                self._publish_next_frame,
            )
        except ProMocError as exc:
            self._set_status(DeviceState.ERROR, exc.error_code, str(exc))
            self.get_logger().error(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            self._set_status(
                DeviceState.ERROR,
                error_codes.UNKNOWN_ERROR,
                f"startup failure: {exc}",
            )
            self.get_logger().error(f"startup failure: {exc}")

    def _publish_next_frame(self) -> None:
        try:
            frame = self.driver.read_frame(self.config.frame_timeout_s)
        except ProMocError as exc:
            self._set_status(DeviceState.ERROR, exc.error_code, str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._set_status(
                DeviceState.ERROR,
                error_codes.UNKNOWN_ERROR,
                f"frame read failure: {exc}",
            )
            return

        message = Image()
        message.header.stamp = frame.stamp or self.get_clock().now().to_msg()
        message.header.frame_id = frame.frame_id or self.config.frame_id
        message.height = int(frame.height)
        message.width = int(frame.width)
        message.encoding = str(frame.encoding)
        message.is_bigendian = 0
        message.step = int(frame.step)
        message.data = frame.data

        stamp_key = (message.header.stamp.sec, message.header.stamp.nanosec)
        if (
            self.config.driver_mode == "hardware"
            and stamp_key == self._last_published_stamp
        ):
            return

        self.image_publisher.publish(message)
        self._last_published_stamp = stamp_key
        self._set_status(
            DeviceState.READY,
            error_codes.SUCCESS,
            (
                f"streaming {self.config.camera_name} "
                f"{message.width}x{message.height} {message.encoding}"
            ),
        )

    def publish_status(self) -> None:
        try:
            self.status_publisher.publish(self._device_status_message())
        except Exception:  # pragma: no cover - ROS shutdown edge case
            return None

    def _device_status_message(self) -> DeviceStatus:
        message = DeviceStatus()
        message.stamp = self.get_clock().now().to_msg()
        message.state = int(self._device_state)
        message.error_code = int(self._error_code)
        message.message = self._status_message
        return message

    def _set_status(self, state: DeviceState, error_code: int, message: str) -> None:
        changed = (
            state != self._device_state
            or int(error_code) != int(self._error_code)
            or message != self._status_message
        )
        self._device_state = state
        self._error_code = int(error_code)
        self._status_message = str(message)
        if changed:
            self.publish_status()

    def destroy_node(self) -> bool:
        self._device_state = DeviceState.STOPPED
        self._error_code = error_codes.SUCCESS
        self._status_message = "stopping camera node"
        try:
            self.driver.stop_acquisition()
        except ProMocError as exc:
            self._device_state = DeviceState.ERROR
            self._error_code = int(exc.error_code)
            self._status_message = str(exc)
            self.get_logger().error(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            self._device_state = DeviceState.ERROR
            self._error_code = error_codes.UNKNOWN_ERROR
            self._status_message = f"shutdown failure: {exc}"
            self.get_logger().error(f"shutdown failure: {exc}")
        try:
            self.driver.disconnect()
        except ProMocError as exc:
            self._device_state = DeviceState.ERROR
            self._error_code = int(exc.error_code)
            self._status_message = str(exc)
            self.get_logger().error(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            self._device_state = DeviceState.ERROR
            self._error_code = error_codes.UNKNOWN_ERROR
            self._status_message = f"shutdown failure: {exc}"
            self.get_logger().error(f"shutdown failure: {exc}")
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
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
