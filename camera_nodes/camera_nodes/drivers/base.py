"""
Abstract base class for camera drivers.

Defines the interface that all camera drivers must implement, providing
a consistent API for camera control independent of hardware type.

Implementations:
- AravisCameraDriver: Real camera via camera_aravis2 ROS2 wrapper
- SimulatedCameraDriver: Simulator for testing without hardware

Interface:
- Connection: connect(), disconnect(), is_connected property
- Image capture: capture_image(), get_latest_image()
- Settings: set_exposure(), get_exposure(), set_roi()

Usage:
    driver: CameraDriver = AravisCameraDriver(node, logger)
    if driver.connect():
        image = driver.capture_image()
        driver.disconnect()
"""

from abc import ABC, abstractmethod

from typing import Optional

import numpy as np


class CameraDriver(ABC):
    """
    Abstract base class for all camera drivers.

    All concrete driver implementations must inherit from this class
    and implement all abstract methods.

    Attributes:
        connected (bool): Connection status to the hardware.
        logger: Logger for output.
    """

    def __init__(self, logger):
        """
        Initializes the base driver.

        Args:
            logger: Logger instance for output.
        """
        self._logger = logger
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Returns whether the camera is connected."""
        return self._connected

    # ══════════════════════════════════════════════════════════════════════════
    # CONNECTION
    # ══════════════════════════════════════════════════════════════════════════

    @abstractmethod
    def connect(self, camera_name: str = None) -> bool:
        """
        Connects to the camera.

        Args:
            camera_name: Camera identifier (e.g., IP address, serial number).
                         Can be None for the simulator.

        Returns:
            bool: True if the connection is successful.

        Raises:
            DeviceNotFoundError: If the camera cannot be found.
            DriverNotAvailableError: If a required driver library is missing.
            HardwareError: For any other connection failure.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnects from the camera and releases resources.

        Should be called on node shutdown.
        """
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # IMAGE CAPTURE
    # ══════════════════════════════════════════════════════════════════════════

    @abstractmethod
    def capture_image(self) -> Optional[np.ndarray]:
        """
        Captures and returns a single image.

        Returns:
            np.ndarray: BGR image as a NumPy array, or None on failure.

        Raises:
            CommunicationError: If not connected to the camera.
            HardwareError: If an error occurs during capture.
        """
        pass

    @abstractmethod
    def get_latest_image(self) -> Optional[np.ndarray]:
        """
        Returns the most recently captured image.

        Unlike capture_image(), this method does not trigger a new capture
        but returns the last cached image.

        Returns:
            np.ndarray: BGR image as a NumPy array, or None if no image is available.
        """
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # CAMERA SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def set_exposure(self, exposure_time: float) -> bool:
        """
        Sets the camera's exposure time.

        Args:
            exposure_time: Exposure time in microseconds (µs).

        Returns:
            bool: True if successful.

        Raises:
            CommunicationError: If the control service is not available.
            HardwareError: If the camera reports an error.
        """
        pass

    @abstractmethod
    def get_exposure(self) -> Optional[float]:
        """
        Returns the current exposure time.

        Returns:
            float: Exposure time in microseconds (µs), or None on failure.
        """
        pass

    @abstractmethod
    def set_roi(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Sets the Region of Interest (ROI).

        Args:
            x: X-offset in pixels.
            y: Y-offset in pixels.
            width: Width in pixels.
            height: Height in pixels.

        Returns:
            bool: True if successful.
        """
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # SIMULATOR-SPECIFIC
    # ══════════════════════════════════════════════════════════════════════════

    def set_focus_position(self, position: float):
        """
        Sets the simulated focus position (for simulator only).

        This method has no effect on real camera drivers.

        Args:
            position: Simulated Z-position for focus calculation.
        """
        pass  # Default implementation does nothing.
