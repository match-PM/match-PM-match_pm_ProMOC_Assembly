"""
Aravis camera driver for real hardware.

This driver communicates with the `camera_aravis2` ROS2 driver, which controls
GigE Vision cameras using the Aravis library.

Architecture:
=============
    ┌─────────────────────────────────────────────────────────┐
    │  AravisCameraDriver                                      │
    │                                                         │
    │  ┌─────────────────┐       ┌─────────────────────────┐ │
    │  │ capture_image() │──────▶│ Image Subscriber        │ │
    │  └─────────────────┘       │ /assembly_camera/image  │ │
    │                            └─────────────────────────┘ │
    │                                                         │
    │  ┌─────────────────┐       ┌─────────────────────────┐ │
    │  │ set_exposure()  │──────▶│ Service Client          │ │
    │  └─────────────────┘       │ .../set_exposure_time   │ │
    │                            └─────────────────────────┘ │
    └─────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────┐
    │  camera_aravis2 Node (external ROS2 driver)             │
    │  - Provides Aravis GigE Vision interface.               │
    │  - Publishes images and offers control services.        │
    └─────────────────────────────────────────────────────────┘

Dependencies:
=============
    - `camera_aravis2`: Must be running as a separate node.
    - `pm_genicam_controller_interfaces`: Required for service definitions.

Usage:
======
    driver = AravisCameraDriver(node, logger)

    if driver.connect():
        await driver.set_exposure(10000.0)  # 10ms
        image = driver.get_latest_image()
        driver.disconnect()
"""

from typing import Optional

import numpy as np

from promoc_core.promoc_exceptions import (
    CommunicationError,
    DriverNotAvailableError,
    HardwareError,
)

from .camera_driver import CameraDriver


class AravisCameraDriver(CameraDriver):
    """
    Camera driver for real hardware via the `camera_aravis2` package.

    This driver acts as a wrapper around the ROS2 services and topics
    provided by the `camera_aravis2` driver node.

    Attributes:
        _node: The parent ROS2 node used for creating service clients.
        _exposure_client: Service client for exposure control.
        _latest_image: The most recently received image (from a subscriber).
        _current_exposure: The current exposure time in microseconds.
    """

    def __init__(self, node, logger):
        """
        Initializes the Aravis driver.

        Args:
            node: The parent ROS2 node (for creating service clients).
            logger: A logger instance for output.
        """
        super().__init__(logger)
        self._node = node

        # ── Service client for exposure control ──
        self._exposure_client = None
        self._SetExposureTime = None

        # ── Image cache ──
        self._latest_image: Optional[np.ndarray] = None
        self._current_exposure: float = 10000.0  # Default: 10ms

    # ══════════════════════════════════════════════════════════════════════════
    # CONNECTION
    # ══════════════════════════════════════════════════════════════════════════

    def connect(self, camera_name: str = None) -> bool:
        """
        Initializes the connection to the camera_aravis2 driver.

        Steps:
        ------
        1. Import the required service definitions.
        2. Create the service client.
        3. (Optional) Wait for the service to become available.

        Args:
            camera_name: Ignored (the camera is defined by the driver node).

        Returns:
            bool: True if the service client was created successfully.

        Raises:
            DriverNotAvailableError: If the required interface package is not found.
        """
        self._logger.info('Connecting to camera_aravis2 driver...')

        try:
            # ── Import service type ──
            from pm_genicam_controller_interfaces.srv import SetExposureTime
            self._SetExposureTime = SetExposureTime

            # ── Create service client ──
            self._exposure_client = self._node.create_client(
                self._SetExposureTime,
                '/promoc/assembly_camera_controller/set_exposure_time'
            )

            self._connected = True
            self._logger.info('✓ Aravis driver connected')
            return True

        except ImportError as e:
            raise DriverNotAvailableError(
                message='pm_genicam_controller_interfaces not available',
                details={'error': str(e), 'driver': 'camera_aravis2'}
            )

    def disconnect(self):
        """Disconnects and releases resources."""
        self._connected = False
        self._exposure_client = None
        self._latest_image = None
        self._logger.info('Aravis driver disconnected')

    # ══════════════════════════════════════════════════════════════════════════
    # IMAGE CAPTURE
    # ══════════════════════════════════════════════════════════════════════════

    def capture_image(self) -> Optional[np.ndarray]:
        """
        Returns the current camera image.

        Note: Since camera_aravis2 streams continuously, this is identical
        to get_latest_image().

        Returns:
            np.ndarray: BGR image as a NumPy array, or None.
        """
        return self.get_latest_image()

    def get_latest_image(self) -> Optional[np.ndarray]:
        """
        Returns the most recently received image.

        The image is set by the image subscriber in `camera_node.py`.

        Returns:
            np.ndarray: BGR image, or None if no image is available.
        """
        return self._latest_image

    def set_latest_image(self, image: np.ndarray):
        """
        Sets the latest image (called from an image subscriber).

        Args:
            image: BGR image as a NumPy array.
        """
        self._latest_image = image

    # ══════════════════════════════════════════════════════════════════════════
    # CAMERA SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    async def set_exposure(self, exposure_time: float) -> bool:
        """
        Sets the exposure time via the camera_aravis2 service.

        Args:
            exposure_time: Exposure time in microseconds (µs).

        Returns:
            bool: True if successful.

        Raises:
            CommunicationError: If the service is not available.
            HardwareError: If the camera reports an error.
        """
        if self._exposure_client is None:
            raise CommunicationError('Exposure service client not initialized.')

        if not self._exposure_client.service_is_ready():
            raise CommunicationError(
                'camera_aravis2 service not ready. Is the driver node running?'
            )

        # ── Call service ──
        request = self._SetExposureTime.Request()
        request.exposure_time = exposure_time

        try:
            future = self._exposure_client.call_async(request)
            response = await future

            if not response.success:
                raise HardwareError(
                    message=f'Failed to set exposure: {response.error}',
                    details={'exposure_time': exposure_time}
                )

            self._current_exposure = exposure_time
            return True

        except Exception as e:
            if isinstance(e, (HardwareError, CommunicationError)):
                raise
            raise HardwareError(
                message=f'Error setting exposure: {e}',
                details={'exposure_time': exposure_time}
            )

    def get_exposure(self) -> Optional[float]:
        """
        Returns the currently set exposure time.

        Returns:
            float: Exposure time in microseconds (µs).
        """
        return self._current_exposure

    def set_roi(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Sets the Region of Interest (ROI).

        Note: Currently not implemented for camera_aravis2. The ROI
        should be configured via the driver's launch parameters.

        Returns:
            bool: False (not supported).
        """
        self._logger.warning(
            'Changing ROI at runtime is not supported. '
            'Configure the ROI via camera_aravis2 launch parameters.'
        )
        return False
