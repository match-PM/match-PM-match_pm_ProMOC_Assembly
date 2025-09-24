"""
Interface class to handle communication with the camera_aravis2 driver.
"""

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
                    self.SetExposureTime, '/assembly_camera/set_exposure_time')
            except ImportError:
                self._node.get_logger().error(
                    "Could not import driver interfaces from 'pm_genicam_controller_interfaces'."
                    " Driver control will be disabled."
                )
        else:
            self._node.get_logger().info("Running in SIMULATOR mode. Aravis Interface is disabled.")

    async def set_exposure(self, exposure_time):
        """
        Calls the driver service to set the exposure time.

        :param exposure_time: The desired exposure time.
        :return: A tuple (bool: success, str: message).
        """
        if self._client is None:
            return False, "Driver client is not available."
        
        if not self._client.service_is_ready():
            return False, "Driver service is not ready."

        request = self.SetExposureTime.Request()
        request.exposure_time = exposure_time
        
        try:
            future = self._client.call_async(request)
            response = await future
            return response.success, response.message
        except Exception as e:
            self._node.get_logger().error(f"Exception while calling set_exposure service: {e}")
            return False, str(e)
