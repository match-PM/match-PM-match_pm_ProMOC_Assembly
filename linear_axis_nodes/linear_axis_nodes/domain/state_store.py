"""Thread-safe operation status store for linear-axis services."""

from __future__ import annotations

import threading

from .status import OperationStatus


class OperationStateStore:
    """Own mutable operation status state shared across callback groups."""

    def __init__(self):
        self._status = OperationStatus.IDLE
        self._message = ""
        self._lock = threading.Lock()

    def get(self) -> tuple[OperationStatus, str]:
        """Return current status snapshot."""
        with self._lock:
            return self._status, self._message

    def set(self, status: OperationStatus, message: str) -> None:
        """Overwrite current status and status message."""
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
        """Conditionally transition state if current status is allowed."""
        with self._lock:
            current = self._status
            if current not in allowed:
                return False, current
            self._status = new_status
            self._message = message
            return True, current
