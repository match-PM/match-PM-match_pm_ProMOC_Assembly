"""MTF callbacks for Modulation Transfer Function measurements."""

from datetime import datetime
from pathlib import Path
import time
import cv2
import numpy as np

from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue

from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
)
from .base import CallbackBase
from ..algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
from ..algorithms.roi_detection import RoiDetector, EdgeROI
from promoc_core.error_handling import handle_service_errors


class MTFCallbacks(CallbackBase):
    """Callbacks for MTF measurements and ROI selection."""

    def _select_roi_interactive(self, cv_image):
        """Opens window for ROI selection."""
        display_image = cv_image.copy()
        height, width = display_image.shape[:2]
        max_height = 800
        scale_factor = 1.0

        if height > max_height:
            scale_factor = max_height / height
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            display_image = cv2.resize(display_image, (new_width, new_height))

        window_name = 'Select ROI'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, display_image.shape[1], display_image.shape[0])

        roi = cv2.selectROI(window_name, display_image,
                            fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(window_name)
        cv2.waitKey(1)

        if roi == (0, 0, 0, 0):
            return None, None

        x_scaled, y_scaled, w_scaled, h_scaled = roi
        x = int(x_scaled / scale_factor)
        y = int(y_scaled / scale_factor)
        w = int(w_scaled / scale_factor)
        h = int(h_scaled / scale_factor)

        img_h, img_w = cv_image.shape[:2]
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))

        roi = (x, y, w, h)
        roi_image = cv_image[y:y+h, x:x+w]
        return roi, roi_image

    @handle_service_errors()
    def select_roi_callback(self, request, response):
        """Interactive ROI selection with MTF calculation."""
        self._node.get_logger().info('ROI selection service called.')

        if self._node.latest_image_msg is None:
            raise ImageProcessingError('No image received yet')

        cv_image = self._node.bridge.imgmsg_to_cv2(
            self._node.latest_image_msg, 'bgr8')

        roi, roi_image = self._select_roi_interactive(cv_image)
        if roi is None:
            response.success = False
            response.status_message = 'ROI selection cancelled.'
            return response

        x, y, w, h = roi
        if w <= 0 or h <= 0:
            raise ConfigurationError('Invalid ROI dimensions')

        mtf_results = self._node.image_processor.calculate_mtf_from_roi(roi_image)
        if not mtf_results:
            raise ImageProcessingError('MTF calculation failed')

        output_dir = self._get_output_dir('mtf_messungen')
        output_filename = str(output_dir / f'mtf_{self._get_timestamp()}.csv')
        self._node.image_processor.export_to_csv(mtf_results, output_filename)

        response.success = True
        response.status_message = f'MTF saved to {output_filename}'

        return response

    def _set_camera_binning(self, factor: int):
        """Switches camera binning factor and resolution via parameter service."""
        try:
            client = self._node.create_client(SetParameters, '/promoc/assembly_camera/set_parameters')
            if not client.wait_for_service(timeout_sec=2.0):
                self._node.get_logger().warn('Parameter service not ready, cannot switch binning')
                return

            req = SetParameters.Request()
            val_bin = ParameterValue(type=ParameterType.PARAMETER_INTEGER, integer_value=factor)
            
            # Determine target resolution based on binning
            # Full Sensor: 5536 x 3690 (approx, depending on camera exact model)
            # Using precise values from config/datasheet
            if factor == 1:
                w, h = 5536, 3692
            else:
                w, h = 2768, 1846
            
            val_w = ParameterValue(type=ParameterType.PARAMETER_INTEGER, integer_value=w)
            val_h = ParameterValue(type=ParameterType.PARAMETER_INTEGER, integer_value=h)

            # We must set Binning first, or Width/Height first?
            # GenICam is tricky. Usually setting Width too high for current Binning fails.
            # So: If going 2->1 (Getting bigger): Set Binning=1 FIRST, then Width=Big.
            # If going 1->2 (Getting smaller): Set Width=Small FIRST, then Binning=2.
            
            # Strategy: Send two requests to be safe, or one order-independent?
            # ROS parameters are set in list order potentially? Or batch?
            # Let's try sending Width/Height and Binning together. 
            # If that fails, we might need logic.
            # Most safe: Set Binning, then Set Size.
            
            # Actually, standard GenICam standard says Width is constrained by Binning.
            # So if we change Binning to 1 (pixels get smaller, sensor "virtual" size gets bigger), 
            # max Width increases. So we can update Width.
            
            # Force order by separate calls if needed. Let's try single batch first, but with thought.
            # If we switch to 1x1, MaxWidth becomes 5536. Current Width is 2768. 2768 is valid in 1x1.
            # So switching Binning to 1 is safe. Then we assume Width stays 2768 (Crop).
            # Then we set Width to 5536.
            
            # If we switch to 2x2, MaxWidth becomes 2768. Current Width is 5536. 
            # If we set Binning=2 while Width=5536, it might error "Value out of range".
            # So for 1->2, we MUST set Width -> 2768 FIRST.
            
            params = []
            
            if factor == 2: # Going to low res
                params.append(Parameter(name='Width', value=val_w))
                params.append(Parameter(name='Height', value=val_h))
                params.append(Parameter(name='BinningHorizontal', value=val_bin))
                params.append(Parameter(name='BinningVertical', value=val_bin))
            else: # Going to high res (1)
                params.append(Parameter(name='BinningHorizontal', value=val_bin))
                params.append(Parameter(name='BinningVertical', value=val_bin))
                params.append(Parameter(name='Width', value=val_w))
                params.append(Parameter(name='Height', value=val_h))

            req.parameters = params
            
            self._node.get_logger().info(f'Switching Binning to {factor}x{factor} ({w}x{h})...')
            
            # Call synchronously-ish (wait for future)
            future = client.call_async(req)
            
            # Wait for result loop (non-blocking spin not possible here)
            start_wait = time.time()
            while not future.done() and time.time() - start_wait < 3.0:
                time.sleep(0.05)
                
            if future.done():
                res = future.result()
                # Check for per-parameter errors?
                successful = True
                for r in res.results:
                    if not r.successful:
                        successful = False
                        self._node.get_logger().error(f"Param Set Failed: {r.reason}")
                
                if successful:
                    self._node.get_logger().info("Camera parameters updated successfully.")
            else:
                self._node.get_logger().warn("Parameter update timed out!")

        except Exception as e:
            self._node.get_logger().error(f'Failed to set binning: {e}')

    @handle_service_errors()
    def measure_mtf_callback(self, request, response):
        """MTF measurement from current camera image."""
        self._node.get_logger().info('MTF measurement service called.')

        original_binning = 2 # Assume we came from 2x2
        switched_resolution = False

        try:
            # 1. Switch to High Resolution (1x1 Binning)
            self._set_camera_binning(1)
            
            # 2. Wait for High-Res Image (Sensor Width > 5000)
            self._node.get_logger().info('Waiting for high-resolution image...')
            start_time = time.time()
            cv_image = None
            
            while time.time() - start_time < 10.0: # 10 seconds timeout
                img = self._get_latest_cv_image()
                if img is not None:
                     if img.shape[1] > 5000:
                        cv_image = img
                        switched_resolution = True
                        self._node.get_logger().info(f'High-res image acquired: {img.shape}')
                        break
                     else:
                        # Debug: Log what we are getting
                        self._node.get_logger().debug(f'Still waiting... current res: {img.shape}')
                
                time.sleep(0.2)
            
            if cv_image is None:
                # If we didn't get high-res, try with whatever we have (maybe switch failed)
                self._node.get_logger().warn('Timeout waiting for high-res image! Using latest avail.')
                cv_image = self._get_latest_cv_image()
            
            if cv_image is None:
                raise ImageProcessingError('No image available')

            pixel_size_um = self._node.get_parameter('pixel_size_um').value
            if not pixel_size_um or pixel_size_um <= 0:
                pixel_size_um = 2.40  # IDS U3-3800CP (Sony IMX183)

            # Important: If we are in 2x2 binning (switch failed), effective pixel size is 2x
            if cv_image.shape[1] < 3000:
                self._node.get_logger().warn('Measuring with low resolution (Binning active)!')
                pixel_size_um *= 2.0
                response.status_message += " [WARNING: Low Res Measurement]"

            # Auto ROI Detection
            edge_rois = []  # List of EdgeROI objects
            roi_list = []   # Legacy list for manual mode
            
            if getattr(request, 'auto_roi', False):
                self._node.get_logger().info('Auto-ROI enabled: Detecting targets...')
                _, bars, squares = RoiDetector.detect_targets(cv_image)
                
                # Priority 1: Squares (use new EdgeROI-based extraction)
                if squares:
                    # Take largest square
                    largest_square = max(squares, key=lambda r: r[1][0] * r[1][1])
                    
                    # Use improved edge extraction with coordinate tracking
                    edge_rois = RoiDetector.create_edge_rois_from_rect(
                        cv_image, largest_square, roi_width=60
                    )
                    
                    # Filter by contrast
                    valid_edges = [e for e in edge_rois if e.is_valid]
                    if valid_edges:
                        edge_rois = valid_edges
                        self._node.get_logger().info(
                            f"Found {len(edge_rois)} valid edges from square "
                            f"(center: {edge_rois[0].parent_center})"
                        )
                    else:
                        self._node.get_logger().warn(
                            f"All {len(edge_rois)} edges have low contrast, trying anyway..."
                        )
                    
                # Priority 2: Bars
                elif bars:
                    # Take largest bar
                    largest_bar = max(bars, key=lambda r: r[1][0] * r[1][1])
                    
                    # Use new EdgeROI extraction for bars too
                    edge_rois = RoiDetector.create_edge_rois_from_rect(
                        cv_image, largest_bar, roi_width=60
                    )
                    
                    if edge_rois:
                        self._node.get_logger().info(
                            f"Found {len(edge_rois)} edges from bar target"
                        )
    
                if not edge_rois:
                    raise ImageProcessingError('Auto-ROI: No targets detected')
            
            else:
                # Manual mode: Interactive selection
                roi, roi_img = self._select_roi_interactive(cv_image)
                if roi is None:
                    raise ImageProcessingError("ROI selection cancelled")
                x, y, w, h = roi
                # Create manual EdgeROI for consistency
                contrast = RoiDetector.calculate_michelson_contrast(roi_img)
                edge_rois = [EdgeROI(
                    image=roi_img,
                    bbox=(x, y, w, h),
                    edge_direction='unknown',
                    edge_name='manual',
                    contrast=contrast,
                    parent_center=(x + w//2, y + h//2)
                )]
    
            # Filter by requested edge (if specified)
            if hasattr(request, 'target_edge') and request.target_edge:
                requested = request.target_edge.lower().strip()
                if requested == "select" or requested == "interactive":
                    # Interactive Candidate Selection - convert EdgeROIs to legacy format
                    roi_list = [{'image': e.image, 'name': f'{e.edge_name.capitalize()} Edge', 'edge_roi': e} 
                                for e in edge_rois]
                    selected = self._select_candidate_interactive(roi_list)
                    if selected and 'edge_roi' in selected:
                        edge_rois = [selected['edge_roi']]
                        self._node.get_logger().info(f"User selected: {selected['name']}")
                    else:
                        raise ImageProcessingError("Interactive selection cancelled")
                elif requested not in ["", "any"]:
                    filtered = [e for e in edge_rois if requested in e.edge_name.lower()]
                    if filtered:
                        edge_rois = filtered
                        self._node.get_logger().info(
                            f"Filtered to '{requested}' edges: {len(edge_rois)} candidates"
                        )
                    else:
                        raise ImageProcessingError(
                            f"Requested edge '{requested}' not found in detected targets"
                        )
    
            # Perform Measurement (Try all edge candidates)
            last_error = "Unknown error"
            
            for edge_roi in edge_rois:
                if edge_roi.contrast < 0.2:
                    self._node.get_logger().warn(
                        f"Low contrast ({edge_roi.contrast:.2f}) for {edge_roi.edge_name} edge"
                    )
                
                config = MTFConfig(pixel_size_um=pixel_size_um)
                
                # Get calibration from valid CameraInfo if available
                camera_matrix = None
                dist_coeffs = None
                
                if self._node.latest_camera_info is not None:
                    try:
                        ci = self._node.latest_camera_info
                        camera_matrix = np.array(ci.k).reshape(3, 3)
                        dist_coeffs = np.array(ci.d)
                        # self._node.get_logger().debug("Using calibration for MTF analysis")
                    except Exception as e:
                        self._node.get_logger().warn(f"Failed to process camera info: {e}")

                analyzer = MTFAnalyzer(config, camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)
                
                result = analyzer.compute_mtf(edge_roi.image)
    
                if result.valid:
                    # Attach edge metadata to result
                    result.edge_name = edge_roi.edge_name
                    result.edge_direction = edge_roi.edge_direction
                    result.contrast = edge_roi.contrast
                    result.roi_bounds = edge_roi.bbox
                    
                    # Success! Return this result
                    response.success = True
                    response.mtf50 = float(result.mtf50)
                    response.mtf20 = float(result.mtf20)
                    response.mtf10 = float(result.mtf10)
                    response.edge_angle = float(result.edge_angle)
                    response.nyquist_frequency = float(result.nyquist_frequency)
                    
                    # Format detailed status message with edge coordinates
                    edge_info = result.format_edge_info()
                    response.status_message = (
                        f"MTF50={response.mtf50:.2f} lp/mm "
                        f"({edge_info}, {result.edge_angle:.1f}°, C:{edge_roi.contrast:.2f})"
                    )
                    
                    self._node.get_logger().info(
                        f"MTF measurement successful: {response.status_message}"
                    )
                    return response
                
                last_error = result.error_msg
            
            # If we get here, no candidate worked
            raise ImageProcessingError(f"MTF failed on all candidates. Last error: {last_error}")
        
        finally:
            # Restore original binning (2x2)
            if switched_resolution:
                self._node.get_logger().info('Restoring Binning 2x2...')
                self._set_camera_binning(original_binning)

        return response

    def _select_candidate_interactive(self, candidates):
        """Shows candidates side-by-side and lets user click to select."""
        # Prepare list of images
        images = []
        for c in candidates:
            if 'image' in c:
                images.append(c['image'])
            elif 'roi' in c and 'source_image' in c: # If we stored source
                 # Should extract roi here if needed, but for now assume edges have 'image'
                 # Bars might need handling. For now, assume edges.
                 pass
            # Fallback: create placeholder if no image
            if 'image' not in c:
                # Try to get latest image and crop
                # This is tricky without passing full image around.
                # Assuming 'image' key is populated for edge candidates.
                images.append(np.zeros((100, 100), dtype=np.uint8)) 

        vis_img, tile_w = RoiDetector.create_debug_visualization(images)
        
        selected_idx = [-1]
        window_name = "Select Target Candidate"

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                if tile_w > 0:
                    idx = x // tile_w
                    if 0 <= idx < len(candidates):
                        selected_idx[0] = idx
                        self.logger.info(f"Selected candidate {idx}: {candidates[idx]['name']}")
                        cv2.destroyWindow(window_name)

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback)
        cv2.imshow(window_name, vis_img)
        
        # Wait until selection or escape
        while selected_idx[0] == -1:
            key = cv2.waitKey(100)
            if key == 27: # ESC
                break
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
                
        cv2.destroyAllWindows()
        
        if selected_idx[0] != -1:
            return candidates[selected_idx[0]]
        return None

    @handle_service_errors()
    def detect_rois_callback(self, request, response):
        """Debug callback to visualize detected ROIs."""
        self._node.get_logger().info('Debugging ROI detection...')
        
        cv_image = self._get_latest_cv_image()
        if cv_image is None:
            raise ImageProcessingError('No image available')
            
        vis_img, bars, squares = RoiDetector.detect_targets(cv_image)
        
        output_dir = self._get_output_dir('debug_rois')
        timestamp = self._get_timestamp()
        
        # 1. Main visualization (Full Image)
        filename_main = str(output_dir / f'rois_full_{timestamp}.jpg')
        cv2.imwrite(filename_main, vis_img)
        
        # 2. Detailed Edge Visualization (if squares found)
        filename_edges = ""
        if squares:
            largest_square = max(squares, key=lambda r: r[1][0] * r[1][1])
            edges = RoiDetector.split_square_into_edges(cv_image, largest_square)
            
            # Unpack tuple (canvas, tile_w)
            vis_edges, _ = RoiDetector.create_debug_visualization(edges)
            
            filename_edges = str(output_dir / f'rois_edges_{timestamp}.jpg')
            cv2.imwrite(filename_edges, vis_edges)
        
        response.success = True
        response.message = f"Detected {len(bars)} bars and {len(squares)} squares. Edges saved."
        response.debug_image_path = filename_edges if filename_edges else filename_main
        response.bars_detected = len(bars)
        response.squares_detected = len(squares)
            
        return response
