"""Typed configuration object for the camera node."""

from __future__ import annotations

from dataclasses import dataclass


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
