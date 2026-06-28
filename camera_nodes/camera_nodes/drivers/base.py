"""Small driver contract for the reduced camera runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from builtin_interfaces.msg import Time


@dataclass(frozen=True)
class CameraFrame:
    """Minimal image payload returned by hardware and mock drivers."""

    width: int
    height: int
    encoding: str
    step: int
    data: bytes
    stamp: Time | None = None
    frame_id: str = ""


class CameraDriver(ABC):
    """Small internal camera-driver contract."""

    def __init__(self) -> None:
        self._connected = False
        self._acquiring = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_acquiring(self) -> bool:
        return self._acquiring

    @abstractmethod
    def connect(self) -> None:
        """Connect to the camera transport."""

    @abstractmethod
    def disconnect(self) -> None:
        """Release camera resources."""

    @abstractmethod
    def start_acquisition(self) -> None:
        """Start continuous acquisition."""

    @abstractmethod
    def stop_acquisition(self) -> None:
        """Stop continuous acquisition."""

    @abstractmethod
    def read_frame(self, timeout_s: float) -> CameraFrame:
        """Read one frame or raise a meaningful error."""
