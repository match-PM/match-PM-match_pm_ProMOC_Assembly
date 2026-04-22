"""Shared models and runtime state for the linear-axis package."""

from __future__ import annotations

import threading
from enum import Enum


class OperationStatus(Enum):
    """Status of long-running linear-axis operations."""

    IDLE = "idle"
    HOMING = "homing"
    MOVING = "moving"
    JOGGING = "jogging"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


class OperationStateStore:
    """Thread-safe operation status shared across motion and admin services."""

    def __init__(self):
        self._status = OperationStatus.IDLE
        self._message = ""
        self._lock = threading.Lock()

    def get(self) -> tuple[OperationStatus, str]:
        with self._lock:
            return self._status, self._message

    def set(self, status: OperationStatus, message: str) -> None:
        with self._lock:
            self._status = status
            self._message = message

    def try_set_if(
        self,
        *,
        allowed: set[OperationStatus],
        new_status: OperationStatus,
        message: str,
    ) -> tuple[bool, OperationStatus]:
        with self._lock:
            current = self._status
            if current not in allowed:
                return False, current
            self._status = new_status
            self._message = message
            return True, current
