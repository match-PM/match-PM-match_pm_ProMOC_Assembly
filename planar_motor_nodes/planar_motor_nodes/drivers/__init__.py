"""Tracked planar-motor driver boundary and implementations."""

from .base import PlanarMotorDriver
from .hardware import HardwarePlanarMotorDriver
from .mock import MockPlanarMotorDriver


def create_planar_motor_driver(logger, config) -> PlanarMotorDriver:
    """Create either the mock or hardware driver for the node."""
    if config.driver_mode in ("mock", "sim", "simulator"):
        return MockPlanarMotorDriver(logger, mock_xbot_count=config.mock_xbot_count)
    return HardwarePlanarMotorDriver(logger)


__all__ = [
    "PlanarMotorDriver",
    "HardwarePlanarMotorDriver",
    "MockPlanarMotorDriver",
    "create_planar_motor_driver",
]
