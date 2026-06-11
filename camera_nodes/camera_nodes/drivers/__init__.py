"""Camera driver exports with lazy hardware/mock loading."""

from __future__ import annotations

from typing import Any

from .base import CameraDriver, CameraFrame


def __getattr__(name: str) -> Any:
    if name in {"MockCameraDriver", "SimulatedCameraDriver"}:
        from .mock import MockCameraDriver

        return MockCameraDriver
    if name in {"HardwareCameraDriver", "AravisCameraDriver"}:
        from .hardware import HardwareCameraDriver

        return HardwareCameraDriver
    if name == "CameraDriver":
        return CameraDriver
    if name == "CameraFrame":
        return CameraFrame
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CameraDriver",
    "CameraFrame",
    "HardwareCameraDriver",
    "MockCameraDriver",
    "AravisCameraDriver",
    "SimulatedCameraDriver",
]
