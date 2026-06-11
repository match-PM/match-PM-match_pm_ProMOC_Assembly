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

from .config import CameraNodeConfig, declare_camera_parameters, load_camera_config
from .drivers import CameraDriver, HardwareCameraDriver, MockCameraDriver


class CameraNode(Node):
    """Connect a camera driver, publish raw images, and publish camera status."""

    def __init__(self, *, parameter_overrides=None):
        super().__init__("camera_node", parameter_overrides=parameter_overrides)
        declare_camera_parameters(self)
        self.config = load_camera_config(self)

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

    def _create_driver(self) -> CameraDriver:
        if self.config.use_mock:
            return MockCameraDriver(self, self.config, self.get_logger())
        return HardwareCameraDriver(self, self.config, self.get_logger())

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
                if self.config.use_mock
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
        if not self.config.use_mock and stamp_key == self._last_published_stamp:
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
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
