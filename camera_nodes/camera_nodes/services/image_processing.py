"""Small camera-image helpers used by the runtime node."""

import cv2
import numpy as np
from typing import Optional


class CameraImageProcessing:
    """Keep lightweight image helpers close to the camera node."""

    def __init__(self, logger, pixel_size_um: float = 2.40):
        self.logger = logger
        self.pixel_size_um = float(pixel_size_um)

    def draw_crosshair(
        self,
        image: np.ndarray,
        color: tuple = (0, 0, 255),
        line_length: Optional[int] = None,
        thickness: int = 2,
        gap: int = 10,
    ) -> np.ndarray:
        """Draw a centered crosshair overlay on a copy of the image."""
        if image is None or image.size == 0:
            self.logger.warning("Empty image provided to draw_crosshair")
            return image

        overlay = image.copy()
        height, width = overlay.shape[:2]
        center_x, center_y = width // 2, height // 2

        if line_length is None:
            line_length = min(width, height) // 20

        cv2.line(
            overlay,
            (center_x - line_length, center_y),
            (center_x - gap, center_y),
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.line(
            overlay,
            (center_x + gap, center_y),
            (center_x + line_length, center_y),
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.line(
            overlay,
            (center_x, center_y - line_length),
            (center_x, center_y - gap),
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.line(
            overlay,
            (center_x, center_y + gap),
            (center_x, center_y + line_length),
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.circle(overlay, (center_x, center_y), 3, color, -1, cv2.LINE_AA)
        return overlay
