"""
Service callbacks for camera node - business logic for image processing.

Implements ROS2 service callbacks for:
- Autofocus: Multi-level refinement algorithm with coarse search and iterative refinement
- MTF measurement: ISO 12233 slanted edge method
- ROI selection: Interactive selection with MTF calculation
- Exposure control: Manual setting of camera exposure time

Architecture:
Service Requests → CameraServiceCallbacks → camera_nodes.algorithms → ROS2 Services

Services:
- select_roi_callback: Interactive ROI selection and MTF measurement
- autofocus_callback: Automatic focus optimization with X-axis control
- measure_mtf_callback: ISO 12233 MTF measurement from image
- manual_set_exposure_callback: Set camera exposure time

Autofocus Algorithm:
Multi-level refinement approach:
1. Coarse search: Scan full range with large steps, find approximate maximum
2. Refinement (Phase 2+): Narrow search range, reduce step size, repeat

Sharpness Metric: Tenengrad (robust for single images)

Exception Handling:
- ImageProcessingError: Image processing failures
- InvalidParameterError: Invalid input values  
- ConfigurationError: Missing configuration
- ServiceCallFailedError: X-axis service unavailable
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
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    HardwareError,
    ImageProcessingError,
    InvalidParameterError,
    ParameterValidationError,
    ServiceCallFailedError,
)

from .algorithms import (
    Autofocus, 
    ParabolicAutofocus,
    HillClimbingAutofocus,
    AutofocusConfig,
    Phase,
    MTFAnalyzer, 
    MTFConfig, 
    tenengrad
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
        username_or_measurements,
        service_type_or_best_position=None,
        request_or_best_score=None,
        config=None
    ) -> str | None:
        """
        Export autofocus measurements to a CSV file.
        
        Two call modes:
        1. Legacy: (measurements, best_position, best_score)
        2. New: (username, service_type, request, config)

        Args:
            username_or_measurements: Username string or measurements list
            service_type_or_best_position: Service type ("standard"/"parabolic") or best position
            request_or_best_score: Request object or best score
            config: AutofocusConfig (for new mode only)

        Returns:
            Path to the created CSV file
        """
        # Determine call mode
        if isinstance(username_or_measurements, list):
            # Legacy mode: (measurements, best_position, best_score)
            measurements = username_or_measurements
            best_position = service_type_or_best_position
            best_score = request_or_best_score
            
            if not measurements:
                return None
                
            # Get username from node parameter
            username = ''
            if self._node.has_parameter('measurement.username'):
                username = self._node.get_parameter(
                    'measurement.username').get_parameter_value().string_value.strip()
            
            # Create filename without parameters (legacy)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f'autofocus_{timestamp}.csv'
            
        else:
            # New mode: (username, service_type, request, config)
            username = username_or_measurements
            service_type = service_type_or_best_position
            request = request_or_best_score
            
            # Create filename with parameters
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = (
                f'autofocus_{service_type}_'
                f'{request.start_position:.0f}-{request.end_position:.0f}mm_'
                f'step{request.step_size:.1f}mm_'
                f'{timestamp}.csv'
            )
            measurements = None  # Will be written incrementally
            best_position = None
            best_score = None

        try:
            # Create output directory
            base_dir = Path.home() / 'Dokumente' / 'Messungen'
            output_dir = (base_dir / username / 'autofocus_logs') if username else (base_dir / 'autofocus_logs')
            output_dir.mkdir(parents=True, exist_ok=True)

            csv_path = output_dir / csv_filename

            # Write CSV file
            fieldnames = [
                'timestamp_s', 'z_position_mm', 'tenengrad_score',
                'best_score', 'phase', 'step_mm', 'range_mm'
            ]

            with open(csv_path, 'w', newline='') as csvfile:
                # Write header comment with summary
                csvfile.write(f'# Autofocus Results - {datetime.now().isoformat()}\n')
                if best_position is not None:
                    csvfile.write(f'# Best Position: {best_position:.4f} mm\n')
                    csvfile.write(f'# Best Tenengrad Score: {best_score:.2f}\n')
                    csvfile.write(f'# Total Measurements: {len(measurements)}\n')
                elif config is not None:
                    csvfile.write(f'# Service: {service_type_or_best_position}\n')
                    csvfile.write(f'# Range: {request_or_best_score.start_position:.1f} - {request_or_best_score.end_position:.1f} mm\n')
                    csvfile.write(f'# Step Size: {request_or_best_score.step_size:.2f} mm\n')
                    csvfile.write(f'# Refinement Samples: {config.refinement_samples}\n')
                    csvfile.write(f'# Min Step: {config.min_step_mm:.4f} mm\n')
                    csvfile.write(f'# Shrink Factor: {config.shrink_factor:.2f}\n')
                
                # Write measurement conditions
                try:
                    # Prefer request overrides if available (and not empty/zero)
                    req = request  # Alias for brevity
                    
                    # 1. Voltage
                    if hasattr(req, 'coaxial_light_voltage') and req.coaxial_light_voltage > 0.001:
                        coaxial_v = req.coaxial_light_voltage
                    else:
                        coaxial_v = self._node.get_parameter('measurement_conditions.coaxial_light_voltage').value
                    
                    # 2. Current
                    if hasattr(req, 'coaxial_light_current') and req.coaxial_light_current > 0.001:
                        coaxial_a = req.coaxial_light_current
                    else:
                        coaxial_a = self._node.get_parameter('measurement_conditions.coaxial_light_current').value
                    
                    # 3. Objective
                    if hasattr(req, 'camera_objective') and req.camera_objective:
                        objective = req.camera_objective
                    else:
                        objective = self._node.get_parameter('measurement_conditions.camera_objective').value
                    
                    # 4. Notes
                    if hasattr(req, 'notes') and req.notes:
                        notes_val = req.notes
                    else:
                        notes_val = self._node.get_parameter('measurement_conditions.notes').value

                    csvfile.write(f'#\n# Measurement Conditions:\n')
                    csvfile.write(f'#   Coaxial Light: {coaxial_v}V, {coaxial_a}A\n')
                    csvfile.write(f'#   Camera Objective: {objective}\n')
                    if notes_val:
                        csvfile.write(f'#   Notes: {notes_val}\n')
                except Exception as e:
                    self._node.get_logger().warn(f'Could not write measurement conditions to CSV: {e}')
                
                csvfile.write('#\n')

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write data if legacy mode
                if measurements:
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

            # Resize image for ROI selection if it's too large
            display_image = cv_image.copy()
            height, width = display_image.shape[:2]
            max_height = 800  # Reasonable height for most screens
            scale_factor = 1.0

            if height > max_height:
                scale_factor = max_height / height
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                display_image = cv2.resize(display_image, (new_width, new_height))
                self._node.get_logger().info(f'Resizing selection window: {width}x{height} -> {new_width}x{new_height} (scale: {scale_factor:.2f})')

            # User selects ROI
            # Note: selectROI can hang if not handled correctly in ROS context
            # Adding a named window with autosize can help
            window_name = 'Select ROI'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, display_image.shape[1], display_image.shape[0])
            
            # Using selectROI on the (possibly resized) image
            roi = cv2.selectROI(window_name, display_image,
                                fromCenter=False, showCrosshair=True)
            cv2.destroyWindow(window_name)
            
            # Process events to ensure window closes properly
            cv2.waitKey(1)

            if roi == (0, 0, 0, 0):
                self._node.get_logger().info('ROI selection cancelled by user.')
                response.success = False
                response.message = 'ROI selection cancelled.'
                return response

            # Extract and validate ROI
            x_scaled, y_scaled, w_scaled, h_scaled = roi
            
            # Scale back to original coordinates
            x = int(x_scaled / scale_factor)
            y = int(y_scaled / scale_factor)
            w = int(w_scaled / scale_factor)
            h = int(h_scaled / scale_factor)
            
            # Clamp to image boundaries just in case
            img_h, img_w = cv_image.shape[:2]
            x = max(0, min(x, img_w - 1))
            y = max(0, min(y, img_h - 1))
            w = max(1, min(w, img_w - x))
            h = max(1, min(h, img_h - y))
            
            roi = (x, y, w, h)
            self._node.get_logger().info(f'Selected ROI (scaled back): {roi}')

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

        Scans the X-axis range and finds the sharpest focus position using Tenengrad metric.

        Args:
            start_position (float): The starting X-axis position for the focus search.
            end_position (float): The ending X-axis position for the focus search.
            step_size (float): The step size for the coarse search phase.
        """

        start_time = time.time()   #Starting a timer to measure duration of autofocus

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

            # Create service clients for the X-axis linear stage.
            # The node name of the X-axis is retrieved from a ROS parameter.
            x_axis_name = self._node.get_parameter(
                'z_axis_node_name').get_parameter_value().string_value
            move_service = f'/{x_axis_name}/move_absolute'
            jog_service = f'/{x_axis_name}/jog_axis'
            status_service = f'/{x_axis_name}/get_operation_status'

            move_abs_client = self._node.create_client(
                MoveAbsolute, move_service)
            jog_client = self._node.create_client(
                JogAxis, jog_service)
            status_client = self._node.create_client(
                GetOperationStatus, status_service)

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

            # Configure the autofocus algorithm
            refinement_samples = self._node.get_parameter(
                'autofocus.refinement_samples').get_parameter_value().integer_value
            min_step_mm = self._node.get_parameter(
                'autofocus.min_step_mm').get_parameter_value().double_value
            shrink_factor = self._node.get_parameter(
                'autofocus.refinement_shrink_factor').get_parameter_value().double_value

            af_config = AutofocusConfig(
                start_mm=float(request.start_position),
                end_mm=float(request.end_position),
                step_mm=float(request.step_size),
                refinement_samples=int(refinement_samples) if refinement_samples else 51,
                min_step_mm=float(min_step_mm) if min_step_mm else 0.01,
                shrink_factor=float(shrink_factor) if shrink_factor else 0.35,
                disable_coarse_early_termination=True  # Scan full range in standard mode
            )
            af = Autofocus(af_config)
            
            # Setup CSV logging
            username = self._node.get_parameter(
                'measurement.username').get_parameter_value().string_value
            csv_path = self._export_autofocus_csv(username, "standard", request, af_config)
            self._node.get_logger().info(f'📊 CSV log: {csv_path}')

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
            is_first_refinement_move = True  # Track first refinement move

            # Collect measurements for CSV export
            af_measurements: list[dict] = []
            af_start_time = time.time()
            last_logged_level = -1  # Track level changes for logging
            
            # Log coarse scan parameters at the very beginning
            self._node.get_logger().info(
                f'→ Starting Coarse Scan: step={request.step_size:.4f}mm range={request.start_position:.1f}-{request.end_position:.1f}mm'
            )

            for _ in range(max_iterations):
                if self._node.latest_image_msg is None:
                    # give the image subscriber a moment
                    time.sleep(0.1)

                if self._node.latest_image_msg is None:
                    raise ImageProcessingError(
                        'No image available during autofocus',
                        details={'x_mm': current_pos}
                    )

                cv_image = self._node.bridge.imgmsg_to_cv2(
                    self._node.latest_image_msg, 'bgr8')

                af_result = af.process_image(current_pos, cv_image)
                best_score = af_result.best_score

                # Write measurement to CSV incrementally
                measurement_time = time.time()
                if af_result.current_score:
                    with open(csv_path, 'a', newline='') as f:
                        csv.writer(f).writerow([
                            measurement_time - af_start_time,  # Relative timestamp
                            round(current_pos, 4),
                            round(af_result.current_score, 2),
                            round(best_score, 2),
                            af_result.phase.name,
                            af_result.current_step_mm,
                            af_result.current_range_mm,
                        ])

                # Logging with Tenengrad score
                if af_result.current_score:
                    self._node.get_logger().info(
                        f'AF {af_result.phase.name}: x={current_pos:.3f}mm '
                        f'tenengrad={af_result.current_score:.0f} best={best_score:.0f}'
                    )
                    
                    # Show level info AFTER measurement, when level changes for NEXT iteration
                    # Skip Level 0 (coarse scan) - only show refinement levels
                    if af_result.current_level != last_logged_level and af_result.current_level > 0:
                        last_logged_level = af_result.current_level
                        if af_result.current_step_mm is not None and af_result.current_range_mm is not None:
                            self._node.get_logger().info(
                                f'→ Level {af_result.current_level}: step={af_result.current_step_mm:.4f}mm range=±{af_result.current_range_mm:.4f}mm'
                            )
                else:
                    self._node.get_logger().debug(
                        f'AF {af_result.phase.name}: x={current_pos:.3f}mm best={best_score:.0f}')

                if af_result.finished:
                    best_position = af_result.best_position_mm
                    break

                if af_result.next_position_mm is None:
                    raise ImageProcessingError(
                        'Autofocus did not provide next position',
                        details={'phase': af_result.phase.name}
                    )

                # Move to next requested position
                next_pos = float(af_result.next_position_mm)

                # Use jog for refinement (more precise), but use move_absolute for first refinement point
                # (could be far from last coarse scan position)
                if af_result.phase == Phase.REFINEMENT and not is_first_refinement_move:
                    # Subsequent refinement moves: use jog (precise, small steps)
                    distance = next_pos - current_pos
                    jog_req = JogAxis.Request()
                    jog_req.step_size = distance
                    move_response = jog_client.call(jog_req)
                else:
                    # Coarse scan OR first refinement point: use absolute positioning
                    if af_result.phase == Phase.REFINEMENT:
                        is_first_refinement_move = False  # Mark that we've done first refinement move
                    move_req = MoveAbsolute.Request()
                    move_req.axis_position = next_pos
                    move_response = move_abs_client.call(move_req)

                if move_response is None or not move_response.success:
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

            # CSV already written incrementally
            self._node.get_logger().info(f'📄 Autofocus data saved to: {csv_path}')

            # Ensure we end at best position
            move_req = MoveAbsolute.Request()
            move_req.axis_position = float(best_position)
            move_response = move_abs_client.call(move_req)
            if move_response is None or not move_response.success:
                raise ServiceCallFailedError(
                    f'Failed to move to best position: {best_position}',
                    details={'target_position': best_position}
                )
            _wait_for_axis_idle()

            duration = time.time() - start_time
            response.success = True
            response.message = (
                f'Autofocus successful. Best position: {best_position:.3f}mm '
                f'(tenengrad: {best_score:.0f}, duration: {duration:.1f}s)'
            )
            response.best_focus_position = best_position
            response.best_focus_value = best_score
            response.total_measurements_taken = len(af_measurements)
            response.duration_seconds = duration

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

    def autofocus_parabolic_callback(self, request, response):
        """
        Enhanced autofocus with parabolic interpolation and peak validation.
        
        Uses ParabolicAutofocus for sub-sample accuracy and faster convergence.
        """
        start_time = time.time()
        
        self._node.get_logger().info(
            f'🔬 Parabolic Autofocus: range {request.start_position}-{request.end_position}mm, step {request.step_size}mm'
        )
        
        try:
            # Parameter validation
            if request.start_position >= request.end_position:
                raise InvalidParameterError(
                    'Start position must be less than end position',
                    details={'start': request.start_position, 'end': request.end_position}
                )

            if request.step_size <= 0:
                raise InvalidParameterError('Step size must be positive')

            # Service clients
            x_axis_name = self._node.get_parameter('z_axis_node_name').value
            move_abs_client = self._node.create_client(MoveAbsolute, f'/{x_axis_name}/move_absolute')
            jog_client = self._node.create_client(JogAxis, f'/{x_axis_name}/jog_axis')
            status_client = self._node.create_client(GetOperationStatus, f'/{x_axis_name}/get_operation_status')

            if not move_abs_client.wait_for_service(timeout_sec=5.0):
                raise ServiceCallFailedError('Move service not available')
            if not jog_client.wait_for_service(timeout_sec=5.0):
                raise ServiceCallFailedError('Jog service not available')
            if not status_client.wait_for_service(timeout_sec=5.0):
                raise ServiceCallFailedError('Status service not available')

            # Autofocus configuration
            config = AutofocusConfig(
                start_mm=request.start_position,
                end_mm=request.end_position,
                step_mm=request.step_size,
                refinement_samples=self._node.get_parameter('autofocus.refinement_samples').value,
                min_step_mm=self._node.get_parameter('autofocus.min_step_mm').value,
                shrink_factor=self._node.get_parameter('autofocus.refinement_shrink_factor').value,
                disable_coarse_early_termination=True  # Scan full range for parabolic fit
            )

            # Initialize ParabolicAutofocus
            autofocus = ParabolicAutofocus(config)
            position_mm = autofocus.start()

            # CSV logging
            username = self._node.get_parameter('measurement.username').value
            csv_path = self._export_autofocus_csv(username, "parabolic", request, config)
            
            measurement_count = 0
            self._node.get_logger().info(f'📊 CSV log: {csv_path}')
            
            # Log coarse scan parameters at the very beginning
            self._node.get_logger().info(
                f'→ Starting Coarse Scan: step={config.step_mm:.4f}mm range={config.start_mm:.1f}-{config.end_mm:.1f}mm'
            )

            # Main loop
            prev_position = position_mm
            current_level = 0
            last_logged_level = -1  # Track level changes for logging
            is_first_level_move = [True] * 10  # Track first move for each level
            while True:
                # Move - use jog for refinement (L1+), but move_absolute for first move of each level
                if current_level > 0 and measurement_count > 0 and not is_first_level_move[current_level]:
                    # Refinement: use jog (more precise) for subsequent moves in level
                    distance = position_mm - prev_position
                    jog_req = JogAxis.Request()
                    jog_req.step_size = distance
                    move_future = jog_client.call_async(jog_req)
                else:
                    # Coarse or first move of refinement level: use absolute
                    if current_level > 0:
                        is_first_level_move[current_level] = False
                    move_req = MoveAbsolute.Request(axis_position=position_mm)
                    move_future = move_abs_client.call_async(move_req)
                
                while not move_future.done():
                    pass
                if not move_future.result().success:
                    raise ServiceCallFailedError(f'Move to {position_mm}mm failed')
                
                prev_position = position_mm

                # Wait for motion complete
                while True:
                    status_future = status_client.call_async(GetOperationStatus.Request())
                    while not status_future.done():
                        pass
                    status_response = status_future.result()
                    if status_response.operation_status not in ['moving', 'homing', 'jogging']:
                        break
                    time.sleep(0.05)

                # Capture & process
                if self._node.latest_image_msg is None:
                    time.sleep(0.1)
                
                if self._node.latest_image_msg is None:
                    raise ImageProcessingError(
                        'No image available during autofocus',
                        details={'x_mm': position_mm}
                    )

                cv_image = self._node.bridge.imgmsg_to_cv2(
                    self._node.latest_image_msg, 'bgr8')

                result = autofocus.process_image(position_mm, cv_image)
                measurement_count += 1
                current_level = result.current_level  # Update for next iteration

                # Logging - show measurement first
                phase_name = "COARSE_SCAN" if result.current_level == 0 else "REFINEMENT"
                
                self._node.get_logger().info(
                    f'AF {phase_name}: x={position_mm:.3f}mm tenengrad={int(result.current_score)} '
                    f'best={int(result.best_score)}'
                )
                
                # Show level info AFTER measurement, when level changes for next iteration
                # Skip Level 0 (coarse scan) - only show refinement levels
                if result.current_level != last_logged_level and result.current_level > 0:
                    last_logged_level = result.current_level
                    self._node.get_logger().info(
                        f'→ Level {result.current_level}: step={result.current_step_mm:.4f}mm range=±{result.current_range_mm:.4f}mm'
                    )

                # CSV
                with open(csv_path, 'a', newline='') as f:
                    csv.writer(f).writerow([
                        time.time() - start_time,  # Relative timestamp
                        position_mm, int(result.current_score),
                        int(result.best_score), phase_name,
                        result.current_step_mm, result.current_range_mm
                    ])

                # Done?
                if result.finished:
                    duration = time.time() - start_time
                    self._node.get_logger().info(
                        f'✅ Parabolic AF complete: {result.best_position_mm:.3f}mm '
                        f'(score: {int(result.best_score)}, {measurement_count} measurements, {duration:.1f}s)'
                    )

                    response.success = True
                    response.message = f'Parabolic autofocus completed: {result.best_position_mm:.3f}mm'
                    response.best_focus_position = result.best_position_mm
                    response.best_focus_value = result.best_score
                    response.total_measurements_taken = measurement_count
                    response.duration_seconds = duration
                    break

                position_mm = result.next_position_mm

        except InvalidParameterError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().error(response.message)

        except ServiceCallFailedError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().error(response.message)

        except ImageProcessingError as e:
            response.success = False
            response.message = f'⚠️ {str(e)}'
            self._node.get_logger().warn(response.message)

        except Exception as e:
            response.success = False
            response.message = f'❌ Parabolic AF failed: {str(e)}'
            self._node.get_logger().error(f'{response.message}\n{type(e).__name__}: {str(e)}')

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

    def autofocus_fast_callback(self, request, response):
        """
        Executes a FAST focus sequence using Hill Climbing.
        
        Aborts coarse scan early when peak is crossed.
        """
        start_time = time.time()
        self._node.get_logger().info(
            f'FAST Autofocus service called with range {request.start_position} '
            f'to {request.end_position} with step {request.step_size}'
        )

        try:
            # Reuse logic from standard callback but with HillClimbingAutofocus class
            # We copy key parts to avoid massive code duplication if we refactored,
            # but for now duplication is safer than breaking standard callback.
            
            # --- SETUP ---
            # Create service clients
            x_axis_name = self._node.get_parameter('z_axis_node_name').get_parameter_value().string_value
            move_abs_client = self._node.create_client(MoveAbsolute, f'/{x_axis_name}/move_absolute')
            jog_client = self._node.create_client(JogAxis, f'/{x_axis_name}/jog_axis')
            status_client = self._node.create_client(GetOperationStatus, f'/{x_axis_name}/get_operation_status')

            if not move_abs_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError('Linear axis move_absolute service not available')
            if not jog_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError('Linear axis jog_axis service not available')

            # Configure
            refinement_samples = self._node.get_parameter('autofocus.refinement_samples').get_parameter_value().integer_value
            min_step_mm = self._node.get_parameter('autofocus.min_step_mm').get_parameter_value().double_value
            
            # Get estimated peak from request (optional)
            estimated_peak_millions = request.estimated_peak_millions if hasattr(request, 'estimated_peak_millions') and request.estimated_peak_millions > 0 else 100.0
            
            af_config = AutofocusConfig(
                start_mm=float(request.start_position),
                end_mm=float(request.end_position),
                step_mm=float(request.step_size),
                refinement_samples=int(refinement_samples) if refinement_samples else 31,
                min_step_mm=float(min_step_mm) if min_step_mm else 0.01
            )
            
            # USE HILL CLIMBING with estimated peak
            af = HillClimbingAutofocus(af_config, estimated_peak_millions)
            
            # Logging
            username = self._node.get_parameter('measurement.username').get_parameter_value().string_value
            csv_path = self._export_autofocus_csv(username, "fast_hillclimb", request, af_config)
            
            # --- MOVEMENT LOOP ---
            current_pos = float(af.start())
            
            # Move to start
            move_req = MoveAbsolute.Request()
            move_req.axis_position = current_pos
            if not move_abs_client.call(move_req).success:
                 raise ServiceCallFailedError('Failed to move to start position')

            # Wait for idle
            while True:
                if status_client.call(GetOperationStatus.Request()).operation_status == 'idle': break
                time.sleep(0.05)
                
            best_position = None
            best_score = 0.0
            af_start_time = time.time()
            is_first_refinement_move = True  # Track first refinement move
            last_logged_level = -1  # Track level changes for logging
            
            # Log coarse scan parameters at the very beginning
            self._node.get_logger().info(
                f'→ Starting Coarse Scan: step={request.step_size:.4f}mm range={request.start_position:.1f}-{request.end_position:.1f}mm'
            )
            
            for _ in range(500): # max iterations
                # Get Image
                if self._node.latest_image_msg is None: time.sleep(0.1)
                if self._node.latest_image_msg is None: raise ImageProcessingError('No image')
                cv_image = self._node.bridge.imgmsg_to_cv2(self._node.latest_image_msg, 'bgr8')
                
                # Process
                af_result = af.process_image(current_pos, cv_image)
                best_score = af_result.best_score
                
                # CSV & Log
                if af_result.current_score:
                    with open(csv_path, 'a', newline='') as f:
                        csv.writer(f).writerow([
                            time.time() - af_start_time,
                            round(current_pos, 4),
                            round(af_result.current_score, 2),
                            round(best_score, 2),
                            af_result.phase.name,
                            af_result.current_step_mm,
                            af_result.current_range_mm,
                        ])
                    
                    # Logging - show measurement first
                    self._node.get_logger().info(
                        f'AF {af_result.phase.name}: x={current_pos:.3f}mm '
                        f'tenengrad={af_result.current_score:.0f} best={best_score:.0f}'
                    )
                    
                    # Show level info AFTER measurement, when level changes for next iteration
                    # Skip Level 0 (coarse scan) - only show refinement levels
                    if af_result.current_level != last_logged_level and af_result.current_level > 0:
                        last_logged_level = af_result.current_level
                        if af_result.current_step_mm is not None and af_result.current_range_mm is not None:
                            self._node.get_logger().info(
                                f'→ Level {af_result.current_level}: step={af_result.current_step_mm:.4f}mm range=±{af_result.current_range_mm:.4f}mm'
                            )

                if af_result.finished:
                    best_position = af_result.best_position_mm
                    break
                    
                # Move Next - use move_absolute for first refinement point, then jog
                next_pos = float(af_result.next_position_mm)
                
                if af_result.phase == Phase.REFINEMENT and not is_first_refinement_move:
                    # Subsequent refinement moves: use jog (precise)
                    distance = next_pos - current_pos
                    jog_req = JogAxis.Request()
                    jog_req.step_size = distance
                    move_response = jog_client.call(jog_req)
                else:
                    # Coarse scan or first refinement point: use absolute
                    if af_result.phase == Phase.REFINEMENT:
                        is_first_refinement_move = False
                    move_req.axis_position = next_pos
                    move_response = move_abs_client.call(move_req)
                
                if move_response is None or not move_response.success:
                    raise ServiceCallFailedError(
                        f'Failed to move axis to {next_pos}mm',
                        details={'target_position': next_pos}
                    )
                
                # Wait for axis to become idle
                while True:
                    status_req = GetOperationStatus.Request()
                    status_resp = status_client.call(status_req)
                    if status_resp and status_resp.operation_status == 'idle':
                        break
                    if status_resp and status_resp.operation_status == 'error':
                        raise ServiceCallFailedError(
                            f'Axis reported error during movement: {status_resp.status_message}')
                    time.sleep(0.05)
                    
                current_pos = next_pos

            # --- FINISH ---
            if best_position is None:
                raise ImageProcessingError('Autofocus did not converge')
                
            # Move to Best
            move_req.axis_position = float(best_position)
            move_abs_client.call(move_req)
            while True:
                if status_client.call(GetOperationStatus.Request()).operation_status == 'idle': break
                time.sleep(0.1)

            duration = time.time() - start_time
            response.success = True
            response.message = f'Fast AF successful: {best_position:.3f}mm ({duration:.1f}s)'
            response.best_focus_position = best_position
            response.best_focus_value = best_score
            response.duration_seconds = duration
            return response

        except Exception as e:
            response.success = False
            response.message = f'Fast AF failed: {str(e)}'
            self._node.get_logger().error(response.message)
            return response

    def autofocus_comparison_test_callback(self, request, response):
        """
        Test service that runs all 3 autofocus algorithms sequentially for comparison.
        
        Calls in order:
        1. Standard Autofocus
        2. Parabolic Autofocus  
        3. Fast Autofocus (HillClimbing)
        
        Returns combined results with timing and accuracy comparison.
        """
        self._node.get_logger().info('='*60)
        self._node.get_logger().info('🧪 AUTOFOCUS COMPARISON TEST STARTED')
        self._node.get_logger().info(f'Range: {request.start_position}-{request.end_position}mm, Step: {request.step_size}mm')
        self._node.get_logger().info('='*60)
        
        results = []
        test_start = time.time()
        
        # Test 1: Standard Autofocus
        self._node.get_logger().info('\n📊 Test 1/3: Standard Autofocus')
        self._node.get_logger().info('-'*60)
        try:
            from promoc_assembly_interfaces.srv import AutoFocus
            req = AutoFocus.Request()
            req.start_position = request.start_position
            req.end_position = request.end_position
            req.step_size = request.step_size
            res = AutoFocus.Response()
            
            res = self.autofocus_callback(req, res)
            
            if res.success:
                results.append({
                    'name': 'Standard',
                    'position': res.best_focus_position,
                    'score': res.best_focus_value,
                    'duration': res.duration_seconds,
                    'measurements': res.total_measurements_taken
                })
                self._node.get_logger().info(f'✓ Standard: {res.best_focus_position:.3f}mm, score={res.best_focus_value:.0f}, time={res.duration_seconds:.1f}s')
            else:
                self._node.get_logger().error(f'✗ Standard failed: {res.message}')
        except Exception as e:
            self._node.get_logger().error(f'✗ Standard exception: {e}')
        
        time.sleep(1.0)  # Brief pause between tests
        
        # Test 2: Parabolic Autofocus
        self._node.get_logger().info('\n📊 Test 2/3: Parabolic Autofocus')
        self._node.get_logger().info('-'*60)
        try:
            req = AutoFocus.Request()
            req.start_position = request.start_position
            req.end_position = request.end_position
            req.step_size = request.step_size
            res = AutoFocus.Response()
            
            res = self.autofocus_parabolic_callback(req, res)
            
            if res.success:
                results.append({
                    'name': 'Parabolic',
                    'position': res.best_focus_position,
                    'score': res.best_focus_value,
                    'duration': res.duration_seconds,
                    'measurements': res.total_measurements_taken
                })
                self._node.get_logger().info(f'✓ Parabolic: {res.best_focus_position:.3f}mm, score={res.best_focus_value:.0f}, time={res.duration_seconds:.1f}s')
            else:
                self._node.get_logger().error(f'✗ Parabolic failed: {res.message}')
        except Exception as e:
            self._node.get_logger().error(f'✗ Parabolic exception: {e}')
        
        time.sleep(1.0)
        
        # Test 3: Fast Autofocus
        self._node.get_logger().info('\n📊 Test 3/3: Fast Autofocus (HillClimbing)')
        self._node.get_logger().info('-'*60)
        try:
            req = AutoFocus.Request()
            req.start_position = request.start_position
            req.end_position = request.end_position
            req.step_size = request.step_size
            req.estimated_peak_millions = 500.0  # Set high threshold to scan full range
            res = AutoFocus.Response()
            
            res = self.autofocus_fast_callback(req, res)
            
            if res.success:
                results.append({
                    'name': 'Fast',
                    'position': res.best_focus_position,
                    'score': res.best_focus_value,
                    'duration': res.duration_seconds,
                    'measurements': 0  # Fast doesn't report this
                })
                self._node.get_logger().info(f'✓ Fast: {res.best_focus_position:.3f}mm, score={res.best_focus_value:.0f}, time={res.duration_seconds:.1f}s')
            else:
                self._node.get_logger().error(f'✗ Fast failed: {res.message}')
        except Exception as e:
            self._node.get_logger().error(f'✗ Fast exception: {e}')
        
        # Summary
        total_duration = time.time() - test_start
        self._node.get_logger().info('\n' + '='*60)
        self._node.get_logger().info('📊 COMPARISON SUMMARY')
        self._node.get_logger().info('='*60)
        
        if len(results) > 0:
            # Calculate statistics
            positions = [r['position'] for r in results]
            scores = [r['score'] for r in results]
            durations = [r['duration'] for r in results]
            
            mean_pos = sum(positions) / len(positions)
            max_deviation = max(abs(p - mean_pos) for p in positions)
            
            self._node.get_logger().info(f'\nResults:')
            for r in results:
                self._node.get_logger().info(
                    f"  {r['name']:10s}: {r['position']:7.3f}mm  "
                    f"score={r['score']:11.0f}  time={r['duration']:5.1f}s"
                )
            
            self._node.get_logger().info(f'\nStatistics:')
            self._node.get_logger().info(f'  Mean position:    {mean_pos:.3f}mm')
            self._node.get_logger().info(f'  Max deviation:    {max_deviation:.3f}mm')
            self._node.get_logger().info(f'  Total test time:  {total_duration:.1f}s')
            
            # Best score
            best_result = max(results, key=lambda x: x['score'])
            self._node.get_logger().info(f'\n🏆 Best score: {best_result["name"]} ({best_result["score"]:.0f})')
            
            # Fastest
            fastest_result = min(results, key=lambda x: x['duration'])
            self._node.get_logger().info(f'⚡ Fastest: {fastest_result["name"]} ({fastest_result["duration"]:.1f}s)')
            
            response.success = True
            response.message = f'Comparison complete: {len(results)}/3 algorithms succeeded. Mean={mean_pos:.3f}mm, deviation={max_deviation:.3f}mm'
        else:
            self._node.get_logger().error('❌ All autofocus algorithms failed!')
            response.success = False
            response.message = 'All autofocus algorithms failed'
        
        self._node.get_logger().info('='*60)
        return response
