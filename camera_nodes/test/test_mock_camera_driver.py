# ruff: noqa: E402
"""Unit tests for the minimal mock camera driver."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("camera_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from camera_nodes.config import CameraNodeConfig
from camera_nodes.drivers.mock import MockCameraDriver
from promoc_core.promoc_exceptions import ConfigurationError


class _Clock:
    def now(self):
        return self

    def to_msg(self):
        return type("Stamp", (), {"sec": 1, "nanosec": 2})()


class _Node:
    def get_clock(self):
        return _Clock()


def _config(**overrides) -> CameraNodeConfig:
    values = {
        "driver_mode": "mock",
        "camera_name": "mock_camera",
        "source_image_topic": "/unused",
        "image_topic": "/promoc/camera/image_raw",
        "status_topic": "/promoc/camera/status",
        "frame_id": "mock_frame",
        "publish_rate_hz": 10.0,
        "frame_timeout_s": 1.0,
        "status_publish_rate_hz": 1.0,
        "mock_width": 64,
        "mock_height": 48,
        "mock_encoding": "mono8",
    }
    values.update(overrides)
    return CameraNodeConfig(**values)


def test_mock_driver_connects_starts_and_stops():
    driver = MockCameraDriver(_Node(), _config())
    driver.connect()
    driver.start_acquisition()

    frame = driver.read_frame(0.5)
    assert frame.width == 64
    assert frame.height == 48
    assert frame.encoding == "mono8"
    assert len(frame.data) == 64 * 48

    driver.stop_acquisition()
    driver.disconnect()
    assert driver.is_connected is False
    assert driver.is_acquiring is False


def test_mock_driver_rejects_invalid_configuration():
    driver = MockCameraDriver(
        _Node(),
        _config(mock_width=0),
    )
    try:
        driver.connect()
    except ConfigurationError as exc:
        assert exc.error_code != 0
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ConfigurationError")
