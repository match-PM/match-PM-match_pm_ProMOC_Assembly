"""Exposure handler for camera control."""

from promoc_core.promoc_exceptions import ConfigurationError
from promoc_core.error_handling import handle_service_errors
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
