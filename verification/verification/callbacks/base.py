"""Shared helper methods for scientific verification callbacks."""

import csv
from datetime import datetime
from pathlib import Path
import time

import numpy as np


class ScientificVerificationBase:
    """Base mixin with image and file I/O helper methods."""

    # ==========================================================================
    # PARAMETER HELPERS
    # ==========================================================================

    def _param_raw(self, name: str, default=None):
        """Read parameter value with fallback if missing/None."""
        if not self.has_parameter(name):
            return default
        value = self.get_parameter(name).value
        if value is None:
            return default
        return value

    def _param_float(self, name: str, default: float) -> float:
        value = self._param_raw(name, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _param_int(self, name: str, default: int) -> int:
        value = self._param_raw(name, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _param_str(self, name: str, default: str = "") -> str:
        value = self._param_raw(name, default)
        try:
            return str(value)
        except Exception:
            return str(default)

    def _param_bool(self, name: str, default: bool = False) -> bool:
        value = self._param_raw(name, default)
        try:
            return bool(value)
        except Exception:
            return bool(default)

    def image_callback(self, msg):
        self.latest_image_msg = msg

    def _stamp_to_tuple(self, msg) -> tuple[int, int] | None:
        """Extract ROS timestamp tuple (sec, nsec) if available."""
        if msg is None:
            return None
        try:
            stamp = msg.header.stamp
            return int(stamp.sec), int(stamp.nanosec)
        except Exception:
            return None

    def _convert_msg_to_cv2(self, msg):
        if msg is None:
            return None
        try:
            return self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().warn(f"Image conversion failed: {e}")
            return None

    def _get_latest_cv_image(self):
        return self._convert_msg_to_cv2(self.latest_image_msg)

    def _wait_for_fresh_cv_image(
        self,
        previous_stamp: tuple[int, int] | None = None,
        timeout_sec: float = 2.0,
    ) -> tuple[np.ndarray | None, tuple[int, int] | None]:
        """Wait for a fresh image (new header timestamp)."""
        start = time.time()
        while time.time() - start < timeout_sec:
            msg = self.latest_image_msg
            stamp = self._stamp_to_tuple(msg)
            if msg is not None and (previous_stamp is None or stamp != previous_stamp):
                return self._convert_msg_to_cv2(msg), stamp
            time.sleep(0.01)

        msg = self.latest_image_msg
        return self._convert_msg_to_cv2(msg), self._stamp_to_tuple(msg)

    def _get_output_dir(
        self, subdirectory: str = "", operator_name: str | None = None
    ) -> Path:
        """Create and return the output directory."""
        username = (operator_name or "").strip()
        base_dir = Path(self._param_str("results_dir", ""))

        if username:
            output_dir = base_dir / username / subdirectory
        else:
            output_dir = base_dir / subdirectory

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _get_measurement_metadata(self) -> dict:
        """Collect basic metadata."""
        return {
            "timestamp": datetime.now().isoformat(),
            "node": self.get_name(),
            "pixel_size_um": self._param_raw("pixel_size_um", None),
        }

    def _write_csv_with_metadata(
        self, filepath: Path, metadata: dict, fieldnames: list, rows: list
    ) -> None:
        """Write CSV file with scientific metadata header."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write("# VERIFICATION_REPORT\n")
            for key, value in metadata.items():
                f.write(f"# {key}: {value}\n")
            f.write("#\n")
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
