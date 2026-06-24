"""Tests for the simplified camera configuration layout."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
path_str = str(ROOT / "camera_nodes")
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from camera_nodes.config import CameraNodeConfig  # noqa: E402


def test_camera_config_is_plain_dataclass():
    cfg = CameraNodeConfig(
        use_mock=True,
        camera_name="mock_cam",
        source_image_topic="/source",
        image_topic="/image",
        status_topic="/status",
        frame_id="camera",
        publish_rate_hz=15.0,
        frame_timeout_s=1.0,
        status_publish_rate_hz=1.0,
        mock_width=320,
        mock_height=240,
        mock_encoding="mono8",
    )

    assert cfg.use_mock is True
    assert cfg.camera_name == "mock_cam"
    assert cfg.mock_width == 320
    assert cfg.mock_height == 240


def test_camera_parameters_are_declared_in_node():
    node_content = (ROOT / "camera_nodes" / "camera_nodes" / "node.py").read_text()
    config_content = (ROOT / "camera_nodes" / "camera_nodes" / "config.py").read_text()

    assert 'self.declare_parameter("driver_mode", "hardware")' in node_content
    assert 'self.declare_parameter("mock.width", 640)' in node_content
    assert "load_camera_config" not in node_content
    assert "declare_camera_parameters" not in config_content
