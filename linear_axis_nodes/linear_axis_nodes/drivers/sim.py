"""Mock linear-axis driver for development and tests."""

from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

from promoc_core.promoc_exceptions import CommunicationError, MovementTimeoutError

from linear_axis_nodes.config import LinearAxisConfig

from .base import LinearAxisDriver


class MockLinearAxisDriver(LinearAxisDriver):
    """Blocking mock driver with stop support and configurable soft limits."""

    def __init__(self, logger, config: LinearAxisConfig):
        self.logger = logger
        self.config = config
        self.connected = False
        self._position = config.min_position
        self._moving = False
        self._velocity = (0.0, config.default_acceleration, config.default_velocity)
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()

    def connect(self, port: str = None) -> bool:
        _ = port
        with self._lock:
            self.connected = True
            self._moving = False
            self._stop_requested.clear()
        self.logger.info("Connected to mock linear axis")
        return True

    def disconnect(self) -> None:
        with self._lock:
            self.connected = False
            self._moving = False
            self._stop_requested.set()
        self.logger.info("Mock linear axis disconnected")

    def move_absolute(self, position: float, timeout: Optional[float] = None) -> None:
        self._run_move(float(position), timeout)

    def move_relative(self, distance: float, timeout: Optional[float] = None) -> None:
        self._run_move(self.get_position() + float(distance), timeout)

    def home(self, timeout: float = 180.0) -> None:
        self._run_move(self.config.min_position, timeout)

    def stop(self) -> None:
        self._stop_requested.set()

    def get_position(self) -> float:
        with self._lock:
            return self._position

    def is_moving(self) -> bool:
        with self._lock:
            return self._moving

    def get_serial_number(self) -> str:
        return self.config.serial_number or f"MOCK-{self.config.axis_id.upper()}"

    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        with self._lock:
            return self._velocity

    def set_velocity_parameters(
        self, min_velocity=None, acceleration=None, max_velocity=None
    ) -> Tuple[float, float, float]:
        with self._lock:
            current = list(self._velocity)
            if min_velocity is not None:
                current[0] = float(min_velocity)
            if acceleration is not None:
                current[1] = float(acceleration)
            if max_velocity is not None:
                current[2] = float(max_velocity)
            self._velocity = tuple(current)
            return self._velocity

    def validate_position(self, position: float) -> bool:
        return self.config.min_position <= float(position) <= self.config.max_position

    def _ensure_connected(self) -> None:
        if not self.connected:
            raise CommunicationError("Mock driver is not connected")

    def _run_move(self, target: float, timeout: Optional[float]) -> None:
        self._ensure_connected()
        if not self.validate_position(target):
            raise ValueError(f"Target {target:.3f} mm is outside configured limits")

        with self._lock:
            start = self._position
            self._moving = True
            self._stop_requested.clear()

        speed = max(self.get_velocity_parameters()[2], 0.1)
        duration_s = max(abs(target - start) / speed, 0.2)
        duration_s = min(duration_s, 1.0)
        started = time.monotonic()
        deadline = started + timeout if timeout is not None else None

        while True:
            elapsed = time.monotonic() - started
            if deadline is not None and time.monotonic() > deadline:
                with self._lock:
                    self._moving = False
                raise MovementTimeoutError("Mock movement timed out")
            if self._stop_requested.is_set():
                with self._lock:
                    self._moving = False
                return
            if elapsed >= duration_s:
                with self._lock:
                    self._position = target
                    self._moving = False
                return

            progress = elapsed / duration_s
            with self._lock:
                self._position = start + (target - start) * progress
            time.sleep(0.02)
