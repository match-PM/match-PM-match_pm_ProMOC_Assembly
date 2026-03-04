"""Base class with common helper methods for camera callbacks."""

import asyncio
from datetime import datetime
import inspect
from pathlib import Path
import threading
import time

import cv2
import numpy as np

from promoc_core.promoc_exceptions import HardwareError

from promoc_core.logging import TaggedLogger, LogTags

from ..algorithms import tenengrad
from ..helpers.parameter_access import ParameterAccessor


class CallbackBase:
    """Common functionality for all camera service callbacks.

    Attributes:
        _node: Parent ROS2 node
        _driver: Camera driver instance
        logger: TaggedLogger instance
    """

    def __init__(self, node, camera_driver):
        self._node = node
        self._driver = camera_driver
        self.logger = TaggedLogger(node.get_logger(), LogTags.CAM)
        self._sift = None
        self.params = ParameterAccessor(node)

    # ==========================================================================
    # PARAMETER HELPERS
    # ==========================================================================

    def _param_raw(self, name: str, default=None):
        """Read parameter value with fallback if missing/None."""
        return self.params.raw(name, default)

    def _param_float(self, name: str, default: float) -> float:
        return self.params.as_float(name, default)

    def _param_int(self, name: str, default: int) -> int:
        return self.params.as_int(name, default)

    def _param_str(self, name: str, default: str = "") -> str:
        return self.params.as_str(name, default)

    def _param_bool(self, name: str, default: bool = False) -> bool:
        return self.params.as_bool(name, default)

    # ==========================================================================
    # IMAGE HELPERS
    # ==========================================================================

    def _get_latest_cv_image(self):
        """Retrieves the latest camera image as OpenCV array.

        Returns:
            tuple: (cv_image, timestamp_ns) or (None, None)
        """
        msg = self._node.latest_image_msg
        if msg is None:
            return None, None
        try:
            cv_img = self._node.bridge.imgmsg_to_cv2(msg, "bgr8")
            # msg.header.stamp is a Time object in rclpy, but here it might be a msg object.
            # In ROS2 python msg, stamp has sec and nanosec.
            ts = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            return cv_img, ts
        except Exception as e:
            self.logger.warn(f"Failed to convert image: {e}")
            return None, None

    def _wait_for_new_image(self, last_timestamp: int, timeout: float = 1.0):
        """Waits for an image with a newer timestamp."""
        start = time.time()
        while time.time() - start < timeout:
            _, ts = self._get_latest_cv_image()
            if ts is not None and ts > last_timestamp:
                return self._get_latest_cv_image()
            time.sleep(0.01)
        return None, None

    def _wait_for_new_frames(self, frame_count: int, timeout_per_frame: float = 1.0):
        """Wait for `frame_count` strictly newer frames and return the latest."""
        frame_count = max(0, int(frame_count))
        last_img, last_ts = self._get_latest_cv_image()
        if frame_count == 0:
            return last_img, last_ts

        if last_ts is None:
            # Try to obtain a first valid frame/timestamp.
            last_img, last_ts = self._wait_for_new_image(0, timeout=timeout_per_frame)
            if last_img is None or last_ts is None:
                return None, None

        for _ in range(frame_count):
            next_img, next_ts = self._wait_for_new_image(
                last_ts, timeout=timeout_per_frame
            )
            if next_img is None or next_ts is None:
                return None, None
            last_img, last_ts = next_img, next_ts

        return last_img, last_ts

    @staticmethod
    def _run_awaitable_blocking(awaitable_obj):
        """Run an awaitable from sync code and return its result."""
        try:
            loop = asyncio.get_running_loop()
            loop_running = loop.is_running()
        except RuntimeError:
            loop_running = False

        if not loop_running:
            return asyncio.run(awaitable_obj)

        result_box = {}
        error_box = {}

        def _runner():
            try:
                result_box["value"] = asyncio.run(awaitable_obj)
            except Exception as exc:  # pragma: no cover - best effort fallback
                error_box["error"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()

        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("value")

    def _set_exposure_us(self, exposure_time_us: float) -> bool:
        """Set exposure robustly from sync callback code."""
        result = self._driver.set_exposure(float(exposure_time_us))
        if inspect.isawaitable(result):
            result = self._run_awaitable_blocking(result)
        success = bool(True if result is None else result)
        if not success:
            raise HardwareError(
                message="Failed to set exposure",
                details={"exposure_time_us": float(exposure_time_us)},
            )
        return True

    @staticmethod
    def _get_center_roi(image: np.ndarray, size: int) -> np.ndarray:
        """Extracts a centered ROI from the image."""
        h, w = image.shape[:2]
        cy, cx = h // 2, w // 2
        half = max(1, size // 2)
        start_y = max(0, cy - half)
        end_y = min(h, cy + half)
        start_x = max(0, cx - half)
        end_x = min(w, cx + half)
        return image[start_y:end_y, start_x:end_x]

    # ==========================================================================
    # SHARPNESS METRICS
    # ==========================================================================

    def _calculate_sharpness(self, image, metric: str = "tenengrad") -> float:
        """Calculates image sharpness using Tenengrad metric."""
        return tenengrad(image)

    def _get_sift(self):
        """Lazy initialization for SIFT detector."""
        if self._sift is None:
            if hasattr(cv2, "SIFT_create"):
                self._sift = cv2.SIFT_create()
            else:
                self._sift = False
                self._node.get_logger().warn("SIFT not available in this OpenCV build.")
        return self._sift

    def _sift_weight(self, roi_gray: np.ndarray) -> float:
        """Calculates SIFT-based weighting for sharpness values."""
        sift = self._get_sift()
        if sift is False or roi_gray.size == 0:
            return 1.0

        roi_small = cv2.resize(
            roi_gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA
        )
        if roi_small.size == 0:
            return 1.0

        keypoints = sift.detect(roi_small, None)
        area = float(roi_small.shape[0] * roi_small.shape[1])
        density = (len(keypoints) / area) if area > 0 else 0.0
        return 1.0 + (density * 1000.0)

    # ==========================================================================
    # CSV EXPORT
    # ==========================================================================

    def _get_output_dir(
        self, subdirectory: str = "", operator_name: str | None = None
    ) -> Path:
        """Creates and returns the output directory."""
        username = ""
        operator_clean = (operator_name or "").strip()
        if operator_clean:
            username = operator_clean
        else:
            username = self._param_str("measurement.username", "").strip()

        base_dir = None
        try:
            base_param = self._param_str("measurement.base_path", "").strip()
            if base_param:
                base_dir = Path(base_param).expanduser()
        except Exception:
            base_dir = None
        if base_dir is None:
            base_dir = Path.home() / "Dokumente" / "Messungen"
        if username:
            output_dir = base_dir / username / subdirectory
        else:
            output_dir = base_dir / subdirectory

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _get_timestamp(self) -> str:
        """Returns the current timestamp as a string."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
