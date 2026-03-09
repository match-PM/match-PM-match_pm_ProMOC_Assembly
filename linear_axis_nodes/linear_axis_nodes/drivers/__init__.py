
"""Linear-axis driver abstractions and implementations."""

from .base import LinearAxisDriver


def __getattr__(name):
    if name == "LinearAxisDriver":
        return LinearAxisDriver
    if name == "ThorlabsLTS300Driver":
        from .hardware import ThorlabsLTS300Driver

        return ThorlabsLTS300Driver
    if name == "SimulatedLinearAxisDriver":
        from .sim import SimulatedLinearAxisDriver

        return SimulatedLinearAxisDriver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LinearAxisDriver",
    "ThorlabsLTS300Driver",
    "SimulatedLinearAxisDriver",
]
