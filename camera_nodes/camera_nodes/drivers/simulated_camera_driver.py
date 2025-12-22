"""
Simulated camera driver for testing without hardware.

This driver generates synthetic images with controllable blur based on a
simulated focal plane.

How it works:
===============
    ┌─────────────────────────────────────────────────────────┐
    │  SimulatedCameraDriver                                   │
    │                                                         │
    │  focal_plane = 15.0mm (fixed focal plane)                │
    │  current_position = variable (from set_focus_position)   │
    │                                                         │
    │  Blur Amount = |current_position - focal_plane|          │
    │                                                         │
    │  ┌─────────────────────────────────────────────────────┐│
    │  │  Generated Image (640x480):                         ││
    │  │                                                     ││
    │  │         ┌─────────────┐                            ││
    │  │         │▓▓▓▓▓▓▓▓▓▓▓▓▓│  ← White rectangle          ││
    │  │         │▓▓▓▓▓▓▓▓▓▓▓▓▓│    rotated by 5°            ││
    │  │         │▓▓▓▓▓▓▓▓▓▓▓▓▓│    (Slanted Edge)           ││
    │  │         └─────────────┘                            ││
    │  │                                                     ││
    │  └─────────────────────────────────────────────────────┘│
    │                                                         │
    │  Gaussian blur is applied based on distance to focal plane.│
    └─────────────────────────────────────────────────────────┘

Slanted Edge for MTF:
=====================
The 5°-rotated rectangle creates a slanted edge, which is used for MTF
calculation according to the ISO 12233 standard.

Focus Simulation:
=================
    Position  →  Blur Amount  →  Image
    ─────────────────────────────────────
    15.0 mm   →  0            →  Sharp
    14.0 mm   →  1            →  Slightly blurry
    10.0 mm   →  5            →  Blurry
     5.0 mm   →  10 (max)     →  Very blurry

Usage:
======
    driver = SimulatedCameraDriver(logger)
    driver.connect()

    # Set the focus position (simulates axis movement):
    driver.set_focus_position(15.0)  # → sharp image
    driver.set_focus_position(10.0)  # → blurry image

    image = driver.capture_image()
"""

from typing import Optional

import cv2
import numpy as np

from .camera_driver import CameraDriver


class SimulatedCameraDriver(CameraDriver):
    """
    Simulated camera driver for testing without hardware.

    Generates synthetic images with a slanted edge and controllable blur,
    ideal for testing autofocus algorithms.

    Attributes:
        _focal_plane (float): Simulated focal plane in mm.
        _current_position (float): Current simulated Z-axis position.
        _exposure (float): Simulated exposure time (has no visual effect).
        _image_size (tuple): Image size as (width, height).
    """

    # ── Constants ──
    DEFAULT_FOCAL_PLANE = 15.0      # mm
    DEFAULT_IMAGE_WIDTH = 640       # px
    DEFAULT_IMAGE_HEIGHT = 480      # px
    MAX_BLUR = 10                   # Maximum blur kernel size
    EDGE_ANGLE = 5                  # Degrees (for slanted edge)

    def __init__(self, logger):
        """
        Initializes the simulator driver.

        Args:
            logger: Logger for output.
        """
        super().__init__(logger)

        # ── Focus Simulation ──
        self._focal_plane = self.DEFAULT_FOCAL_PLANE
        self._current_position = 0.0

        # ── Camera Settings ──
        self._exposure = 10000.0  # µs (has no visual effect)
        self._image_size = (self.DEFAULT_IMAGE_WIDTH,
                            self.DEFAULT_IMAGE_HEIGHT)

        # ── Image Cache ──
        self._latest_image: Optional[np.ndarray] = None

    # ══════════════════════════════════════════════════════════════════════════
    # CONNECTION
    # ══════════════════════════════════════════════════════════════════════════

    def connect(self, camera_name: str = None) -> bool:
        """
        Simulates a camera connection.

        Generates the first image immediately upon connection.

        Returns:
            bool: Always True, as the simulator cannot fail to connect.
        """
        self._connected = True
        self._logger.info('📷 Camera simulator connected')
        self._logger.info(f'   Focal plane is at Z = {self._focal_plane} mm')

        # Generate the initial image
        self._update_image()
        return True

    def disconnect(self):
        """Disconnects the simulator."""
        self._connected = False
        self._latest_image = None
        self._logger.info('Camera simulator disconnected')

    # ══════════════════════════════════════════════════════════════════════════
    # IMAGE CAPTURE
    # ══════════════════════════════════════════════════════════════════════════

    def capture_image(self) -> Optional[np.ndarray]:
        """
        Generates a new image with the current blur level.

        Returns:
            np.ndarray: A BGR image (640x480 by default).
        """
        self._update_image()
        return self._latest_image

    def get_latest_image(self) -> Optional[np.ndarray]:
        """
        Returns the most recently generated image.

        Returns:
            np.ndarray: BGR image, or None.
        """
        if self._latest_image is None:
            self._update_image()
        return self._latest_image

    def _update_image(self):
        """
        Generates a new image based on the current focus position.

        Steps:
        ------
        1. Calculate blur from the distance to the focal plane.
        2. Generate the slanted edge image.
        3. Apply Gaussian blur.
        """
        # ── Calculate blur amount ──
        blur_amount = abs(self._current_position - self._focal_plane)
        blur_amount = min(blur_amount, self.MAX_BLUR)

        # ── Generate image ──
        width, height = self._image_size
        self._latest_image = self._generate_slanted_edge_image(
            width, height, blur_amount
        )

    def _generate_slanted_edge_image(
        self,
        width: int,
        height: int,
        blur_amount: float
    ) -> np.ndarray:
        """
        Generates a test image containing a slanted edge.

        The image contains a white rectangle rotated by 5 degrees.
        This slanted edge allows for MTF calculation per ISO 12233.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.
            blur_amount: Blur level (0=sharp, 10=max blur).

        Returns:
            np.ndarray: A BGR image.
        """
        # ── Create a black image ──
        image = np.zeros((height, width), dtype=np.uint8)

        # ── Define rectangle coordinates (centered at 0,0) ──
        rect_width, rect_height = 200, 400
        box_coords = np.array([
            [-rect_width / 2, -rect_height / 2],
            [rect_width / 2, -rect_height / 2],
            [rect_width / 2, rect_height / 2],
            [-rect_width / 2, rect_height / 2]
        ])

        # ── Rotate by 5 degrees ──
        center_x, center_y = width // 2, height // 2
        M = cv2.getRotationMatrix2D((0, 0), self.EDGE_ANGLE, 1.0)
        rotated_coords = box_coords @ M[:, :2].T

        # ── Translate to image center ──
        rotated_coords[:, 0] += center_x
        rotated_coords[:, 1] += center_y

        # ── Fill the rectangle with white ──
        cv2.fillConvexPoly(image, np.int32(rotated_coords), 255)

        # ── Apply Gaussian blur ──
        if blur_amount > 0:
            kernel_size = int(blur_amount) * 2 + 1
            image = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

        # ── Convert to BGR for ROS compatibility ──
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    # ══════════════════════════════════════════════════════════════════════════
    # CAMERA SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    async def set_exposure(self, exposure_time: float) -> bool:
        """
        Simulates changing the exposure time.

        Note: This has no visual effect on the generated image,
        but the value is stored for completeness.

        Args:
            exposure_time: Exposure time in microseconds (µs).

        Returns:
            bool: Always True.
        """
        self._exposure = exposure_time
        self._logger.debug(f'Simulated exposure set to: {exposure_time} µs')
        return True

    def get_exposure(self) -> Optional[float]:
        """
        Returns the simulated exposure time.

        Returns:
            float: Exposure time in microseconds (µs).
        """
        return self._exposure

    def set_roi(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Changes the image size (simulating an ROI).

        Args:
            x, y: Ignored (image is always centered).
            width, height: New image dimensions.

        Returns:
            bool: True.
        """
        self._image_size = (width, height)
        self._logger.info(f'Simulated image size set to: {width}x{height}')
        self._update_image()
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # SIMULATOR-SPECIFIC
    # ══════════════════════════════════════════════════════════════════════════

    def set_focus_position(self, position: float):
        """
        Sets the simulated focus position.

        The image blur is calculated based on the distance between
        this position and the defined focal plane.

        Args:
            position: Z-axis position in mm.

        Example:
            driver.set_focus_position(15.0)  # → sharp image
            driver.set_focus_position(10.0)  # → blurry image
        """
        self._current_position = position
        self._update_image()

    def set_focal_plane(self, focal_plane: float):
        """
        Sets the focal plane (the position where the image is sharp).

        Args:
            focal_plane: Z-position of the focal plane in mm.
        """
        self._focal_plane = focal_plane
        self._logger.info(f'Focal plane changed to Z = {focal_plane} mm')
        self._update_image()
