"""Exposure handler for camera control."""

from promoc_core.promoc_exceptions import ConfigurationError
from promoc_core.error_handling import handle_service_errors
from .base import CallbackBase


class ExposureHandler(CallbackBase):
    """Handler for exposure control."""

    @handle_service_errors()
    def manual_set_exposure_callback(self, request, response):
        """Sets the manual exposure time.
        
        Args:
            request.exposure_time: Exposure time in microseconds
        """
        self._node.get_logger().info(
            f'Setting exposure time to {request.exposure_time} µs')

        if request.exposure_time <= 0:
            raise ConfigurationError(
                'Exposure time must be positive',
                details={'value': request.exposure_time})

        self._set_exposure_us(request.exposure_time)
        settle_frames = 2
        timeout_s = 1.0
        settle_frames = self._param_int('exposure.settle_frames_after_set', settle_frames)
        timeout_s = self._param_float('exposure.frame_timeout_s', timeout_s)
        if settle_frames > 0:
            img, _ = self._wait_for_new_frames(settle_frames, timeout_per_frame=timeout_s)
            if img is None:
                self._node.get_logger().warn(
                    f'Exposure changed but timed out waiting for {settle_frames} new frames.'
                )
        
        response.success = True
        response.status_message = f'Exposure set to {request.exposure_time} µs'

        return response

