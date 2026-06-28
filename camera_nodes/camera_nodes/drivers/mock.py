"""Minimal mock camera driver for vendor-free development."""

from __future__ import annotations

from promoc_core import error_codes
from promoc_core.promoc_exceptions import CommunicationError, ConfigurationError

from .base import CameraDriver, CameraFrame


_ENCODING_CHANNELS = {
    "mono8": 1,
    "rgb8": 3,
    "bgr8": 3,
}


class MockCameraDriver(CameraDriver):
    """Generate a plain black image stream without hardware dependencies."""

    def __init__(self, node, config) -> None:
        super().__init__()
        self._node = node
        self._config = config

    def connect(self) -> None:
        if self._config.mock_width <= 0 or self._config.mock_height <= 0:
            raise ConfigurationError(
                "mock image dimensions must be positive",
                error_code=error_codes.INVALID_CONFIGURATION,
            )
        if self._config.mock_encoding not in _ENCODING_CHANNELS:
            raise ConfigurationError(
                f"unsupported mock encoding '{self._config.mock_encoding}'",
                error_code=error_codes.INVALID_CONFIGURATION,
            )
        self._connected = True

    def disconnect(self) -> None:
        self._acquiring = False
        self._connected = False

    def start_acquisition(self) -> None:
        if not self._connected:
            raise CommunicationError(
                "mock camera is not connected",
                error_code=error_codes.CONNECTION_FAILED,
            )
        self._acquiring = True

    def stop_acquisition(self) -> None:
        self._acquiring = False

    def read_frame(self, timeout_s: float) -> CameraFrame:
        _ = timeout_s
        if not self._connected:
            raise CommunicationError(
                "mock camera is not connected",
                error_code=error_codes.CONNECTION_FAILED,
            )
        if not self._acquiring:
            raise CommunicationError(
                "mock camera acquisition has not started",
                error_code=error_codes.DEVICE_NOT_READY,
            )

        channels = _ENCODING_CHANNELS[self._config.mock_encoding]
        step = self._config.mock_width * channels
        data = bytes(step * self._config.mock_height)
        return CameraFrame(
            width=self._config.mock_width,
            height=self._config.mock_height,
            encoding=self._config.mock_encoding,
            step=step,
            data=data,
            stamp=self._node.get_clock().now().to_msg(),
            frame_id=self._config.frame_id,
        )
