"""
Contains the service callback logic for the CameraNode.
"""

import cv2
import rclpy
from promoc_assembly_interfaces.srv import MoveAbsolute, JogAxis
import time

class CameraServiceCallbacks:
    """Holds all service callback methods for the main camera node."""

    def __init__(self, node, aravis_interface):
        """
        Initializes the callbacks.
        :param node: The parent ROS2 node.
        :param aravis_interface: The CameraAravisInterface instance.
        """
        self._node = node
        self._interface = aravis_interface

    def _calculate_sharpness(self, image):
        """Calculates the sharpness of an image using the variance of the Laplacian."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return laplacian.var()

    def select_roi_callback(self, request, response):
        """Callback to manually select a ROI and trigger MTF calculation."""
        self._node.get_logger().info("ROI selection service called.")

        if self._node.latest_image_msg is None:
            response.success = False
            response.message = "No image received yet."
            self._node.get_logger().error(response.message)
            return response

        try:
            cv_image = self._node.bridge.imgmsg_to_cv2(self._node.latest_image_msg, "bgr8")
            roi = cv2.selectROI("Select ROI", cv_image, fromCenter=False, showCrosshair=True)
            cv2.destroyWindow("Select ROI")

            if roi == (0, 0, 0, 0):
                response.success = False
                response.message = "ROI selection cancelled."
                self._node.get_logger().warn(response.message)
                return response

            self._node.get_logger().info(f"Selected ROI (x, y, w, h): {roi}")
            x, y, w, h = roi
            roi_image = cv_image[y:y+h, x:x+w]

            self._node.get_logger().info("Calculating MTF from selected ROI...")
            mtf_results = self._node.image_processor.calculate_mtf_from_roi(roi_image)

            if mtf_results:
                output_filename = self._node.get_parameter('mtf_csv_path').get_parameter_value().string_value
                if not output_filename:
                    response.success = False
                    response.message = "MTF calculated, but no 'mtf_csv_path' was set. Results not saved."
                    self._node.get_logger().warn(response.message)
                    return response

                self._node.image_processor.export_to_csv(mtf_results, output_filename)
                response.success = True
                response.message = f"MTF calculation successful. Results saved to {output_filename}"
                self._node.get_logger().info(response.message)
            else:
                response.success = False
                response.message = "MTF calculation failed. Could not determine ESF or edge was not found."
                self._node.get_logger().error(response.message)

        except Exception as e:
            response.success = False
            response.message = f"An exception occurred: {e}"
            self._node.get_logger().error(response.message, exc_info=True)

        return response

    def autofocus_callback(self, request, response):
        """Callback for the autofocus service."""
        self._node.get_logger().info(
            f"Autofocus service called with range {request.start_position} to {request.end_position} with step {request.step_size}")

        move_abs_client = self._node.create_client(MoveAbsolute, '/lts300_node/move_absolute')
        jog_client = self._node.create_client(JogAxis, '/lts300_node/jog_axis')

        if not move_abs_client.wait_for_service(timeout_sec=1.0) or not jog_client.wait_for_service(timeout_sec=1.0):
            response.success = False
            response.message = "Linear axis services not available."
            self._node.get_logger().error(response.message)
            return response

        sharpness_values = []
        positions = []

        # Move to start position
        move_req = MoveAbsolute.Request()
        move_req.position = request.start_position
        future = move_abs_client.call_async(move_req)
        rclpy.spin_until_future_complete(self._node, future)
        if future.result() is None or not future.result().success:
            response.success = False
            response.message = "Failed to move to start position."
            self._node.get_logger().error(response.message)
            return response

        current_pos = request.start_position
        while current_pos <= request.end_position:
            positions.append(current_pos)
            
            # Capture image and calculate sharpness
            if self._node.latest_image_msg is None:
                time.sleep(0.5) # Wait for image
            if self._node.latest_image_msg is None:
                self._node.get_logger().warn(f"No image at position {current_pos}")
                sharpness_values.append(0)
            else:
                cv_image = self._node.bridge.imgmsg_to_cv2(self._node.latest_image_msg, "bgr8")
                sharpness = self._calculate_sharpness(cv_image)
                sharpness_values.append(sharpness)
                self._node.get_logger().info(f"Position: {current_pos}, Sharpness: {sharpness}")

            # Move to next position
            jog_req = JogAxis.Request()
            jog_req.step_size = request.step_size
            future = jog_client.call_async(jog_req)
            rclpy.spin_until_future_complete(self._node, future)
            if future.result() is None or not future.result().success:
                self._node.get_logger().warn("Failed to jog axis.")
            
            current_pos += request.step_size

        if not sharpness_values:
            response.success = False
            response.message = "No sharpness values were calculated."
            self._node.get_logger().error(response.message)
            return response

        # Find best position
        max_sharpness = max(sharpness_values)
        best_position = positions[sharpness_values.index(max_sharpness)]
        
        self._node.get_logger().info(f"Best position found at {best_position} with sharpness {max_sharpness}")

        # Move to best position
        move_req.position = best_position
        future = move_abs_client.call_async(move_req)
        rclpy.spin_until_future_complete(self._node, future)
        if future.result() is None or not future.result().success:
            response.success = False
            response.message = f"Failed to move to best position {best_position}."
            self._node.get_logger().error(response.message)
            return response

        response.success = True
        response.message = f"Autofocus successful. Best position found at {best_position}"
        response.best_position = best_position
        return response

    async def manual_set_exposure_callback(self, request, response):
        """Callback for the manual exposure setting service."""
        self._node.get_logger().info(f"Received manual request to set exposure to {request.exposure_time}")
        
        success, message = await self._interface.set_exposure(request.exposure_time)
        
        response.success = success
        response.message = message
        
        if not success:
            self._node.get_logger().warn(f"Failed to set exposure: {message}")
            
        return response