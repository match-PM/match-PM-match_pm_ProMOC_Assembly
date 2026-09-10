"""Manual and deterministic automatic exposure control."""

from __future__ import annotations

import numpy as np

from promoc_core.promoc_exceptions import ConfigurationError, ImageProcessingError
from promoc_core.error_handling import handle_service_errors
from ..intensity import (
    aggregate_intensity,
    analysis_values,
    clip_roi,
    exposure_ratio,
    measure_intensity,
    native_max_value,
)
from .base import CallbackBase


class ExposureHandler(CallbackBase):
    """Handler for exposure control."""

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
        return native_max_value(pixel_format, image)

    @staticmethod
    def _clip_roi(
        image: np.ndarray,
        roi: tuple[int, int, int, int] | None,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        """Return a valid image crop and its absolute origin."""
        try:
            return clip_roi(image, roi)
        except ValueError as exc:
            if image is None or getattr(image, "size", 0) == 0:
                raise ImageProcessingError(
                    "Auto exposure received an empty camera frame"
                ) from exc
            raise ConfigurationError(
                "Auto exposure ROI does not overlap the camera image",
                details={"roi": list(roi or ())},
            ) from exc

    @staticmethod
    def _analysis_values(
        image: np.ndarray,
        roi: tuple[int, int, int, int] | None,
        *,
        pixel_format: str,
    ) -> np.ndarray:
        """Extract intensity samples, using only native green sensels for Bayer RGGB."""
        try:
            return analysis_values(image, roi, pixel_format=pixel_format)
        except ValueError as exc:
            raise ImageProcessingError(str(exc)) from exc

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
        diagnostics = cls._measure_diagnostics(
            frames,
            roi,
            pixel_format=pixel_format,
            saturation_threshold_fraction=saturation_threshold_fraction,
        )
        # Preserve the private compatibility contract used by existing tests.
        level_key = "white_level_norm" if percentile == 95.0 else "p95_norm"
        return (
            float(diagnostics[level_key]),
            float(diagnostics["saturation_fraction"]),
            float(diagnostics["native_max"]),
        )

    @staticmethod
    def _measure_diagnostics(
        frames: list[np.ndarray],
        roi: tuple[int, int, int, int] | None,
        *,
        pixel_format: str,
        saturation_threshold_fraction: float,
        clipping_level_fraction: float = 0.95,
        max_saturated_fraction: float = 0.001,
    ) -> dict[str, object]:
        """Return median-combined linear intensity and clipping diagnostics."""
        if not frames:
            raise ImageProcessingError("Auto exposure did not receive camera frames")
        try:
            return aggregate_intensity(
                [
                    measure_intensity(
                        frame,
                        roi,
                        pixel_format=pixel_format,
                        saturation_threshold_fraction=saturation_threshold_fraction,
                        clipping_level_fraction=clipping_level_fraction,
                        max_saturated_fraction=max_saturated_fraction,
                    )
                    for frame in frames
                ]
            )
        except ValueError as exc:
            raise ImageProcessingError(str(exc)) from exc

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
                "auto_exposure.target_level_fraction", 0.70
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
            "clipping_level_fraction": self._param_float(
                "auto_exposure.clipping_level_fraction", 0.95
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
        if not 0.5 <= float(options["clipping_level_fraction"]) <= 1.0:
            raise ConfigurationError(
                "Auto exposure clipping level must be between 0.5 and 1"
            )
        return options

    @staticmethod
    def _populate_auto_response(response, diagnostics, exposure_us, iterations, success):
        """Populate legacy and additive auto-exposure response fields."""
        response.success = bool(success)
        response.exposure_time = float(exposure_us)
        response.iterations = int(iterations)
        response.measured_level_fraction = float(diagnostics["white_level_norm"])
        response.saturated_fraction = float(diagnostics["saturation_fraction"])
        response.native_max_value = float(diagnostics["native_max"])
        response.white_level = float(diagnostics["white_level"])
        response.white_level_normalized = float(diagnostics["white_level_norm"])
        response.black_level = float(diagnostics["black_level"])
        response.black_level_normalized = float(diagnostics["black_level_norm"])
        response.p95 = float(diagnostics["p95"])
        response.p95_normalized = float(diagnostics["p95_norm"])
        response.p99_9 = float(diagnostics["p99_9"])
        response.p99_9_normalized = float(diagnostics["p99_9_norm"])
        response.saturation_fraction = float(diagnostics["saturation_fraction"])
        response.intensity_method = str(diagnostics["intensity_method"])
        response.clipping_detected = bool(diagnostics["clipping_detected"])

    @handle_service_errors()
    def auto_exposure_callback(self, request, response):
        """Regulate exposure from fresh raw frames using robust black/white plateaus."""
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
        diagnostics = {
            "white_level": 0.0,
            "white_level_norm": 0.0,
            "black_level": 0.0,
            "black_level_norm": 0.0,
            "p95": 0.0,
            "p95_norm": 0.0,
            "p99_9": 0.0,
            "p99_9_norm": 0.0,
            "saturation_fraction": 0.0,
            "native_max": 0.0,
            "intensity_method": "p95_fallback",
            "clipping_detected": False,
        }

        for iteration in range(1, int(options["max_iterations"]) + 1):
            frames, last_timestamp = self._collect_raw_frames(
                int(options["frames_per_iteration"]), last_timestamp, timeout_s
            )
            diagnostics = self._measure_diagnostics(
                frames,
                roi,
                pixel_format=pixel_format,
                saturation_threshold_fraction=float(
                    options["saturation_threshold_fraction"]
                ),
                clipping_level_fraction=float(options["clipping_level_fraction"]),
                max_saturated_fraction=float(options["max_saturated_fraction"]),
            )
            level = float(diagnostics["white_level_norm"])
            saturated = float(diagnostics["saturation_fraction"])
            in_band = abs(level - float(options["target"])) <= float(
                options["tolerance"]
            )
            clipping_ok = not bool(diagnostics["clipping_detected"])
            stable_count = stable_count + 1 if in_band and clipping_ok else 0
            self._node.get_logger().info(
                f"Auto exposure {iteration}/{int(options['max_iterations'])}: "
                f"exposure={current_exposure_us:.1f}us, "
                f"white={level:.3f} ({diagnostics['intensity_method']}), "
                f"P99.9={float(diagnostics['p99_9_norm']):.3f}, "
                f"saturated={saturated:.5f}"
            )
            if stable_count >= int(options["stable_iterations"]):
                response.success = True
                response.status_message = (
                    f"Auto exposure converged at {current_exposure_us:.1f} us; "
                    f"white={level:.3f}, "
                    f"saturated={saturated:.5f}"
                )
                self._populate_auto_response(
                    response, diagnostics, current_exposure_us, iteration, True
                )
                return response

            if in_band and clipping_ok:
                # Confirm an apparently good exposure with another independent
                # frame set instead of introducing an unnecessary tiny write.
                continue

            ratio = exposure_ratio(diagnostics, float(options["target"]))
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
            f"white={float(diagnostics['white_level_norm']):.3f}, "
            f"saturated={saturated:.5f}"
        )
        self._populate_auto_response(
            response, diagnostics, current_exposure_us, iteration, False
        )
        return response
