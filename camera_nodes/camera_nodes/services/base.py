"""Base class with common helper methods for camera service handlers."""

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
from ..preview import is_bayer_encoding, ros_image_to_bgr8_preview


class ParameterAccessor:
    """Small adapter to centralize typed ROS parameter reads."""

    def __init__(self, node):
        self._node = node

    def raw(self, name: str, default=None):
        if not self._node.has_parameter(name):
            return default
        value = self._node.get_parameter(name).value
        if value is None:
            return default
        return value

    def as_float(self, name: str, default: float) -> float:
        value = self.raw(name, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def as_int(self, name: str, default: int) -> int:
        value = self.raw(name, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def as_str(self, name: str, default: str = "") -> str:
        value = self.raw(name, default)
        try:
            return str(value)
        except Exception:
            return str(default)

    def as_bool(self, name: str, default: bool = False) -> bool:
        value = self.raw(name, default)
        try:
            return bool(value)
        except Exception:
            return bool(default)


class CallbackBase:
    """Common functionality for camera service handlers.

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
        self._warned_image_failures: set[str] = set()

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
            ts = self._msg_timestamp_ns(msg)
            return cv_img, ts
        except Exception as e:
            encoding = str(getattr(msg, "encoding", ""))
            try:
                if not is_bayer_encoding(encoding):
                    raise
                cv_img = ros_image_to_bgr8_preview(msg, self._convert_image_msg)
                ts = self._msg_timestamp_ns(msg)
                return cv_img, ts
            except Exception as fallback_exc:
                self._warn_once(
                    f"latest_cv_image:{encoding.lower() or 'unknown'}",
                    "Failed to convert image for OpenCV processing "
                    f"(encoding={encoding or 'unknown'}, direct={e}, fallback={fallback_exc})",
                )
                return None, None

    def _warn_once(self, key: str, message: str):
        """Log one warning per repeated conversion problem."""
        if key in self._warned_image_failures:
            return
        self._warned_image_failures.add(key)
        self.logger.warn(message)

    def _msg_timestamp_ns(self, msg) -> int:
        """Return ROS header timestamp in nanoseconds for an image-like message."""
        if msg is None or not hasattr(msg, "header"):
            return 0
        stamp = getattr(msg.header, "stamp", None)
        if stamp is None:
            return 0
        return int(getattr(stamp, "sec", 0)) * 1_000_000_000 + int(
            getattr(stamp, "nanosec", 0)
        )

    def _get_latest_image_timestamp_ns(self) -> int:
        """Return timestamp of the latest cached image message."""
        return self._msg_timestamp_ns(self._node.latest_image_msg)

    def _convert_image_msg(self, msg, desired_encoding: str):
        """Convert an image message through cv_bridge with one desired encoding."""
        if msg is None:
            return None
        return self._node.bridge.imgmsg_to_cv2(msg, desired_encoding=desired_encoding)

    def _get_latest_passthrough_image(self):
        """Return latest image without forcing debayer/color conversion.

        Returns:
            tuple: (image, timestamp_ns, encoding) or (None, None, "")
        """
        msg = self._node.latest_image_msg
        if msg is None:
            return None, None, ""
        encoding = str(getattr(msg, "encoding", ""))
        try:
            image = self._convert_image_msg(msg, "passthrough")
            return image, self._msg_timestamp_ns(msg), encoding
        except Exception as exc:
            self._warn_once(
                f"latest_passthrough:{encoding.lower() or 'unknown'}",
                "Failed to convert passthrough image "
                f"(encoding={encoding or 'unknown'}): {exc}",
            )
            return None, None, encoding

    def _wait_for_new_image_from(
        self,
        fetch_image_fn,
        last_timestamp: int,
        timeout: float = 1.0,
        empty_result=(None, None),
    ):
        """Wait for a newer image using a caller-provided fetch function."""
        start = time.time()
        while time.time() - start < timeout:
            fetched = fetch_image_fn()
            if not fetched:
                time.sleep(0.01)
                continue
            ts = fetched[1] if len(fetched) > 1 else None
            if ts is not None and ts > last_timestamp:
                return fetch_image_fn()
            time.sleep(0.01)
        return empty_result

    def _wait_for_new_image(self, last_timestamp: int, timeout: float = 1.0):
        """Waits for an image with a newer timestamp."""
        image, ts = self._wait_for_new_image_from(
            self._get_latest_cv_image,
            last_timestamp,
            timeout=timeout,
            empty_result=(None, None),
        )
        return image, ts

    def _wait_for_new_passthrough_image(self, last_timestamp: int, timeout: float = 1.0):
        """Wait for a newer image without forcing bgr8 conversion."""
        image, ts, encoding = self._wait_for_new_image_from(
            self._get_latest_passthrough_image,
            last_timestamp,
            timeout=timeout,
            empty_result=(None, None, ""),
        )
        return image, ts, encoding

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
