"""Operation status definitions for linear-axis service callbacks."""

from __future__ import annotations

from enum import Enum


class OperationStatus(Enum):
    """Status of long-running linear-axis operations."""

    IDLE = "idle"
    HOMING = "homing"
    MOVING = "moving"
    JOGGING = "jogging"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
