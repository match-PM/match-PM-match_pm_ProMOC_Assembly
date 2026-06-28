"""Tiny local dummy driver for linear-axis development without hardware."""

from __future__ import annotations

from typing import Optional, Tuple

from promoc_core.promoc_exceptions import CommunicationError

from linear_axis_nodes.config import LinearAxisConfig

from .base import LinearAxisDriver


class MockLinearAxisDriver(LinearAxisDriver):
    """Minimal in-memory axis.

    It is not a motion simulation. Commands update the stored position
    immediately so the ROS node can be started and clicked through at home.
    """

    def __init__(self, logger, config: LinearAxisConfig):
        self.logger = logger
        self.config = config
        self.connected = False
        self._position = config.min_position
        self._moving = False
        self._velocity = (0.0, config.default_acceleration, config.default_velocity)

    def connect(self, port: str = None) -> bool:
        _ = port
        self.connected = True
        self.logger.info("Connected to mock linear axis")
        return True

    def disconnect(self) -> None:
        self.connected = False
        self._moving = False

    def move_absolute(self, position: float, timeout: Optional[float] = None) -> None:
        _ = timeout
        self._ensure_connected()
        self._set_position(position)

    def move_relative(self, distance: float, timeout: Optional[float] = None) -> None:
        _ = timeout
        self._ensure_connected()
        self._set_position(self._position + float(distance))

    def jog(self, step_size: float, timeout: Optional[float] = None) -> None:
        _ = timeout
        self._ensure_connected()
        self._set_position(self._position + float(step_size))

    def home(self, timeout: float = 180.0) -> None:
        _ = timeout
        self._ensure_connected()
        self._position = self.config.min_position

    def stop(self) -> None:
        self._moving = False

    def get_position(self) -> float:
        self._ensure_connected()
        return self._position

    def is_moving(self) -> bool:
        return self._moving

    def get_serial_number(self) -> str:
        return self.config.serial_number or f"MOCK-{self.config.axis_id.upper()}"

    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        return self._velocity

    def set_velocity_parameters(
        self,
        min_velocity: Optional[float] = None,
        acceleration: Optional[float] = None,
        max_velocity: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        current = list(self._velocity)
        if min_velocity is not None:
            current[0] = float(min_velocity)
        if acceleration is not None:
            current[1] = float(acceleration)
        if max_velocity is not None:
            current[2] = float(max_velocity)
        self._velocity = tuple(current)
        return self._velocity

    def _set_position(self, position: float) -> None:
        position = float(position)
        if position < self.config.min_position or position > self.config.max_position:
            raise ValueError(f"Target {position:.3f} mm is outside configured limits")
        self._position = position

    def _ensure_connected(self) -> None:
        if not self.connected:
            raise CommunicationError("Mock driver is not connected")
