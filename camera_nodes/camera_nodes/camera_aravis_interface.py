"""
Interface class to handle communication with the camera_aravis2 driver.
"""
from promoc_core.promoc_exceptions import HardwareError, CommunicationError, DriverNotAvailableError

class CameraAravisInterface:
    """A wrapper for ROS2 services provided by the camera_aravis2 driver."""

    def __init__(self, node):
        """
        Initializes the interface.
        :param node: The parent ROS2 node.
        """
        self._node = node
        self._client = None
        self.SetExposureTime = None

        if not self._node.use_simulator:
            self._node.get_logger().info("Running in REAL mode. Initializing Aravis Interface.")
            try:
                from pm_genicam_controller_interfaces.srv import SetExposureTime
                self.SetExposureTime = SetExposureTime
                
                self._client = self._node.create_client(
                    self.SetExposureTime, '/promoc/assembly_camera_controller/set_exposure_time')
            except ImportError:
                # We raise an exception here to signal that the driver is not available
                # The calling node should catch this if it can operate without the camera
                raise DriverNotAvailableError(
                    message="Could not import driver interfaces from 'pm_genicam_controller_interfaces'.",
                    details={'driver': 'camera_aravis2'}
                )
        else:
            self._node.get_logger().info("Running in SIMULATOR mode. Aravis Interface is disabled.")

    async def set_exposure(self, exposure_time):
        """
        Calls the driver service to set the exposure time.

        :param exposure_time: The desired exposure time.
        :raises CommunicationError: If the service is not available or ready.
        :raises HardwareError: If the service call fails.
        :return: True if successful (legacy return, but exceptions are preferred).
        """
        if self._client is None:
            raise CommunicationError("Driver client is not available.")
        
        if not self._client.service_is_ready():
            raise CommunicationError("Driver service is not ready.")

        request = self.SetExposureTime.Request()
        request.exposure_time = exposure_time
        
        try:
            future = self._client.call_async(request)
            response = await future
            if not response.success:
                raise HardwareError(
                    message=f"Failed to set exposure time: {response.error}",
                    details={'exposure_time': exposure_time}
                )
            return True
        except Exception as e:
            if isinstance(e, (HardwareError, CommunicationError)):
                raise e
            raise HardwareError(f"Exception while calling set_exposure service: {e}")
