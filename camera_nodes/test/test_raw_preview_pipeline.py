"""Regression tests for raw Bayer preview conversion on the messstand."""

from __future__ import annotations

from pathlib import Path
import sys
import types

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camera_nodes.algorithms.roi_detection import RoiDetector  # noqa: E402
from camera_nodes.preview import raw_array_to_bgr8_preview  # noqa: E402
from camera_nodes.services.base import CallbackBase  # noqa: E402


class _Logger:
    def __init__(self):
        self.warn_messages = []

    def warn(self, *_args, **_kwargs):
        if _args:
            self.warn_messages.append(str(_args[0]))
        return None

    def warning(self, *_args, **_kwargs):
        return self.warn(*_args, **_kwargs)

    def info(self, *_args, **_kwargs):
        return None


class _Bridge:
    def __init__(self, raw_image: np.ndarray):
        self._raw_image = raw_image

    def imgmsg_to_cv2(self, _msg, desired_encoding="passthrough"):
        if desired_encoding == "bgr8":
            raise RuntimeError("direct bgr8 conversion unavailable for raw Bayer")
        if desired_encoding == "passthrough":
            return self._raw_image
        raise RuntimeError(f"unexpected encoding request: {desired_encoding}")


class _Node:
    def __init__(self, raw_image: np.ndarray):
        self.bridge = _Bridge(raw_image)
        self.latest_image_msg = types.SimpleNamespace(
            encoding="bayer_rggb16",
            header=types.SimpleNamespace(
                stamp=types.SimpleNamespace(sec=1, nanosec=2)
            ),
        )
        self._logger = _Logger()

    def get_logger(self):
        return self._logger

    def has_parameter(self, _name: str) -> bool:
        return False


class _BrokenBridge(_Bridge):
    def imgmsg_to_cv2(self, _msg, desired_encoding="passthrough"):
        raise RuntimeError(f"broken conversion for {desired_encoding}")


def test_raw_array_to_bgr8_preview_normalizes_bayer_rggb16():
    raw = np.array(
        [
            [0, 1024, 2048, 3072],
            [512, 1536, 2560, 3584],
            [256, 1280, 2304, 3328],
            [768, 1792, 2816, 4095],
        ],
        dtype=np.uint16,
    )

    preview = raw_array_to_bgr8_preview(raw, "bayer_rggb16")

    assert preview.dtype == np.uint8
    assert preview.shape == (4, 4, 3)
    assert int(preview.max()) <= 255


def test_callback_base_get_latest_cv_image_falls_back_to_raw_preview():
    raw = np.array(
        [
            [0, 4095],
            [2048, 1024],
        ],
        dtype=np.uint16,
    )
    callback = CallbackBase(_Node(raw), camera_driver=object())

    image, timestamp_ns = callback._get_latest_cv_image()

    assert image is not None
    assert image.dtype == np.uint8
    assert image.shape == (2, 2, 3)
    assert timestamp_ns == 1_000_000_002


def test_roi_detection_accepts_uint16_grayscale_input():
    image = np.zeros((80, 80), dtype=np.uint16)
    image[20:60, 20:60] = 4095

    vis_img, bars, squares = RoiDetector.detect_targets(image)

    assert vis_img.dtype == np.uint8
    assert vis_img.shape == (80, 80, 3)
    assert isinstance(bars, list)
    assert isinstance(squares, list)


def test_callback_base_warns_once_for_repeated_preview_conversion_failure():
    raw = np.array([[0, 4095], [2048, 1024]], dtype=np.uint16)
    node = _Node(raw)
    node.bridge = _BrokenBridge(raw)
    callback = CallbackBase(node, camera_driver=object())

    first_image, first_timestamp_ns = callback._get_latest_cv_image()
    second_image, second_timestamp_ns = callback._get_latest_cv_image()

    assert first_image is None
    assert first_timestamp_ns is None
    assert second_image is None
    assert second_timestamp_ns is None
    assert len(node.get_logger().warn_messages) == 1
    assert "Failed to convert image for OpenCV processing" in node.get_logger().warn_messages[0]
