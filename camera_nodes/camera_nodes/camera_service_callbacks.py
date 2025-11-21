"""
Contains the service callback logic for the CameraNode.
"""

import cv2
import rclpy
from promoc_assembly_interfaces.srv import MoveAbsolute, JogAxis
import time
import sys
from promoc_core.promoc_exceptions import (
    ConnectionError,
    InvalidParameterError,
    ServiceCallFailedError,
    ImageProcessingError,
    ConfigurationError,
    HardwareError
)

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

        try:
            # Check if image is available
            if self._node.latest_image_msg is None:
                raise ImageProcessingError(
                    "No image received yet",
                    details={'context': 'ROI selection requires active camera feed'}
                )

            # Convert ROS image to OpenCV format
            try:
                cv_image = self._node.bridge.imgmsg_to_cv2(self._node.latest_image_msg, "bgr8")
            except Exception as e:
                raise ImageProcessingError(
                    f"Failed to convert ROS image to OpenCV format: {str(e)}",
                    details={'encoding': 'bgr8', 'error': str(e)}
                )

            # Select ROI
            roi = cv2.selectROI("Select ROI", cv_image, fromCenter=False, showCrosshair=True)
            cv2.destroyWindow("Select ROI")

            if roi == (0, 0, 0, 0):
                self._node.get_logger().info("ROI selection cancelled by user.")
                response.success = False
                response.message = "ROI selection cancelled."
                return response

            # Extract ROI from image
            x, y, w, h = roi
            self._node.get_logger().info(f"Selected ROI (x, y, w, h): {roi}")
            
            if w <= 0 or h <= 0:
                raise ParameterValidationError(
                    "Invalid ROI dimensions",
                    details={'roi': roi, 'width': w, 'height': h, 'constraint': 'width and height must be positive'}
                )
            
            roi_image = cv_image[y:y+h, x:x+w]

            # Calculate MTF
            self._node.get_logger().info("Calculating MTF from selected ROI...")
            mtf_results = self._node.image_processor.calculate_mtf_from_roi(roi_image)

            if not mtf_results:
                raise ImageProcessingError(
                    "MTF calculation failed - could not determine ESF or edge was not found",
                    details={'roi': roi, 'roi_size': (w, h)}
                )

            # Get output path and validate
            output_filename = self._node.get_parameter('mtf_csv_path').get_parameter_value().string_value
            if not output_filename:
                raise ConfigurationError(
                    "MTF CSV output path not configured",
                    details={'parameter': 'mtf_csv_path', 'value': output_filename}
                )

            # Export results
            self._node.image_processor.export_to_csv(mtf_results, output_filename)
            
            response.success = True
            response.message = f"MTF calculation successful. Results saved to {output_filename}"
            self._node.get_logger().info(response.message)
            
        except ImageProcessingError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(f"Image processing error details: {e.details}")
            
        except ParameterValidationError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(f"Parameter validation details: {e.details}")
            
        except ConfigurationError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(f"Configuration error details: {e.details}")
            
        except Exception as e:
            response.success = False
            response.message = f"❌ ROI selection failed: {str(e)}"
            self._node.get_logger().error(response.message, exc_info=True)

        return response

    def autofocus_callback(self, request, response):
        """Callback for the autofocus service."""
        self._node.get_logger().info(
            f"Autofocus service called with range {request.start_position} to {request.end_position} with step {request.step_size}")

        try:
            # Validate parameters
            if request.start_position >= request.end_position:
                raise InvalidParameterError(
                    "Start position must be less than end position",
                    details={
                        'start_position': request.start_position,
                        'end_position': request.end_position,
                        'constraint': 'start < end'
                    }
                )
            
            if request.step_size <= 0:
                raise InvalidParameterError(
                    "Step size must be positive",
                    details={
                        'parameter': 'step_size',
                        'value': request.step_size,
                        'constraint': 'positive'
                    }
                )

            # Create service clients
            move_abs_client = self._node.create_client(MoveAbsolute, '/lts300_node/move_absolute')
            jog_client = self._node.create_client(JogAxis, '/lts300_node/jog_axis')

            if not move_abs_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    "Linear axis move_absolute service not available",
                    details={'service': '/lts300_node/move_absolute', 'timeout': 1.0}
                )
            
            if not jog_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    "Linear axis jog_axis service not available",
                    details={'service': '/lts300_node/jog_axis', 'timeout': 1.0}
                )

            sharpness_values = []
            positions = []

            # Move to start position
            move_req = MoveAbsolute.Request()
            move_req.position = request.start_position
            future = move_abs_client.call_async(move_req)
            rclpy.spin_until_future_complete(self._node, future)
            
            if future.result() is None:
                raise ServiceCallFailedError(
                    "Move to start position - no response received",
                    details={'target_position': request.start_position}
                )
            
            if not future.result().success:
                raise ServiceCallFailedError(
                    f"Failed to move to start position: {future.result().status_message}",
                    details={
                        'target_position': request.start_position,
                        'service_response': future.result().status_message
                    }
                )

            # Scan through positions
            current_pos = request.start_position
            while current_pos <= request.end_position:
                positions.append(current_pos)
                
                # Capture image and calculate sharpness
                if self._node.latest_image_msg is None:
                    time.sleep(0.5)  # Wait for image
                
                if self._node.latest_image_msg is None:
                    self._node.get_logger().warn(f"No image at position {current_pos}")
                    sharpness_values.append(0)
                else:
                    try:
                        cv_image = self._node.bridge.imgmsg_to_cv2(self._node.latest_image_msg, "bgr8")
                        sharpness = self._calculate_sharpness(cv_image)
                        sharpness_values.append(sharpness)
                        self._node.get_logger().debug(f"Position: {current_pos:.2f}mm, Sharpness: {sharpness:.2f}")
                    except Exception as e:
                        self._node.get_logger().warn(f"Failed to process image at position {current_pos}: {str(e)}")
                        sharpness_values.append(0)

                # Move to next position (unless we're at the end)
                if current_pos + request.step_size <= request.end_position:
                    jog_req = JogAxis.Request()
                    jog_req.step_size = request.step_size
                    future = jog_client.call_async(jog_req)
                    rclpy.spin_until_future_complete(self._node, future)
                    
                    if future.result() is None or not future.result().success:
                        self._node.get_logger().warn(f"Failed to jog axis at position {current_pos}")
                
                current_pos += request.step_size

            # Validate results
            if not sharpness_values or all(s == 0 for s in sharpness_values):
                raise ImageProcessingError(
                    "No valid sharpness values calculated during autofocus scan",
                    details={
                        'positions_scanned': len(positions),
                        'valid_measurements': sum(1 for s in sharpness_values if s > 0)
                    }
                )

            # Find best position
            max_sharpness = max(sharpness_values)
            best_position = positions[sharpness_values.index(max_sharpness)]
            
            self._node.get_logger().info(f"📷 Best focus position: {best_position:.2f}mm (sharpness: {max_sharpness:.2f})")

            # Move to best position
            move_req.position = best_position
            future = move_abs_client.call_async(move_req)
            rclpy.spin_until_future_complete(self._node, future)
            
            if future.result() is None:
                raise ServiceCallFailedError(
                    "Move to best position - no response received",
                    details={'target_position': best_position}
                )
            
            if not future.result().success:
                raise ServiceCallFailedError(
                    f"Failed to move to best position: {future.result().status_message}",
                    details={
                        'target_position': best_position,
                        'max_sharpness': max_sharpness,
                        'service_response': future.result().status_message
                    }
                )

            response.success = True
            response.message = f"Autofocus successful. Best position: {best_position:.2f}mm (sharpness: {max_sharpness:.2f})"
            response.best_position = best_position
            
        except InvalidParameterError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(f"Parameter validation details: {e.details}")
            
        except ServiceCallFailedError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().error(response.message)
            self._node.get_logger().debug(f"Service call error details: {e.details}")
            
        except ImageProcessingError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(f"Image processing error details: {e.details}")
            
        except Exception as e:
            response.success = False
            response.message = f"❌ Autofocus failed: {str(e)}"
            self._node.get_logger().error(response.message, exc_info=True)
            
        return response

    async def manual_set_exposure_callback(self, request, response):
        """Callback for the manual exposure setting service."""
        self._node.get_logger().info(f"Received manual request to set exposure to {request.exposure_time}µs")
        
        try:
            # Validate exposure time
            if request.exposure_time <= 0:
                raise InvalidParameterError(
                    "Exposure time must be positive",
                    details={
                        'parameter': 'exposure_time',
                        'value': request.exposure_time,
                        'constraint': 'positive',
                        'unit': 'microseconds'
                    }
                )
            
            # Set exposure
            success, message = await self._interface.set_exposure(request.exposure_time)
            
            if not success:
                raise HardwareError(
                    f"Failed to set exposure: {message}",
                    details={
                        'requested_exposure': request.exposure_time,
                        'hardware_response': message
                    }
                )
            
            response.success = True
            response.message = f"Exposure set to {request.exposure_time}µs successfully"
            self._node.get_logger().info(response.message)
            
        except InvalidParameterError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(f"Parameter validation details: {e.details}")
            
        except HardwareError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().error(response.message)
            self._node.get_logger().debug(f"Hardware error details: {e.details}")
            
        except Exception as e:
            response.success = False
            response.message = f"❌ Setting exposure failed: {str(e)}"
            self._node.get_logger().error(response.message, exc_info=True)
            
        return response