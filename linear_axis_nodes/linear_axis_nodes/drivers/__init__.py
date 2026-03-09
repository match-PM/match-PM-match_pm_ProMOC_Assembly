"""Driver selection helpers for the linear-axis package."""

from __future__ import annotations

from .base import LinearAxisDriver
from .hardware import ThorlabsLTS300Driver
from .sim import SimulatedLinearAxisDriver
from promoc_core.logging import LogTags, TaggedLogger


def create_linear_axis_driver(logger, config) -> LinearAxisDriver:
    """Create the active driver from the node config."""
    if config.use_sim_time:
        driver = SimulatedLinearAxisDriver()
        driver.set_logger(TaggedLogger(logger._logger, LogTags.MOCK))
        logger.info("Using basic simulation driver for LTS300")
        return driver

    logger.info("Using Thorlabs LTS300 hardware driver")
    return ThorlabsLTS300Driver(logger)


def connect_linear_axis_driver(driver: LinearAxisDriver, logger, config) -> bool:
    """Connect the selected driver with config-specific setup."""
    try:
        serial = config.serial_number
        port = config.serial_port
        logger.info(f"Connecting to device with S/N {serial} on port {port}...")

        if config.use_sim_time:
            connected = driver.connect()
            if connected:
                logger.info("Connected in simulation mode")
        else:
            connected = driver.connect(port=port)
            if connected:
                device_serial = driver.get_serial_number()
                if device_serial != serial:
                    logger.warn(
                        f"Expected S/N {serial}, but device reports {device_serial}"
                    )
                logger.info(f"Connected to Thorlabs LTS300 (S/N: {device_serial})")
                poll_interval = config.position_poll_interval_s
                if (
                    hasattr(driver, "start_position_polling")
                    and poll_interval
                    and poll_interval > 0
                ):
                    driver.start_position_polling(poll_interval)
        return connected
    except Exception as exc:
        logger.error(f"Connection failed: {exc}")
        return False


__all__ = [
    "LinearAxisDriver",
    "ThorlabsLTS300Driver",
    "SimulatedLinearAxisDriver",
    "create_linear_axis_driver",
    "connect_linear_axis_driver",
]
