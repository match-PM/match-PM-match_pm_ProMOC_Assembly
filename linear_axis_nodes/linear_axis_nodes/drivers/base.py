"""Abstract driver contract shared by hardware and mock linear axes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class LinearAxisDriver(ABC):
    """Small device interface used by the unified axis node."""

    @abstractmethod
    def connect(self, port: str = None) -> bool:
        """Connect to the axis device."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the axis device."""

    @abstractmethod
    def move_absolute(self, position: float, timeout: Optional[float] = None) -> None:
        """Move to an absolute position in millimeters."""

    @abstractmethod
    def move_relative(self, distance: float, timeout: Optional[float] = None) -> None:
        """Move by a relative distance in millimeters."""

    @abstractmethod
    def home(self, timeout: float = 180.0) -> None:
        """Home the axis."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the current motion."""

    @abstractmethod
    def jog_positive(
        self, step_size: float = 1.0, timeout: Optional[float] = None
    ) -> None:
        """Jog in the positive direction."""

    @abstractmethod
    def jog_negative(
        self, step_size: float = 1.0, timeout: Optional[float] = None
    ) -> None:
        """Jog in the negative direction."""

    @abstractmethod
    def get_position(self) -> float:
        """Return the current position in millimeters."""

    @abstractmethod
    def is_moving(self) -> bool:
        """Return whether the axis is currently moving."""

    @abstractmethod
    def get_serial_number(self) -> str:
        """Return the device serial number."""

    @abstractmethod
    def get_axis_type(self) -> str:
        """Return the configured axis identifier."""

    @abstractmethod
    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """Return (min_velocity, acceleration, max_velocity)."""

    @abstractmethod
    def set_velocity_parameters(
        self,
        min_velocity: Optional[float] = None,
        acceleration: Optional[float] = None,
        max_velocity: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Set velocity parameters and return the applied values."""

    @abstractmethod
    def validate_position(self, position: float) -> bool:
        """Return whether the position is within the driver's own hard limits."""
