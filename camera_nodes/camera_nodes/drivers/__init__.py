"""Camera driver abstractions.

Provides driver abstraction layer with lazy loading to avoid import failures
during test collection when optional dependencies are missing.

Some drivers (e.g., Aravis) depend on optional ROS interfaces that may not be
installed in minimal environments. Using lazy imports via __getattr__ prevents
import-time failures.

Usage:
    from camera_nodes.drivers import CameraDriver
    from camera_nodes.drivers import AravisCameraDriver  # Loaded on demand
"""

from __future__ import annotations

from typing import Any

from .base import CameraDriver


def __getattr__(name: str) -> Any:
    """Lazily import driver implementations.

    This avoids import-time failures during test collection when optional
    dependencies for hardware drivers are not installed.
    """
    if name == 'AravisCameraDriver':
        from .hardware import AravisCameraDriver

        return AravisCameraDriver
    if name == 'CameraDriver':
        return CameraDriver
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


__all__ = ['CameraDriver', 'AravisCameraDriver']
