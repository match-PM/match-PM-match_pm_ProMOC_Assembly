"""Adapter-level conversion helpers for camera runtime modules."""

from __future__ import annotations

import numpy as np


def ensure_uint8_image(image: np.ndarray) -> np.ndarray:
    """Normalize image dtype for OpenCV-based processing."""
    if image.dtype == np.uint8:
        return image
    clipped = np.clip(image, 0, 255)
    return clipped.astype(np.uint8)
