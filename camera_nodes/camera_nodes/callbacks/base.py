"""Base class with common helper methods for camera callbacks."""

import csv
from datetime import datetime
from pathlib import Path
import time

import cv2
import numpy as np

from promoc_core.promoc_exceptions import (
    ConfigurationError,
    HardwareError,
    ImageProcessingError,
    ServiceError,
)

from promoc_core.logging import TaggedLogger, LogTags

from ..algorithms import tenengrad


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
            cv_img = self._node.bridge.imgmsg_to_cv2(msg, 'bgr8')
            # msg.header.stamp is a Time object in rclpy, but here it might be a msg object.
            # In ROS2 python msg, stamp has sec and nanosec.
            ts = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            return cv_img, ts
        except Exception as e:
            self.logger.warn(f'Failed to convert image: {e}')
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

    def _calculate_sharpness(self, image, metric: str = 'tenengrad') -> float:
        """Calculates image sharpness using Tenengrad metric."""
        return tenengrad(image)

    def _get_sift(self):
        """Lazy initialization for SIFT detector."""
        if self._sift is None:
            if hasattr(cv2, 'SIFT_create'):
                self._sift = cv2.SIFT_create()
            else:
                self._sift = False
                self._node.get_logger().warn(
                    'SIFT not available in this OpenCV build.')
        return self._sift

    def _sift_weight(self, roi_gray: np.ndarray) -> float:
        """Calculates SIFT-based weighting for sharpness values."""
        sift = self._get_sift()
        if sift is False or roi_gray.size == 0:
            return 1.0

        roi_small = cv2.resize(roi_gray, None, fx=0.5, fy=0.5, 
                               interpolation=cv2.INTER_AREA)
        if roi_small.size == 0:
            return 1.0

        keypoints = sift.detect(roi_small, None)
        area = float(roi_small.shape[0] * roi_small.shape[1])
        density = (len(keypoints) / area) if area > 0 else 0.0
        return 1.0 + (density * 1000.0)

    # ==========================================================================
    # CSV EXPORT
    # ==========================================================================

    def _get_output_dir(self, subdirectory: str = '', operator_name: str | None = None) -> Path:
        """Creates and returns the output directory."""
        username = ''
        operator_clean = (operator_name or '').strip()
        if operator_clean:
            username = operator_clean
        elif self._node.has_parameter('measurement.username'):
            username = self._node.get_parameter(
                'measurement.username').get_parameter_value().string_value.strip()

        base_dir = None
        if self._node.has_parameter('measurement.base_path'):
            try:
                base_param = self._node.get_parameter(
                    'measurement.base_path').get_parameter_value().string_value.strip()
                if base_param:
                    base_dir = Path(base_param).expanduser()
            except Exception:
                base_dir = None
        if base_dir is None:
            base_dir = Path.home() / 'Dokumente' / 'Messungen'
        if username:
            output_dir = base_dir / username / subdirectory
        else:
            output_dir = base_dir / subdirectory
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _get_timestamp(self) -> str:
        """Returns the current timestamp as a string."""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
