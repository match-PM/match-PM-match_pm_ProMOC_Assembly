"""
Service callbacks for camera node - business logic for image processing.

Implements ROS2 service callbacks for:
- Autofocus: Hybrid algorithm with coarse search and multi-level refinement
- MTF measurement: ISO 12233 slanted edge method
- ROI selection: Interactive selection with MTF calculation
- Exposure control: Manual setting of camera exposure time

Architecture:
Service Requests → CameraServiceCallbacks → promoc_core algorithms → ROS2 Services

Services:
- select_roi_callback: Interactive ROI selection and MTF measurement
- autofocus_callback: Automatic focus optimization with Z-axis control
- measure_mtf_callback: ISO 12233 MTF measurement from image
- manual_set_exposure_callback: Set camera exposure time

Autofocus Algorithm:
Hybrid multi-level refinement approach:
1. Coarse search: Scan full range with large steps, find approximate maximum
2. Refinement (Phase 2+): Narrow search range, reduce step size, repeat

Sharpness Metric: Tenengrad (robust for single images)

Exception Handling:
- ImageProcessingError: Image processing failures
- InvalidParameterError: Invalid input values  
- ConfigurationError: Missing configuration
- ServiceCallFailedError: Z-axis service unavailable
"""

import csv
from datetime import datetime
from pathlib import Path
import time

import cv2
from promoc_assembly_interfaces.srv import (
    GetOperationStatus,
    GetVelocityParameters,
    JogAxis,
    MoveAbsolute,
    SetVelocityParameters,
)
from promoc_core.algorithms import (
    AutofocusConfig,
    HybridAutofocus,
    MTFAnalyzer,
    MTFConfig,
    tenengrad,
)
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    HardwareError,
    ImageProcessingError,
    InvalidParameterError,
    ParameterValidationError,
    ServiceCallFailedError,
)


class CameraServiceCallbacks:
    """
    Business logic for all camera services.

    Implements callbacks for autofocus, MTF measurement, and ROI selection.
    Decoupled from ROS2 - uses promoc_core for algorithms.

    Attributes:
        _node: Parent ROS2 node
        _driver: Camera driver (abstract)
        _mtf_analyzer: MTF analyzer instance (lazy init)

    Main Methods:
        select_roi_callback(): Interactive ROI selection + MTF measurement
        autofocus_callback(): Automatic focus optimization
        measure_mtf_callback(): ISO 12233 MTF measurement
    """

    def __init__(self, node, camera_driver):
        """Initialize service callbacks.

        Args:
            node: Parent ROS2 node
            camera_driver: Camera driver instance
        """
        self._node = node
        self._driver = camera_driver

        # MTF analyzer created on first use
        self._mtf_analyzer = None

    # SHARPNESS CALCULATION

    def _calculate_sharpness(self, image, metric: str = 'tenengrad'):
        """
        Calculates the sharpness of an image using the Tenengrad metric.

        This method centralizes sharpness evaluation, ensuring consistency.

        Args:
            image: Input image (BGR or grayscale).
            metric: Ignored. Kept for backward compatibility.
                    Only 'tenengrad' is used.

        Returns:
            float: Sharpness score (higher is sharper).

        Example:
            >>> sharpness = self._calculate_sharpness(cv_image)
            >>> print(f"Sharpness: {sharpness:.2f}")
        """
        if metric != 'tenengrad':
            # Warn if an unsupported metric is requested, but still use tenengrad.
            # This prevents failures with older clients that might still use 'variance'.
            self._node.get_logger().warn(
                f"Unsupported sharpness metric '{metric}', using 'tenengrad' instead")
        return tenengrad(image)

    # CSV EXPORT

    def _export_autofocus_csv(
        self,
        measurements: list[dict],
        best_position: float,
        best_score: float
    ) -> str | None:
        """
        Export autofocus measurements to a CSV file.

        Args:
            measurements: List of measurement dictionaries
            best_position: Best focus position in mm
            best_score: Best tenengrad score

        Returns:
            Path to the created CSV file, or None on error
        """
        if not measurements:
            return None

        try:
            # Create output directory in home folder
            output_dir = Path.home() / 'autofocus_logs'
            output_dir.mkdir(exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f'autofocus_{timestamp}.csv'
            csv_path = output_dir / csv_filename

            # Write CSV file
            fieldnames = [
                'timestamp_s', 'z_position_mm', 'tenengrad_score',
                'best_score', 'phase', 'step_mm', 'range_mm'
            ]

            with open(csv_path, 'w', newline='') as csvfile:
                # Write header comment with summary
                csvfile.write(f'# Autofocus Results - {datetime.now().isoformat()}\n')
                csvfile.write(f'# Best Position: {best_position:.4f} mm\n')
                csvfile.write(f'# Best Tenengrad Score: {best_score:.2f}\n')
                csvfile.write(f'# Total Measurements: {len(measurements)}\n')
                csvfile.write('#\n')

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(measurements)

            return str(csv_path)

        except Exception as e:
            self._node.get_logger().warn(f'Failed to export autofocus CSV: {e}')
            return None

    # ROI SELECTION

    def select_roi_callback(self, request, response):
        """
        Select ROI interactively and calculate MTF.

        Steps:
        1. Get latest camera image
        2. Open OpenCV window for ROI selection
        3. User selects rectangle around slanted edge
        4. Calculate MTF from ROI
        5. Export results to CSV
        """
        self._node.get_logger().info('ROI selection service called.')

        try:
            # Get latest image
            if self._node.latest_image_msg is None:
                raise ImageProcessingError(
                    'No image received yet',
                    details={
                        'context': 'ROI selection requires active camera feed'}
                )

            # Convert ROS image to OpenCV
            try:
                cv_image = self._node.bridge.imgmsg_to_cv2(
                    self._node.latest_image_msg, 'bgr8')
            except Exception as e:
                raise ImageProcessingError(
                    f'Failed to convert ROS image to OpenCV format: {str(e)}',
                    details={'encoding': 'bgr8', 'error': str(e)}
                )

            # User selects ROI
            roi = cv2.selectROI('Select ROI', cv_image,
                                fromCenter=False, showCrosshair=True)
            cv2.destroyWindow('Select ROI')

            if roi == (0, 0, 0, 0):
                self._node.get_logger().info('ROI selection cancelled by user.')
                response.success = False
                response.message = 'ROI selection cancelled.'
                return response

            # Extract and validate ROI
            x, y, w, h = roi
            self._node.get_logger().info(f'Selected ROI (x, y, w, h): {roi}')

            if w <= 0 or h <= 0:
                raise ParameterValidationError(
                    'Invalid ROI dimensions',
                    details={'roi': roi, 'width': w, 'height': h,
                             'constraint': 'width and height must be positive'}
                )

            roi_image = cv_image[y:y+h, x:x+w]

            # Calculate MTF
            self._node.get_logger().info('Calculating MTF from selected ROI...')
            mtf_results = self._node.image_processor.calculate_mtf_from_roi(
                roi_image)

            if not mtf_results:
                raise ImageProcessingError(
                    'MTF calculation failed - could not determine ESF or edge was not found',
                    details={'roi': roi, 'roi_size': (w, h)}
                )

            # Export results
            output_filename = self._node.get_parameter(
                'mtf_csv_path').get_parameter_value().string_value
            if not output_filename:
                raise ConfigurationError(
                    'MTF CSV output path not configured',
                    details={'parameter': 'mtf_csv_path',
                             'value': output_filename}
                )

            self._node.image_processor.export_to_csv(
                mtf_results, output_filename)

            response.success = True
            response.message = (
                f'MTF calculation successful. Results saved to {output_filename}'
            )
            self._node.get_logger().info(response.message)

        except ImageProcessingError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f'Image processing error details: {e.details}')

        except ParameterValidationError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f'Parameter validation details: {e.details}')

        except ConfigurationError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f'Configuration error details: {e.details}')

        except Exception as e:
            response.success = False
            response.message = f'❌ ROI selection failed: {str(e)}'
            self._node.get_logger().error(response.message, exc_info=True)

        return response

    # AUTOFOKUS

    def autofocus_callback(self, request, response):
        """
        Executes an automatic focus sequence.

        This implements a hybrid autofocus algorithm (promoc_core.algorithms.HybridAutofocus):
        - Coarse search across the full range.
        - Fine search around the detected maximum (unidirectional to minimize hysteresis).
        - Sharpness Metric: Tenengrad.

        Args:
            start_position (float): The starting Z-axis position for the focus search.
            end_position (float): The ending Z-axis position for the focus search.
            step_size (float): The step size for the coarse search phase.
        """
        self._node.get_logger().info(
            f'Autofocus service called with range {request.start_position} '
            f'to {request.end_position} with step {request.step_size}'
        )

        try:
            # Validate parameters
            if request.start_position >= request.end_position:
                raise InvalidParameterError(
                    'Start position must be less than end position',
                    details={
                        'start_position': request.start_position,
                        'end_position': request.end_position,
                        'constraint': 'start < end'
                    }
                )

            if request.step_size <= 0:
                raise InvalidParameterError(
                    'Step size must be positive',
                    details={
                        'parameter': 'step_size',
                        'value': request.step_size,
                        'constraint': 'positive'
                    }
                )

            # Create service clients for the Z-axis linear stage.
            # The node name of the Z-axis is retrieved from a ROS parameter.
            z_axis_name = self._node.get_parameter(
                'z_axis_node_name').get_parameter_value().string_value
            move_service = f'/{z_axis_name}/move_absolute'
            jog_service = f'/{z_axis_name}/jog_axis'
            status_service = f'/{z_axis_name}/get_operation_status'
            get_velocity_service = f'/{z_axis_name}/get_velocity_parameters'
            set_velocity_service = f'/{z_axis_name}/set_velocity_parameters'

            move_abs_client = self._node.create_client(
                MoveAbsolute, move_service)
            jog_client = self._node.create_client(
                JogAxis, jog_service)
            status_client = self._node.create_client(
                GetOperationStatus, status_service)
            get_velocity_client = self._node.create_client(
                GetVelocityParameters, get_velocity_service)
            set_velocity_client = self._node.create_client(
                SetVelocityParameters, set_velocity_service)

            if not move_abs_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    'Linear axis move_absolute service not available',
                    details={'service': move_service,
                             'timeout': 1.0}
                )

            if not jog_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    'Linear axis jog_axis service not available',
                    details={'service': jog_service, 'timeout': 1.0}
                )

            if not status_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    'Linear axis get_operation_status service not available',
                    details={'service': status_service, 'timeout': 1.0}
                )

            if not get_velocity_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    'Linear axis get_velocity_parameters service not available',
                    details={'service': get_velocity_service, 'timeout': 1.0}
                )

            if not set_velocity_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    'Linear axis set_velocity_parameters service not available',
                    details={'service': set_velocity_service, 'timeout': 1.0}
                )

            # Get current velocity parameters for later restoration
            get_vel_req = GetVelocityParameters.Request()
            get_vel_resp = get_velocity_client.call(get_vel_req)
            if get_vel_resp is None or not get_vel_resp.success:
                raise ServiceCallFailedError(
                    'Failed to get current velocity parameters',
                    details={'service': get_velocity_service}
                )
            original_max_velocity = get_vel_resp.max_velocity
            original_min_velocity = get_vel_resp.min_velocity
            original_acceleration = get_vel_resp.acceleration
            reduced_max_velocity = original_max_velocity * (2.0 / 3.0)  # 2/3 speed for backward
            self._node.get_logger().info(
                f'Velocity settings: normal={original_max_velocity:.2f}mm/s, '
                f'reduced (backward)={reduced_max_velocity:.2f}mm/s')

            def _set_velocity(max_vel: float) -> None:
                """Helper to set axis velocity."""
                set_vel_req = SetVelocityParameters.Request()
                set_vel_req.min_velocity = original_min_velocity
                set_vel_req.acceleration = original_acceleration
                set_vel_req.max_velocity = max_vel
                set_velocity_client.call(set_vel_req)

            # Configure the HybridAutofocus algorithm from promoc_core.
            # Multi-level refinement can be enabled via ROS parameters
            # to avoid changing the service interface.
            enable_multilevel = self._node.get_parameter(
                'autofocus.enable_multilevel').get_parameter_value().bool_value
            refinement_samples = self._node.get_parameter(
                'autofocus.refinement_samples').get_parameter_value().integer_value
            min_step_mm = self._node.get_parameter(
                'autofocus.min_step_mm').get_parameter_value().double_value
            refinement_shrink_factor = self._node.get_parameter(
                'autofocus.refinement_shrink_factor').get_parameter_value().double_value

            af_config = AutofocusConfig(
                z_min_mm=float(request.start_position),
                z_max_mm=float(request.end_position),
                coarse_step_mm=float(request.step_size),
                # Other params like fine_step_mm use defaults from AutofocusConfig.
                metric='tenengrad',
                enable_multilevel=bool(enable_multilevel),
                refinement_samples=int(
                    refinement_samples) if refinement_samples else 41,
                min_step_mm=float(min_step_mm) if min_step_mm else 0.01,
                refinement_shrink_factor=float(
                    refinement_shrink_factor) if refinement_shrink_factor else 0.25,
            )
            af = HybridAutofocus(af_config)

            # Move to initial position
            current_pos = float(af.start())
            move_req = MoveAbsolute.Request()
            move_req.axis_position = current_pos
            move_response = move_abs_client.call(move_req)

            if move_response is None:
                raise ServiceCallFailedError(
                    'Move to start position - no response received',
                    details={'target_position': request.start_position}
                )

            if not move_response.success:
                raise ServiceCallFailedError(
                    f'Failed to move to start position: {move_response.status_message}',
                    details={
                        'target_position': request.start_position,
                        'service_response': move_response.status_message
                    }
                )

            def _wait_for_axis_idle() -> None:
                self._node.get_logger().debug('Waiting for axis to become idle...')
                while True:
                    status_req = GetOperationStatus.Request()
                    status_resp = status_client.call(status_req)
                    if status_resp and status_resp.operation_status == 'idle':
                        return
                    if status_resp and status_resp.operation_status == 'error':
                        raise ServiceCallFailedError(
                            f'Axis reported error during movement: {status_resp.status_message}')
                    time.sleep(0.1)

            # Initial move wait
            _wait_for_axis_idle()

            # State-machine loop
            best_position: float | None = None
            best_score: float = 0.0
            max_iterations = 1000

            # Collect measurements for CSV export
            af_measurements: list[dict] = []
            af_start_time = time.time()

            for _ in range(max_iterations):
                if self._node.latest_image_msg is None:
                    # give the image subscriber a moment
                    time.sleep(0.1)

                if self._node.latest_image_msg is None:
                    raise ImageProcessingError(
                        'No image available during autofocus',
                        details={'z_mm': current_pos}
                    )

                cv_image = self._node.bridge.imgmsg_to_cv2(
                    self._node.latest_image_msg, 'bgr8')

                af_result = af.process_image(current_pos, cv_image)
                best_score = af_result.best_score

                # Collect measurement data for CSV export
                measurement_time = time.time() - af_start_time
                if af_result.current_score:
                    af_measurements.append({
                        'timestamp_s': round(measurement_time, 3),
                        'z_position_mm': round(current_pos, 4),
                        'tenengrad_score': round(af_result.current_score, 2),
                        'best_score': round(best_score, 2),
                        'phase': af_result.phase.name,
                        'step_mm': af_result.refinement_step_mm,
                        'range_mm': af_result.refinement_range_mm,
                    })

                # Logging with Tenengrad score
                if af_result.current_score:
                    level_info = ''
                    if (
                        af_result.refinement_step_mm is not None
                        and af_result.refinement_range_mm is not None
                    ):
                        level_info = (
                            f' step={af_result.refinement_step_mm:.4f}mm'
                            f' range=±{af_result.refinement_range_mm:.4f}mm'
                        )
                    self._node.get_logger().info(
                        f'AF {af_result.phase.name}: z={current_pos:.3f}mm '
                        f'tenengrad={af_result.current_score:.0f} best={best_score:.0f}{level_info}'
                    )
                else:
                    self._node.get_logger().debug(
                        f'AF {af_result.phase.name}: z={current_pos:.3f}mm best={best_score:.0f}')

                if af_result.finished:
                    best_position = float(
                        af_result.best_z_mm) if af_result.best_z_mm is not None else None
                    break

                if af_result.next_z_mm is None:
                    raise ImageProcessingError(
                        'Autofocus did not provide next position',
                        details={'phase': af_result.phase.name}
                    )

                # Move to next requested position
                next_pos = float(af_result.next_z_mm)

                # Reduce velocity when moving backward (decreasing position)
                # to prevent axis issues (loud beeping)
                is_backward = next_pos < current_pos
                if is_backward:
                    _set_velocity(reduced_max_velocity)
                else:
                    _set_velocity(original_max_velocity)

                move_req = MoveAbsolute.Request()
                move_req.axis_position = next_pos
                move_response = move_abs_client.call(move_req)

                if move_response is None or not move_response.success:
                    _set_velocity(original_max_velocity)  # Restore on error
                    raise ServiceCallFailedError(
                        f'Failed to move axis to {next_pos}',
                        details={'target_position': next_pos}
                    )

                _wait_for_axis_idle()
                current_pos = next_pos

            if best_position is None:
                raise ImageProcessingError(
                    'Autofocus did not finish within expected iterations',
                    details={'max_iterations': max_iterations}
                )

            self._node.get_logger().info(
                f'📷 Best focus position: {best_position:.3f}mm (tenengrad: {best_score:.0f})')

            # Export measurements to CSV
            csv_path = self._export_autofocus_csv(af_measurements, best_position, best_score)
            if csv_path:
                self._node.get_logger().info(f'📄 Autofocus data saved to: {csv_path}')

            final_step = getattr(af_result, 'refinement_step_mm', None)
            final_range = getattr(af_result, 'refinement_range_mm', None)
            final_level_info = ''
            if final_step is not None and final_range is not None:
                final_level_info = (
                    f' final_step={final_step:.4f}mm final_range=±{final_range:.4f}mm'
                )

            # Ensure we end at best position
            # Restore normal velocity for final move
            _set_velocity(original_max_velocity)
            move_req = MoveAbsolute.Request()
            move_req.axis_position = float(best_position)
            move_response = move_abs_client.call(move_req)
            if move_response is None or not move_response.success:
                raise ServiceCallFailedError(
                    f'Failed to move to best position: {best_position}',
                    details={'target_position': best_position}
                )
            _wait_for_axis_idle()

            response.success = True
            response.message = (
                f'Autofocus successful. Best position: {best_position:.3f}mm '
                f'(tenengrad score: {best_score:.2f}){final_level_info}'
            )

        except InvalidParameterError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f'Parameter validation details: {e.details}')

        except ServiceCallFailedError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().error(response.message)
            self._node.get_logger().debug(
                f'Service call error details: {e.details}')

        except ImageProcessingError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f'Image processing error details: {e.details}')

        except Exception as e:
            response.success = False
            response.message = f'❌ Autofocus failed: {str(e)}'
            self._node.get_logger().error(
                f'{response.message}\n{type(e).__name__}: {str(e)}')

        return response

    async def manual_set_exposure_callback(self, request, response):
        """Set the manual exposure time."""
        self._node.get_logger().info(
            f'Received manual request to set exposure to {request.exposure_time}µs')

        try:
            # Validate exposure time
            if request.exposure_time <= 0:
                raise InvalidParameterError(
                    'Exposure time must be positive',
                    details={
                        'parameter': 'exposure_time',
                        'value': request.exposure_time,
                        'constraint': 'positive',
                        'unit': 'microseconds'
                    }
                )

            # Set exposure time via driver
            success = await self._driver.set_exposure(request.exposure_time)

            if not success:
                raise HardwareError(
                    'Failed to set exposure time',
                    details={
                        'requested_exposure': request.exposure_time
                    }
                )

            response.success = True
            response.message = f'Exposure set to {request.exposure_time}µs successfully'
            self._node.get_logger().info(response.message)

        except InvalidParameterError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f'Parameter validation details: {e.details}')

        except HardwareError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().error(response.message)
            self._node.get_logger().debug(
                f'Hardware error details: {e.details}')

        except Exception as e:
            response.success = False
            response.message = f'❌ Setting exposure failed: {str(e)}'
            self._node.get_logger().error(response.message, exc_info=True)

        return response

    def measure_mtf_callback(self, request, response):
        """
        Measure MTF via the slanted edge method.

        Uses the slanted edge method (ISO 12233) to compute MTF from
        the current camera image.
        """
        self._node.get_logger().info('MTF measurement service called')

        try:
            # Check if image is available
            if self._node.latest_image_msg is None:
                raise ImageProcessingError(
                    'No image received yet',
                    details={
                        'context': 'MTF measurement requires active camera feed'}
                )

            # Convert ROS image to OpenCV format
            try:
                cv_image = self._node.bridge.imgmsg_to_cv2(
                    self._node.latest_image_msg, 'bgr8')
            except Exception as e:
                raise ImageProcessingError(
                    f'Failed to convert ROS image to OpenCV format: {str(e)}',
                    details={'encoding': 'bgr8', 'error': str(e)}
                )

            # Get pixel size from request or parameter
            pixel_size_um = request.pixel_size_um
            if pixel_size_um <= 0:
                pixel_size_um = self._node.get_parameter(
                    'pixel_size_um').get_parameter_value().double_value
                if pixel_size_um <= 0:
                    pixel_size_um = 3.45  # Default

            # Get ROI dimensions from request or parameter
            roi_width = request.roi_width
            if roi_width <= 0:
                roi_width = self._node.get_parameter(
                    'default_roi_width').get_parameter_value().integer_value
                if roi_width <= 0:
                    roi_width = 200

            roi_height = request.roi_height
            if roi_height <= 0:
                roi_height = self._node.get_parameter(
                    'default_roi_height').get_parameter_value().integer_value
                if roi_height <= 0:
                    roi_height = 200

            # Get ROI center
            h, w = cv_image.shape[:2]
            if request.roi_center_x < 0:
                roi_center_x = w // 2
            else:
                roi_center_x = request.roi_center_x

            if request.roi_center_y < 0:
                roi_center_y = h // 2
            else:
                roi_center_y = request.roi_center_y

            # Configure MTF analyzer
            config = MTFConfig(
                pixel_size_um=pixel_size_um,
                roi_width=roi_width,
                roi_height=roi_height,
                roi_center=(roi_center_x, roi_center_y)
            )

            analyzer = MTFAnalyzer(config)

            # Compute MTF
            self._node.get_logger().info(
                f'Computing MTF: ROI=({roi_center_x}, {roi_center_y}) '
                f'{roi_width}x{roi_height}px, pixel_size={pixel_size_um}µm'
            )

            result = analyzer.compute_mtf(cv_image)

            if not result.valid:
                raise ImageProcessingError(
                    f'MTF computation failed: {result.error_msg}',
                    details={
                        'edge_angle': result.edge_angle,
                        'roi_bounds': result.roi_bounds
                    }
                )

            # Populate response
            response.success = True
            response.message = (
                f'MTF measurement successful. MTF50={result.mtf50:.2f} lp/mm'
            )
            response.mtf50 = float(result.mtf50)
            response.mtf20 = float(result.mtf20)
            response.mtf10 = float(result.mtf10)
            response.edge_angle = float(result.edge_angle)
            response.nyquist_frequency = float(result.nyquist_frequency)

            self._node.get_logger().info(
                f'📊 MTF Results: MTF50={result.mtf50:.2f}, '
                f'MTF20={result.mtf20:.2f}, MTF10={result.mtf10:.2f} lp/mm '
                f'(edge angle: {result.edge_angle:.1f}°)'
            )

        except ImageProcessingError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f'Image processing error details: {e.details}')

        except Exception as e:
            response.success = False
            response.message = f'❌ MTF measurement failed: {str(e)}'
            self._node.get_logger().error(response.message, exc_info=True)

        return response
