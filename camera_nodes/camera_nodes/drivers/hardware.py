"""Hardware driver wrapper around the external ROS image stream."""

from __future__ import annotations

import time

from promoc_core import error_codes
from promoc_core.promoc_exceptions import (
    CommunicationError,
    CommunicationTimeoutError,
    ConfigurationError,
    HardwareError,
)
from sensor_msgs.msg import Image

from .base import CameraDriver, CameraFrame


class HardwareCameraDriver(CameraDriver):
    """Read frames from the existing camera ROS topic without vendor imports."""

    def __init__(self, node, config, logger) -> None:
        super().__init__(logger)
        self._node = node
        self._config = config
        self._subscription = None
        self._latest_message: Image | None = None
        self._last_receive_monotonic = 0.0

    def connect(self) -> None:
        topic = self._config.source_image_topic.strip()
        if not topic:
            raise ConfigurationError(
                "source_image_topic must not be empty",
                error_code=error_codes.INVALID_CONFIGURATION,
            )
        if self._subscription is None:
            self._subscription = self._node.create_subscription(
                Image,
                topic,
                self._handle_image,
                10,
            )
        self._connected = True

    def disconnect(self) -> None:
        if self._subscription is not None:
            self._node.destroy_subscription(self._subscription)
            self._subscription = None
        self._latest_message = None
        self._last_receive_monotonic = 0.0
        self._acquiring = False
        self._connected = False

    def start_acquisition(self) -> None:
        if not self._connected:
            raise CommunicationError(
                "camera stream is not connected",
                error_code=error_codes.CONNECTION_FAILED,
            )
        self._acquiring = True

    def stop_acquisition(self) -> None:
        self._acquiring = False

    def read_frame(self, timeout_s: float) -> CameraFrame:
        if not self._connected:
            raise CommunicationError(
                "camera stream is not connected",
                error_code=error_codes.CONNECTION_FAILED,
            )
        if not self._acquiring:
            raise CommunicationError(
                "camera acquisition has not started",
                error_code=error_codes.DEVICE_NOT_READY,
            )
        if self._latest_message is None:
            raise CommunicationTimeoutError(
                f"waiting for frames on {self._config.source_image_topic}",
                error_code=error_codes.CONNECTION_TIMEOUT,
            )

        age_s = time.monotonic() - self._last_receive_monotonic
        if timeout_s > 0.0 and age_s > timeout_s:
            raise CommunicationTimeoutError(
                f"frame timeout on {self._config.source_image_topic}",
                error_code=error_codes.CONNECTION_TIMEOUT,
            )

        message = self._latest_message
        if message.width <= 0 or message.height <= 0 or not message.data:
            raise HardwareError(
                "received invalid image data",
                error_code=error_codes.DRIVER_FAILURE,
            )

        return CameraFrame(
            width=int(message.width),
            height=int(message.height),
            encoding=str(message.encoding or "mono8"),
            step=int(message.step),
            data=bytes(message.data),
            stamp=message.header.stamp,
            frame_id=message.header.frame_id or self._config.frame_id,
        )

    def _handle_image(self, message: Image) -> None:
        self._latest_message = message
        self._last_receive_monotonic = time.monotonic()
