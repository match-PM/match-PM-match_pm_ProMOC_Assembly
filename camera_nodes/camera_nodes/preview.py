"""Helpers to derive stable preview images from raw ROS camera frames."""

from __future__ import annotations

import cv2
import numpy as np


_BAYER_CODE_MAP = {
    "bayer_rggb": getattr(cv2, "COLOR_BayerRG2BGR", None),
    "bayer_bggr": getattr(cv2, "COLOR_BayerBG2BGR", None),
    "bayer_gbrg": getattr(cv2, "COLOR_BayerGB2BGR", None),
    "bayer_grbg": getattr(cv2, "COLOR_BayerGR2BGR", None),
}


def is_bayer_encoding(encoding: str) -> bool:
    """Return True when a ROS encoding string describes a Bayer mosaic."""
    return "bayer" in str(encoding or "").lower()


def normalize_raw_to_u8_preview(image: np.ndarray, encoding: str = "") -> np.ndarray:
    """Normalize a raw image array into an 8-bit preview-friendly representation."""
    if image is None:
        raise ValueError("image must not be None")

    if image.dtype == np.uint8:
        return image

    if image.size == 0:
        return np.zeros(image.shape, dtype=np.uint8)

    max_value = float(np.max(image))
    if max_value <= 0.0:
        max_value = 1.0

    encoding_lc = str(encoding or "").lower()
    if np.issubdtype(image.dtype, np.integer):
        # BayerRG12 is usually transported in a 16-bit container with a 0..4095 payload.
        if "16" in encoding_lc and max_value <= 4095.0:
            scale_base = 4095.0
        else:
            scale_base = 65535.0 if max_value > 255.0 else 255.0
    else:
        scale_base = max_value

    return np.clip(
        image.astype(np.float32) * (255.0 / scale_base),
        0,
        255,
    ).astype(np.uint8)


def raw_array_to_bgr8_preview(image: np.ndarray, encoding: str = "") -> np.ndarray:
    """Convert a passthrough ROS image array into a BGR8 preview image."""
    encoding_lc = str(encoding or "").lower()
    preview_u8 = normalize_raw_to_u8_preview(image, encoding_lc)

    for key, code in _BAYER_CODE_MAP.items():
        if key in encoding_lc:
            if code is None:
                return cv2.cvtColor(preview_u8, cv2.COLOR_GRAY2BGR)
            return cv2.cvtColor(preview_u8, code)

    if preview_u8.ndim == 2:
        return cv2.cvtColor(preview_u8, cv2.COLOR_GRAY2BGR)

    if preview_u8.ndim == 3 and preview_u8.shape[2] == 3 and "rgb" in encoding_lc:
        return cv2.cvtColor(preview_u8, cv2.COLOR_RGB2BGR)

    return preview_u8


def ros_image_to_bgr8_preview(msg, convert_image_fn) -> np.ndarray:
    """Convert a ROS image message to a BGR8 preview using passthrough data."""
    raw = convert_image_fn(msg, "passthrough")
    encoding = str(getattr(msg, "encoding", ""))
    return raw_array_to_bgr8_preview(raw, encoding)
