"""Configuration helpers for the reduced camera runtime."""

from __future__ import annotations

from dataclasses import dataclass


PARAMETER_DEFAULTS: tuple[tuple[str, object], ...] = (
    ("driver_mode", "hardware"),
    ("camera_name", "assembly_camera"),
    ("source_image_topic", "/promoc/assembly_camera/stream0/image_raw"),
    ("image_topic", "/promoc/camera/image_raw"),
    ("status_topic", "/promoc/camera/status"),
    ("frame_id", "assembly_camera_frame"),
    ("publish_rate_hz", 15.0),
    ("frame_timeout_s", 1.0),
    ("status_publish_rate_hz", 1.0),
    ("mock.width", 640),
    ("mock.height", 480),
    ("mock.encoding", "mono8"),
)


@dataclass(frozen=True)
class CameraNodeConfig:
    """Resolved runtime settings for the camera node."""

    use_mock: bool
    camera_name: str
    source_image_topic: str
    image_topic: str
    status_topic: str
    frame_id: str
    publish_rate_hz: float
    frame_timeout_s: float
    status_publish_rate_hz: float
    mock_width: int
    mock_height: int
    mock_encoding: str


def declare_camera_parameters(node) -> None:
    """Declare all camera-node parameters with their defaults."""
    for name, default in PARAMETER_DEFAULTS:
        node.declare_parameter(name, default)


def get_camera_param(node, name: str, default=None):
    """Read a parameter value with a fallback for missing or null values."""
    if not node.has_parameter(name):
        return default
    value = node.get_parameter(name).value
    return default if value is None else value


def load_camera_config(node) -> CameraNodeConfig:
    """Load and normalize the reduced camera runtime configuration."""
    driver_mode = str(get_camera_param(node, "driver_mode", "hardware")).strip().lower()

    if driver_mode not in {"hardware", "mock", "sim", "simulator"}:
        node.get_logger().warn(
            f"Invalid driver_mode '{driver_mode}', falling back to hardware."
        )
        driver_mode = "hardware"

    publish_rate_hz = _float_param(node, "publish_rate_hz", 15.0)
    frame_timeout_s = _float_param(node, "frame_timeout_s", 1.0)
    status_publish_rate_hz = _float_param(node, "status_publish_rate_hz", 1.0)

    return CameraNodeConfig(
        use_mock=driver_mode in {"mock", "sim", "simulator"},
        camera_name=str(get_camera_param(node, "camera_name", "assembly_camera")),
        source_image_topic=str(
            get_camera_param(node, "source_image_topic", "/promoc/assembly_camera/stream0/image_raw")
        ),
        image_topic=str(get_camera_param(node, "image_topic", "/promoc/camera/image_raw")),
        status_topic=str(get_camera_param(node, "status_topic", "/promoc/camera/status")),
        frame_id=str(get_camera_param(node, "frame_id", "assembly_camera_frame")),
        publish_rate_hz=publish_rate_hz if publish_rate_hz > 0.0 else 15.0,
        frame_timeout_s=frame_timeout_s if frame_timeout_s > 0.0 else 1.0,
        status_publish_rate_hz=(
            status_publish_rate_hz if status_publish_rate_hz > 0.0 else 1.0
        ),
        mock_width=max(1, _int_param(node, "mock.width", 640)),
        mock_height=max(1, _int_param(node, "mock.height", 480)),
        mock_encoding=str(get_camera_param(node, "mock.encoding", "mono8")),
    )


def load_camera_runtime_config(node) -> CameraNodeConfig:
    """Compatibility alias for existing tests and callers."""
    return load_camera_config(node)


def _float_param(node, name: str, default: float) -> float:
    try:
        return float(get_camera_param(node, name, default))
    except (TypeError, ValueError):
        return float(default)


def _int_param(node, name: str, default: int) -> int:
    try:
        return int(get_camera_param(node, name, default))
    except (TypeError, ValueError):
        return int(default)
