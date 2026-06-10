"""Driver factory helpers for the unified linear-axis node."""

from __future__ import annotations

from linear_axis_nodes.config import LinearAxisConfig

from .base import LinearAxisDriver
from .hardware import ThorlabsLTS300Driver
from .sim import MockLinearAxisDriver


def create_linear_axis_driver(
    logger, config: LinearAxisConfig
) -> LinearAxisDriver:
    """Create the configured driver implementation."""
    if config.driver_mode == "mock":
        logger.info("Using mock linear-axis driver")
        return MockLinearAxisDriver(logger, config)

    logger.info("Using Thorlabs LTS300 hardware driver")
    return ThorlabsLTS300Driver(logger, config.axis_id)


__all__ = [
    "LinearAxisDriver",
    "ThorlabsLTS300Driver",
    "MockLinearAxisDriver",
    "create_linear_axis_driver",
]
