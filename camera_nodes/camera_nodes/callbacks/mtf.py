"""MTF callbacks for Modulation Transfer Function measurements."""

from datetime import datetime
from pathlib import Path
import cv2
import numpy as np

from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
)
from .base import CallbackBase
from ..algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
from ..algorithms.roi_detection import RoiDetector
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

    @handle_service_errors()
    def measure_mtf_callback(self, request, response):
        """MTF measurement from current camera image."""
        self._node.get_logger().info('MTF measurement service called.')

        cv_image = self._get_latest_cv_image()
        if cv_image is None:
            raise ImageProcessingError('No image available')

        pixel_size_um = self._node.get_parameter('pixel_size_um').value
        if not pixel_size_um or pixel_size_um <= 0:
            pixel_size_um = 2.40  # IDS U3-3800CP (Sony IMX183)

        # Auto ROI Detection
        roi_list = []
        if getattr(request, 'auto_roi', False):
            self._node.get_logger().info('Auto-ROI enabled: Detecting targets...')
            _, bars, squares = RoiDetector.detect_targets(cv_image)
            
            # Priority 1: Squares (split into 4 edges)
            if squares:
                # Take largest square
                largest_square = max(squares, key=lambda r: r[1][0] * r[1][1])
                edges = RoiDetector.split_square_into_edges(cv_image, largest_square)
                
                # Try all 4 edges (Top, Right, Bottom, Left)
                edge_names = ['Top', 'Right', 'Bottom', 'Left']
                for i, edge_img in enumerate(edges):
                    roi_list.append({'image': edge_img, 'name': f'Square {edge_names[i]} Edge'})
                
            # Priority 2: Bars
            elif bars:
                # Take largest bar
                largest_bar = max(bars, key=lambda r: r[1][0] * r[1][1])
                # Simple fallback: Use the bounding box of the rotated rect.
                box = cv2.boxPoints(largest_bar)
                x, y, w, h = cv2.boundingRect(box)
                # Clamp to image bounds
                h_img, w_img = cv_image.shape[:2]
                x = max(0, x); y = max(0, y)
                w = min(w, w_img - x); h = min(h, h_img - y)
                
                roi_list.append({'roi': (x, y, w, h), 'name': 'Slanted Bar'})

            if not roi_list:
                raise ImageProcessingError('Auto-ROI: No targets detected')
        
        else:
            # Manual mode: Interactive selection
            # Note: This requires a GUI environment on the host
            roi, roi_img = self._select_roi_interactive(cv_image)
            if roi is None:
                raise ImageProcessingError("ROI selection cancelled")
            roi_list = [{'image': roi_img, 'name': 'Manual ROI'}]

        # Filter by requested edge (if specified)
        if hasattr(request, 'target_edge') and request.target_edge:
            requested = request.target_edge.lower().strip()
            if requested == "select" or requested == "interactive":
                    # Interactive Candidate Selection
                    selected = self._select_candidate_interactive(roi_list)
                    if selected:
                        roi_list = [selected]
                        self._node.get_logger().info(f"User selected target: {selected['name']}")
                    else:
                        raise ImageProcessingError("Interactive selection cancelled")
            elif requested not in ["", "any"]:
                filtered = [t for t in roi_list if requested in t['name'].lower()]
                if filtered:
                    roi_list = filtered
                    self._node.get_logger().info(f"Filtered targets by edge '{requested}': {len(roi_list)} candidates")
                else:
                    raise ImageProcessingError(f"Requested edge '{requested}' not found in detected targets")

        # Perform Measurement (Try all candidates)
        last_error = "Unknown error"
        
        for target in roi_list:
            # Check contrast if image available
            contrast = 0.0
            if 'image' in target:
                contrast = RoiDetector.calculate_michelson_contrast(target['image'])
                if contrast < 0.2:
                    self._node.get_logger().warn(f"Low contrast ({contrast:.2f}) for {target['name']}")
            
            config = MTFConfig(pixel_size_um=pixel_size_um)
            analyzer = MTFAnalyzer(config)
            
            if 'image' in target:
                result = analyzer.compute_mtf(target['image'])
            else:
                result = analyzer.compute_mtf(cv_image, roi=target['roi'])

            if result.valid:
                # Success! Return this result
                response.success = True
                response.mtf50 = float(result.mtf50)
                response.mtf20 = float(result.mtf20)
                response.mtf10 = float(result.mtf10)
                response.edge_angle = float(result.edge_angle)
                response.nyquist_frequency = float(result.nyquist_frequency)
                response.status_message = (
                    f"MTF50={response.mtf50:.2f} lp/mm ({target['name']}, {result.edge_angle:.1f}°, C:{contrast:.2f})"
                )
                return response
            
            last_error = result.error_msg
        
        # If we get here, no candidate worked
        raise ImageProcessingError(f"MTF failed on all candidates. Last error: {last_error}")

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
        response.status_message = f"Detected {len(bars)} bars and {len(squares)} squares. Edges saved."
        response.debug_image_path = filename_edges if filename_edges else filename_main
        response.bars_detected = len(bars)
        response.squares_detected = len(squares)
            
        return response
