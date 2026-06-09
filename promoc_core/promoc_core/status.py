"""Shared device and axis status values for ProMOC assembly nodes."""

from enum import IntEnum


class DeviceState(IntEnum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    NOT_READY = 3
    READY = 4
    BUSY = 5
    STOPPED = 6
    ERROR = 7


class AxisState(IntEnum):
    UNKNOWN = 0
    UNHOMED = 1
    HOMING = 2
    HOMED = 3
