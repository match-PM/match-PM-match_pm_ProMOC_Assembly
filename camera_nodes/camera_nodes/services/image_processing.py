<<<<<<< HEAD
"""Small camera-image helpers used by the runtime node."""

import cv2
import numpy as np
from typing import Optional


class CameraImageProcessing:
    """Keep lightweight image helpers close to the camera node."""

    def __init__(self, logger, pixel_size_um: float = 2.40):
        self.logger = logger
        self.pixel_size_um = float(pixel_size_um)
=======
"""Small helpers for MTF ROI analysis and debug overlays."""

import csv
from typing import Optional

import cv2
import numpy as np

from ..algorithms.mtf import MTFAnalyzer, MTFConfig


class CameraImageProcessing:
    """Wrap MTF analysis plus one small debug-overlay helper."""

    def __init__(self, logger, pixel_size_um: float = 2.40):
        self.logger = logger
        self._config = MTFConfig(pixel_size_um=pixel_size_um)
        self._analyzer = MTFAnalyzer(self._config)

    def calculate_mtf_from_roi(
        self,
        roi_image,
        oversample_factor: int = 4,
    ) -> Optional[dict]:
        """Return MTF arrays and headline values for a selected ROI."""
        if roi_image is None or roi_image.size == 0:
            self.logger.error("Empty ROI provided")
            return None

        self._config.oversample_factor = oversample_factor
        result = self._analyzer.compute_mtf(roi_image)
        if not result.valid:
            self.logger.error(f"MTF calculation failed: {result.error_msg}")
            return None
        if getattr(result, "warning_msg", ""):
            self.logger.warning(f"MTF warning: {result.warning_msg}")

        return {
            "frequency": result.frequencies,
            "mtf": result.mtf_values,
            "mtf50": result.mtf50,
            "mtf20": result.mtf20,
            "mtf10": result.mtf10,
            "edge_angle": result.edge_angle,
        }

    def export_to_csv(self, data_dict: dict, filename: str) -> None:
        """Write iterable MTF data to CSV."""
        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(list(data_dict.keys()))
            array_data = {
                key: value
                for key, value in data_dict.items()
                if hasattr(value, "__iter__") and not isinstance(value, str)
            }
            if array_data:
                writer.writerows(zip(*array_data.values()))

        self.logger.info(f"Data successfully exported to {filename}")
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

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
