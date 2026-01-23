"""Exposure callbacks for camera control."""

from promoc_core.promoc_exceptions import HardwareError, ConfigurationError
from .base import CallbackBase


class ExposureCallbacks(CallbackBase):
    """Callbacks for exposure control."""

    def manual_set_exposure_callback(self, request, response):
        """Sets the manual exposure time.
        
        Args:
            request.exposure_time: Exposure time in microseconds
        """
        self._node.get_logger().info(
            f'Setting exposure time to {request.exposure_time} µs')

        try:
            if request.exposure_time <= 0:
                raise ConfigurationError(
                    'Exposure time must be positive',
                    details={'value': request.exposure_time})

            self._driver.set_exposure(request.exposure_time)
            
            response.success = True
            response.message = f'Exposure set to {request.exposure_time} µs'

        except ConfigurationError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().warn(response.message)

        except HardwareError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().error(response.message)

        except Exception as e:
            response.success = False
            response.message = f'ERROR: Failed to set exposure: {str(e)}'
            self._node.get_logger().error(response.message)

        return response
