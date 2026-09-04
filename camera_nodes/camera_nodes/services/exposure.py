"""Manual and deterministic automatic exposure control."""

from __future__ import annotations

import re

import numpy as np

from promoc_core.promoc_exceptions import ConfigurationError, ImageProcessingError
from promoc_core.error_handling import handle_service_errors
from .base import CallbackBase


class ExposureHandler(CallbackBase):
    """Handler for exposure control."""

    _SUPPORTED_SENSOR_BITS = {8, 10, 12, 14, 16}

    @staticmethod
    def _format_exposure(exposure_us: float) -> str:
        exposure_ms = float(exposure_us) / 1000.0
        return f"{float(exposure_us):.1f} us ({exposure_ms:.3f} ms)"

    def _clamp_exposure_us(self, exposure_us: float) -> tuple[float, str]:
        """Clamp the requested exposure to the configured camera range if needed."""
        requested_exposure_us = float(exposure_us)
        min_exposure_us = max(0.0, self._param_float("camera.min_exposure_us", 0.0))
        max_exposure_us = max(0.0, self._param_float("camera.max_exposure_us", 0.0))

        if max_exposure_us > 0.0 and min_exposure_us > max_exposure_us:
            max_exposure_us = min_exposure_us

        clamped_exposure_us = requested_exposure_us
        if min_exposure_us > 0.0:
            clamped_exposure_us = max(clamped_exposure_us, min_exposure_us)
        if max_exposure_us > 0.0:
            clamped_exposure_us = min(clamped_exposure_us, max_exposure_us)

        if abs(clamped_exposure_us - requested_exposure_us) <= 1e-6:
            return requested_exposure_us, ""

        range_parts = []
        if min_exposure_us > 0.0:
            range_parts.append(f"min={self._format_exposure(min_exposure_us)}")
        if max_exposure_us > 0.0:
            range_parts.append(f"max={self._format_exposure(max_exposure_us)}")
        range_suffix = ", ".join(range_parts) if range_parts else "camera limits unavailable"

        message = (
            "Requested exposure "
            f"{self._format_exposure(requested_exposure_us)} is outside the allowed "
            f"camera range ({range_suffix}); clamped to "
            f"{self._format_exposure(clamped_exposure_us)}"
        )
        return clamped_exposure_us, message

    @handle_service_errors()
    def manual_set_exposure_callback(self, request, response):
        """Sets the manual exposure time.

        Args:
            request.exposure_time: Exposure time in microseconds
        """
        self._node.get_logger().info(
            f"Setting exposure time to {self._format_exposure(request.exposure_time)}"
        )

        if request.exposure_time <= 0:
            raise ConfigurationError(
                "Exposure time must be positive",
                details={"value": request.exposure_time},
            )

        target_exposure_us, clamp_message = self._clamp_exposure_us(
            request.exposure_time
        )
        if clamp_message:
            self._node.get_logger().warn(clamp_message)

        outcome = self._set_exposure_us(target_exposure_us)
        settle_frames = 2
        timeout_s = 1.0
        settle_frames = self._param_int(
            "exposure.settle_frames_after_set", settle_frames
        )
        timeout_s = self._param_float("exposure.frame_timeout_s", timeout_s)
        if settle_frames > 0:
            img, _ = self._wait_for_new_frames(
                settle_frames, timeout_per_frame=timeout_s
            )
            if img is None:
                self._node.get_logger().warn(
                    f"Exposure changed but timed out waiting for {settle_frames} new frames."
                )

        response.success = True
        applied_exposure_us = float(
            outcome.get("applied_exposure_us", request.exposure_time)
        )
        if outcome.get("used_fallback"):
            result_message = (
                "Requested exposure could not be applied; "
                "restored configured start exposure from camera profile to "
                f"{self._format_exposure(applied_exposure_us)}"
            )
        else:
            result_message = f"Exposure set to {self._format_exposure(applied_exposure_us)}"

        if clamp_message:
            response.status_message = f"{clamp_message}. {result_message}"
        else:
            response.status_message = result_message

        return response

    @classmethod
    def _native_max_value(cls, pixel_format: str, image: np.ndarray) -> float:
        """Resolve the sensor code maximum without confusing container and bit depth."""
        match = re.search(r"(?:mono|bayer[a-z]*)(8|10|12|14|16)", str(pixel_format), re.I)
        if match:
            bits = int(match.group(1))
            if bits in cls._SUPPORTED_SENSOR_BITS:
                native_max = (1 << bits) - 1
                if np.issubdtype(image.dtype, np.integer):
                    container_bits = int(np.iinfo(image.dtype).bits)
                    shift = container_bits - bits
                    if shift > 0:
                        values = image.reshape(-1)
                        nonzero = values[values != 0]
                        low_bit_mask = (1 << shift) - 1
                        looks_left_aligned = (
                            nonzero.size > 0
                            and (
                                int(np.max(nonzero)) > native_max
                                or np.all(
                                    np.bitwise_and(nonzero, low_bit_mask) == 0
                                )
                            )
                        )
                        if looks_left_aligned:
                            return float(native_max << shift)
                return float(native_max)
        if np.issubdtype(image.dtype, np.integer):
            return float(np.iinfo(image.dtype).max)
        return 1.0

    @staticmethod
    def _clip_roi(
        image: np.ndarray,
        roi: tuple[int, int, int, int] | None,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        """Return a valid image crop and its absolute origin."""
        if image is None or image.size == 0:
            raise ImageProcessingError("Auto exposure received an empty camera frame")
        if roi is None:
            return image, (0, 0)

        x, y, width, height = (int(value) for value in roi)
        image_height, image_width = image.shape[:2]
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(image_width, x + width)
        y1 = min(image_height, y + height)
        if width <= 0 or height <= 0 or x1 <= x0 or y1 <= y0:
            raise ConfigurationError(
                "Auto exposure ROI does not overlap the camera image",
                details={"roi": [x, y, width, height]},
            )
        return image[y0:y1, x0:x1], (x0, y0)

    @staticmethod
    def _analysis_values(
        image: np.ndarray,
        roi: tuple[int, int, int, int] | None,
        *,
        pixel_format: str,
    ) -> np.ndarray:
        """Extract intensity samples, using only native green sensels for Bayer RGGB."""
        cropped, (origin_x, origin_y) = ExposureHandler._clip_roi(image, roi)
        if cropped.ndim == 3:
            channel = 1 if cropped.shape[2] >= 2 else 0
            return cropped[:, :, channel].reshape(-1).astype(np.float64)

        if "bayer" in str(pixel_format).lower():
            row_even = origin_y % 2
            row_odd = 1 - row_even
            col_even = origin_x % 2
            col_odd = 1 - col_even
            green_1 = cropped[row_even::2, col_odd::2].reshape(-1)
            green_2 = cropped[row_odd::2, col_even::2].reshape(-1)
            if green_1.size and green_2.size:
                return np.concatenate((green_1, green_2)).astype(np.float64)

        return cropped.reshape(-1).astype(np.float64)

    @classmethod
    def _measure_level(
        cls,
        frames: list[np.ndarray],
        roi: tuple[int, int, int, int] | None,
        *,
        pixel_format: str,
        percentile: float,
        saturation_threshold_fraction: float,
    ) -> tuple[float, float, float]:
        """Return robust (level fraction, saturation fraction, native maximum)."""
        if not frames:
            raise ImageProcessingError("Auto exposure did not receive camera frames")
        native_max = cls._native_max_value(pixel_format, frames[0])
        levels = []
        saturated = []
        threshold = float(saturation_threshold_fraction) * native_max
        for frame in frames:
            values = cls._analysis_values(frame, roi, pixel_format=pixel_format)
            if values.size == 0:
                raise ImageProcessingError("Auto exposure ROI contains no usable pixels")
            levels.append(float(np.percentile(values, percentile)) / native_max)
            saturated.append(float(np.mean(values >= threshold)))
        return float(np.median(levels)), float(np.median(saturated)), native_max

    def _capture_state(self) -> tuple[str, float]:
        """Return active pixel format and exposure readback with configured fallbacks."""
        controller = getattr(self._node, "_format_controller", None)
        state = controller.read_capture_state() if controller is not None else None
        values = dict((state or {}).get("values", {}))
        pixel_format = str(
            values.get("pixel_format")
            or self._param_str("camera.default_pixel_format", "")
            or self._param_str("mtf.capture_pixel_format", "")
        )
        exposure_us = float(values.get("exposure_time") or self._current_exposure_us())
        return pixel_format, exposure_us

    def _collect_raw_frames(
        self,
        count: int,
        last_timestamp: int,
        timeout_s: float,
    ) -> tuple[list[np.ndarray], int]:
        """Collect distinct passthrough frames for one control iteration."""
        frames = []
        timestamp = int(last_timestamp)
        for _ in range(max(1, int(count))):
            image, next_timestamp, _encoding = self._wait_for_new_passthrough_image(
                timestamp,
                timeout=timeout_s,
            )
            if image is None or next_timestamp is None:
                raise ImageProcessingError(
                    "Auto exposure timed out waiting for a fresh raw camera frame"
                )
            frames.append(image)
            timestamp = int(next_timestamp)
        return frames, timestamp

    def _discard_raw_frames(
        self,
        count: int,
        last_timestamp: int,
        timeout_s: float,
    ) -> int:
        """Discard frames that may still carry the previous exposure."""
        timestamp = int(last_timestamp)
        for _ in range(max(0, int(count))):
            _image, next_timestamp, _encoding = self._wait_for_new_passthrough_image(
                timestamp,
                timeout=timeout_s,
            )
            if next_timestamp is None:
                raise ImageProcessingError(
                    "Auto exposure timed out while waiting for the new exposure to settle"
                )
            timestamp = int(next_timestamp)
        return timestamp

    @staticmethod
    def _request_roi(request) -> tuple[int, int, int, int] | None:
        width = int(getattr(request, "roi_width", 0) or 0)
        height = int(getattr(request, "roi_height", 0) or 0)
        if width <= 0 or height <= 0:
            return None
        return (
            int(getattr(request, "roi_x", 0) or 0),
            int(getattr(request, "roi_y", 0) or 0),
            width,
            height,
        )

    def _resolve_auto_exposure_options(self, request) -> dict[str, float | int]:
        """Resolve request overrides on top of conservative node defaults."""
        target = float(getattr(request, "target_level_fraction", 0.0) or 0.0)
        tolerance = float(getattr(request, "tolerance_fraction", 0.0) or 0.0)
        iterations = int(getattr(request, "max_iterations", 0) or 0)
        frames = int(getattr(request, "frames_per_iteration", 0) or 0)
        options = {
            "target": target if target > 0 else self._param_float(
                "auto_exposure.target_level_fraction", 0.75
            ),
            "tolerance": tolerance if tolerance > 0 else self._param_float(
                "auto_exposure.tolerance_fraction", 0.02
            ),
            "max_iterations": iterations if iterations > 0 else self._param_int(
                "auto_exposure.max_iterations", 10
            ),
            "frames_per_iteration": frames if frames > 0 else self._param_int(
                "auto_exposure.frames_per_iteration", 3
            ),
            "stable_iterations": self._param_int("auto_exposure.stable_iterations", 2),
            "percentile": self._param_float("auto_exposure.percentile", 95.0),
            "max_saturated_fraction": self._param_float(
                "auto_exposure.max_saturated_fraction", 0.001
            ),
            "saturation_threshold_fraction": self._param_float(
                "auto_exposure.saturation_threshold_fraction", 0.98
            ),
        }
        options["max_iterations"] = max(1, int(options["max_iterations"]))
        options["frames_per_iteration"] = max(
            1, int(options["frames_per_iteration"])
        )
        options["stable_iterations"] = max(1, int(options["stable_iterations"]))
        if not 0.05 <= float(options["target"]) <= 0.95:
            raise ConfigurationError("Auto exposure target must be between 0.05 and 0.95")
        if not 0.001 <= float(options["tolerance"]) <= 0.25:
            raise ConfigurationError("Auto exposure tolerance must be between 0.001 and 0.25")
        if not 50.0 <= float(options["percentile"]) <= 100.0:
            raise ConfigurationError("Auto exposure percentile must be between 50 and 100")
        if not 0.0 <= float(options["max_saturated_fraction"]) <= 1.0:
            raise ConfigurationError(
                "Auto exposure maximum saturated fraction must be between 0 and 1"
            )
        if not 0.5 <= float(options["saturation_threshold_fraction"]) <= 1.0:
            raise ConfigurationError(
                "Auto exposure saturation threshold must be between 0.5 and 1"
            )
        return options

    @handle_service_errors()
    def auto_exposure_callback(self, request, response):
        """Regulate exposure from fresh raw frames using a robust bright percentile."""
        options = self._resolve_auto_exposure_options(request)
        roi = self._request_roi(request)
        pixel_format, current_exposure_us = self._capture_state()
        if current_exposure_us <= 0:
            raise ConfigurationError("Current camera exposure is unavailable")

        min_exposure_us = max(1.0, self._param_float("camera.min_exposure_us", 1.0))
        max_exposure_us = self._param_float("camera.max_exposure_us", 0.0)
        if max_exposure_us <= 0:
            max_exposure_us = float("inf")
        settle_frames = self._param_int("auto_exposure.settle_frames_after_set", 2)
        timeout_s = self._param_float("exposure.frame_timeout_s", 1.0)
        last_timestamp = self._get_latest_image_timestamp_ns()
        stable_count = 0
        level = 0.0
        saturated = 0.0
        native_max = 0.0

        for iteration in range(1, int(options["max_iterations"]) + 1):
            frames, last_timestamp = self._collect_raw_frames(
                int(options["frames_per_iteration"]), last_timestamp, timeout_s
            )
            level, saturated, native_max = self._measure_level(
                frames,
                roi,
                pixel_format=pixel_format,
                percentile=float(options["percentile"]),
                saturation_threshold_fraction=float(
                    options["saturation_threshold_fraction"]
                ),
            )
            in_band = abs(level - float(options["target"])) <= float(
                options["tolerance"]
            )
            clipping_ok = saturated <= float(options["max_saturated_fraction"])
            stable_count = stable_count + 1 if in_band and clipping_ok else 0
            self._node.get_logger().info(
                f"Auto exposure {iteration}/{int(options['max_iterations'])}: "
                f"exposure={current_exposure_us:.1f}us, "
                f"P{float(options['percentile']):g}={level:.3f}, "
                f"saturated={saturated:.5f}"
            )
            if stable_count >= int(options["stable_iterations"]):
                response.success = True
                response.status_message = (
                    f"Auto exposure converged at {current_exposure_us:.1f} us; "
                    f"P{float(options['percentile']):g}={level:.3f}, "
                    f"saturated={saturated:.5f}"
                )
                response.exposure_time = float(current_exposure_us)
                response.iterations = int(iteration)
                response.measured_level_fraction = float(level)
                response.saturated_fraction = float(saturated)
                response.native_max_value = float(native_max)
                return response

            if in_band and clipping_ok:
                # Confirm an apparently good exposure with another independent
                # frame set instead of introducing an unnecessary tiny write.
                continue

            ratio = float(options["target"]) / max(level, 1e-6)
            ratio = max(0.5, min(2.0, ratio)) ** 0.7
            if not clipping_ok:
                ratio = min(ratio, 0.8)
            requested_exposure_us = max(
                min_exposure_us,
                min(max_exposure_us, current_exposure_us * ratio),
            )
            if abs(requested_exposure_us - current_exposure_us) < 0.5:
                break
            self._node.get_logger().info(
                f"Auto exposure adjustment: {current_exposure_us:.1f}us -> "
                f"{requested_exposure_us:.1f}us"
            )
            outcome = self._set_exposure_us(requested_exposure_us)
            current_exposure_us = float(
                outcome.get("applied_exposure_us", requested_exposure_us)
            )
            last_timestamp = self._discard_raw_frames(
                settle_frames, last_timestamp, timeout_s
            )

        response.success = False
        response.status_message = (
            f"Auto exposure did not converge; exposure={current_exposure_us:.1f} us, "
            f"P{float(options['percentile']):g}={level:.3f}, "
            f"saturated={saturated:.5f}"
        )
        response.exposure_time = float(current_exposure_us)
        response.iterations = int(iteration)
        response.measured_level_fraction = float(level)
        response.saturated_fraction = float(saturated)
        response.native_max_value = float(native_max)
        return response
