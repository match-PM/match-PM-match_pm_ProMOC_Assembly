"""Unit tests for reduced camera config loading."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
path_str = str(ROOT / "camera_nodes")
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from camera_nodes.config import declare_camera_parameters, load_camera_config  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


class _Logger:
    def __init__(self):
        self.warnings = []

    def warn(self, message):
        self.warnings.append(str(message))


class _Node:
    def __init__(self):
        self._params = {}
        self._logger = _Logger()

    def declare_parameter(self, name, default):
        self._params.setdefault(name, default)

    def has_parameter(self, name):
        return name in self._params

    def get_parameter(self, name):
        return _Param(self._params[name])

    def get_logger(self):
        return self._logger


def test_declare_and_load_camera_config():
    node = _Node()
    declare_camera_parameters(node)

    node._params["driver_mode"] = "mock"
    node._params["camera_name"] = "mock_cam"
    node._params["mock.width"] = 320
    node._params["mock.height"] = 240
    node._params["publish_rate_hz"] = 12.5

    cfg = load_camera_config(node)
    assert cfg.use_mock is True
    assert cfg.camera_name == "mock_cam"
    assert cfg.mock_width == 320
    assert cfg.mock_height == 240
    assert cfg.publish_rate_hz == 12.5




def test_invalid_driver_mode_falls_back_to_hardware():
    node = _Node()
    declare_camera_parameters(node)
    node._params["driver_mode"] = "broken"

    cfg = load_camera_config(node)
    assert cfg.use_mock is False
    assert node.get_logger().warnings
