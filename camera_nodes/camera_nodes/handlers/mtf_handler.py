"""MTF handler for Modulation Transfer Function measurements."""

import cv2
import numpy as np

from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
)
from .base import CallbackBase
from .camera_format_controller import CameraFormatController
from ..algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
from ..algorithms.roi_detection import RoiDetector, EdgeROI
from ..support.mtf_param_mapping import apply_mtf_param_mapping
from promoc_core.error_handling import handle_service_errors

MTF_AVG_SAMPLES = 10
MTF_DEFAULT_PIXEL_SIZE_UM = 2.40
MTF_AUTO_ROI_EDGE_WIDTH = 60
MTF_MIN_EDGE_CONTRAST = 0.2
MTF_SAMPLE_TIMEOUT_S = 1.0


class MTFHandler(CallbackBase):
    """Handler for MTF measurements and ROI selection."""

    def __init__(self, node, camera_driver):
        """Initialize MTF handler and shared camera format controller."""
        super().__init__(node, camera_driver)
        self._camera_format_controller = CameraFormatController(node)

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

        window_name = "Select ROI"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, display_image.shape[1], display_image.shape[0])

        roi = cv2.selectROI(
            window_name, display_image, fromCenter=False, showCrosshair=True
        )
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
        roi_image = cv_image[y : y + h, x : x + w]
        return roi, roi_image

    def _build_mtf_config(
        self,
        pixel_size_um: float,
        min_edge_angle: float,
        max_edge_angle: float,
        auto_roi: bool,
    ) -> MTFConfig:
        """Build MTFConfig from node parameters and profile overrides."""
        config = MTFConfig(
            pixel_size_um=pixel_size_um,
            min_edge_angle=min_edge_angle,
            max_edge_angle=max_edge_angle,
        )

        # Debug export
        debug_dir = self._param_str("mtf.debug_export_dir", "").strip()
        if debug_dir:
            config.debug_export_dir = debug_dir
            prefix = self._param_str("mtf.debug_export_prefix", "").strip()
            if prefix:
                config.debug_export_prefix = prefix
            if self._param_raw("mtf.debug_export_csv", None) is not None:
                config.debug_export_csv = self._param_bool(
                    "mtf.debug_export_csv", config.debug_export_csv
                )
            if self._param_raw("mtf.debug_export_png", None) is not None:
                config.debug_export_png = self._param_bool(
                    "mtf.debug_export_png", config.debug_export_png
                )

        # Centralized declarative parameter mapping
        apply_mtf_param_mapping(config, self._param_raw)

        # Validation-only switch for auto ROI mode
        if self._param_bool("mtf.edge_validation_only_auto", False) and not auto_roi:
            config.edge_validation_mode = "off"

        # Apply profile last (overrides for ease-of-use)
        profile = self._param_str("mtf.profile", "default").strip().lower()
        if profile in ("scientific", "debug"):
            config.derivative_mode = "iso"
            config.apply_derivative_correction = True
            config.apply_angle_correction = True
            config.clip_to_nyquist = True
            config.lsf_window_mode = "peak"
            config.lsf_peak_window_size = 0
            config.edge_validation_mode = "warn"
        if profile == "debug":
            if not config.debug_export_dir:
                debug_root = self._get_output_dir("mtf_debug")
                run_dir = debug_root / self._get_timestamp()
                run_dir.mkdir(parents=True, exist_ok=True)
                config.debug_export_dir = str(run_dir)
            config.debug_export_csv = True
            config.debug_export_png = True
            if config.esf_smooth_mode == "none":
                config.esf_smooth_mode = "sg"
            config.export_dual_curves = True
        if profile not in ("default", "scientific", "debug", ""):
            self._node.get_logger().warn(
                f"Unknown mtf.profile='{profile}', using current configuration."
            )

        return config

    @handle_service_errors()
    def select_roi_callback(self, request, response):
        """Interactive ROI selection with MTF calculation."""
        self._node.get_logger().info("ROI selection service called.")

        if self._node.latest_image_msg is None:
            raise ImageProcessingError("No image received yet")

        cv_image = self._node.bridge.imgmsg_to_cv2(self._node.latest_image_msg, "bgr8")

        roi, roi_image = self._select_roi_interactive(cv_image)
        if roi is None:
            response.success = False
            response.status_message = "ROI selection cancelled."
            return response

        x, y, w, h = roi
        if w <= 0 or h <= 0:
            raise ConfigurationError("Invalid ROI dimensions")

        mtf_results = self._node.image_processor.calculate_mtf_from_roi(roi_image)
        if not mtf_results:
            raise ImageProcessingError("MTF calculation failed")

        output_dir = self._get_output_dir("mtf_messungen")
        output_filename = str(output_dir / f"mtf_{self._get_timestamp()}.csv")
        self._node.image_processor.export_to_csv(mtf_results, output_filename)

        response.success = True
        response.status_message = f"MTF saved to {output_filename}"

        return response

    @handle_service_errors()
    def measure_mtf_callback(self, request, response):
        """MTF measurement from current camera image."""
        self._node.get_logger().info("MTF measurement service called.")
        if self._param_bool("mtf.use_full_frame", True) and not getattr(
            self._node, "use_simulator", False
        ):
            self._node.get_logger().info(
                "MTF capture: switching camera format from cropped ROI to FULL resolution "
                "(crop OFF, fullres ON)."
            )
        restore_state = None

        try:
            # 1. Get latest image and optionally switch camera to full frame for MTF
            cv_image = None
            image_ts_ns = None
            cv_image, image_ts_ns = self._get_latest_cv_image()
            if cv_image is None:
                raise ImageProcessingError("No image available")

            restore_state, switched_image = (
                self._camera_format_controller.switch_to_full_frame_for_mtf(
                    image_ts_ns if image_ts_ns is not None else 0,
                    get_latest_image_fn=self._get_latest_cv_image,
                    wait_for_new_image_fn=self._wait_for_new_image,
                )
            )
            if switched_image is not None:
                cv_image = switched_image

            pixel_size_um = self._param_float(
                "pixel_size_um", MTF_DEFAULT_PIXEL_SIZE_UM
            )
            if not pixel_size_um or pixel_size_um <= 0:
                pixel_size_um = MTF_DEFAULT_PIXEL_SIZE_UM

            min_edge_angle = self._param_float("mtf_min_edge_angle", 2.0)
            max_edge_angle = self._param_float("mtf_max_edge_angle", 10.0)

            # Pass edge angle limits into analyzer (applied per ROI below)

            # Auto ROI Detection
            edge_rois = []  # List of EdgeROI objects
            roi_list = []  # Legacy list for manual mode

            if getattr(request, "auto_roi", False):
                self._node.get_logger().info("Auto-ROI enabled: Detecting targets...")
                _, bars, squares = RoiDetector.detect_targets(cv_image)

                # Priority 1: Squares (use new EdgeROI-based extraction)
                if squares:
                    # Take largest square
                    largest_square = max(squares, key=lambda r: r[1][0] * r[1][1])

                    # Use improved edge extraction with coordinate tracking
                    edge_rois = RoiDetector.create_edge_rois_from_rect(
                        cv_image, largest_square, roi_width=MTF_AUTO_ROI_EDGE_WIDTH
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
                        cv_image, largest_bar, roi_width=MTF_AUTO_ROI_EDGE_WIDTH
                    )

                    if edge_rois:
                        self._node.get_logger().info(
                            f"Found {len(edge_rois)} edges from bar target"
                        )

                if not edge_rois:
                    raise ImageProcessingError("Auto-ROI: No targets detected")

            else:
                # Manual mode: Interactive selection
                roi, roi_img = self._select_roi_interactive(cv_image)
                if roi is None:
                    raise ImageProcessingError("ROI selection cancelled")
                x, y, w, h = roi
                # Create manual EdgeROI for consistency
                contrast = RoiDetector.calculate_michelson_contrast(roi_img)
                edge_rois = [
                    EdgeROI(
                        image=roi_img,
                        bbox=(x, y, w, h),
                        edge_direction="unknown",
                        edge_name="manual",
                        contrast=contrast,
                        parent_center=(x + w // 2, y + h // 2),
                    )
                ]

            # Filter by requested edge (if specified)
            if hasattr(request, "target_edge") and request.target_edge:
                requested = request.target_edge.lower().strip()
                if requested == "select" or requested == "interactive":
                    # Interactive Candidate Selection - convert EdgeROIs to legacy format
                    roi_list = [
                        {
                            "image": e.image,
                            "name": f"{e.edge_name.capitalize()} Edge",
                            "edge_roi": e,
                        }
                        for e in edge_rois
                    ]
                    selected = self._select_candidate_interactive(roi_list)
                    if selected and "edge_roi" in selected:
                        edge_rois = [selected["edge_roi"]]
                        self._node.get_logger().info(
                            f"User selected: {selected['name']}"
                        )
                    else:
                        raise ImageProcessingError("Interactive selection cancelled")
                elif requested not in ["", "any"]:
                    filtered = [
                        e for e in edge_rois if requested in e.edge_name.lower()
                    ]
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
                if edge_roi.contrast < MTF_MIN_EDGE_CONTRAST:
                    self._node.get_logger().warn(
                        f"Low contrast ({edge_roi.contrast:.2f}) for {edge_roi.edge_name} edge"
                    )

                config = self._build_mtf_config(
                    pixel_size_um=pixel_size_um,
                    min_edge_angle=min_edge_angle,
                    max_edge_angle=max_edge_angle,
                    auto_roi=getattr(request, "auto_roi", False),
                )

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
                        self._node.get_logger().warn(
                            f"Failed to process camera info: {e}"
                        )

                analyzer = MTFAnalyzer(
                    config, camera_matrix=camera_matrix, dist_coeffs=dist_coeffs
                )

                debug_label = (
                    f"{edge_roi.edge_name}_{edge_roi.bbox[0]}_{edge_roi.bbox[1]}"
                )
                result = analyzer.compute_mtf(edge_roi.image, debug_label=debug_label)

                if result.valid:
                    if result.warning_msg:
                        self._node.get_logger().warn(
                            f"MTF warning ({edge_roi.edge_name}): {result.warning_msg}"
                        )
                    # --- Averaging Logic ---
                    num_samples = MTF_AVG_SAMPLES
                    valid_samples = [result]

                    if num_samples > 1:
                        self._node.get_logger().info(
                            f"Edge valid. Measuring {num_samples-1} more frames for averaging..."
                        )
                        roi_x, roi_y, roi_w, roi_h = edge_roi.bbox
                        _, last_ts = self._get_latest_cv_image()
                        if last_ts is None:
                            last_ts = 0

                        for _ in range(num_samples - 1):
                            next_img, next_ts = self._wait_for_new_image(
                                int(last_ts),
                                timeout=MTF_SAMPLE_TIMEOUT_S,
                            )
                            if next_img is not None:
                                if next_ts is not None:
                                    last_ts = next_ts
                                # Ensure ROI is within bounds (in case image size changed?? unlikely but safe)
                                if (
                                    roi_y + roi_h <= next_img.shape[0]
                                    and roi_x + roi_w <= next_img.shape[1]
                                ):
                                    crop_img = next_img[
                                        roi_y : roi_y + roi_h, roi_x : roi_x + roi_w
                                    ]
                                    sample_res = analyzer.compute_mtf(crop_img)
                                    if sample_res.valid:
                                        valid_samples.append(sample_res)
                            else:
                                self._node.get_logger().warn(
                                    "Timeout waiting for next image in averaging loop"
                                )

                    # Compute Averages
                    avg_mtf50 = float(np.mean([r.mtf50 for r in valid_samples]))
                    avg_mtf20 = float(np.mean([r.mtf20 for r in valid_samples]))
                    avg_mtf10 = float(np.mean([r.mtf10 for r in valid_samples]))
                    avg_angle = float(np.mean([r.edge_angle for r in valid_samples]))

                    # Attach edge metadata to result (using first result for metadata)
                    result.edge_name = edge_roi.edge_name
                    result.edge_direction = edge_roi.edge_direction
                    result.contrast = edge_roi.contrast
                    result.roi_bounds = edge_roi.bbox

                    # Success! Return this result
                    response.success = True
                    response.mtf50 = avg_mtf50
                    response.mtf20 = avg_mtf20
                    response.mtf10 = avg_mtf10
                    response.edge_angle = avg_angle
                    response.nyquist_frequency = float(result.nyquist_frequency)

                    # Format detailed status message with edge coordinates
                    edge_info = edge_roi.format_coords()
                    response.status_message = (
                        f"MTF50={response.mtf50:.2f} lp/mm (Avg {len(valid_samples)}) "
                        f"({edge_info}, {response.edge_angle:.1f}°, C:{edge_roi.contrast:.2f})"
                    )

                    self._node.get_logger().info(
                        f"MTF measurement successful: {response.status_message}"
                    )
                    return response

                last_error = result.error_msg

            # If we get here, no candidate worked
            raise ImageProcessingError(
                f"MTF failed on all candidates. Last error: {last_error}"
            )

        finally:
            self._camera_format_controller.restore_after_mtf(restore_state)

        return response

    def _select_candidate_interactive(self, candidates):
        """Shows candidates side-by-side and lets user click to select."""
        # Prepare list of images
        images = []
        for c in candidates:
            if "image" in c:
                images.append(c["image"])
            elif "roi" in c and "source_image" in c:  # If we stored source
                # Should extract roi here if needed, but for now assume edges have 'image'
                # Bars might need handling. For now, assume edges.
                pass
            # Fallback: create placeholder if no image
            if "image" not in c:
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
                        self.logger.info(
                            f"Selected candidate {idx}: {candidates[idx]['name']}"
                        )
                        cv2.destroyWindow(window_name)

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback)
        cv2.imshow(window_name, vis_img)

        # Wait until selection or escape
        while selected_idx[0] == -1:
            key = cv2.waitKey(100)
            if key == 27:  # ESC
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
        self._node.get_logger().info("Debugging ROI detection...")

        cv_image, _ = self._get_latest_cv_image()
        if cv_image is None:
            raise ImageProcessingError("No image available")

        vis_img, bars, squares = RoiDetector.detect_targets(cv_image)

        output_dir = self._get_output_dir("debug_rois")
        timestamp = self._get_timestamp()

        # 1. Main visualization (Full Image)
        filename_main = str(output_dir / f"rois_full_{timestamp}.jpg")
        cv2.imwrite(filename_main, vis_img)

        # 2. Detailed Edge Visualization (if squares found)
        filename_edges = ""
        if squares:
            largest_square = max(squares, key=lambda r: r[1][0] * r[1][1])
            edges = RoiDetector.split_square_into_edges(cv_image, largest_square)

            # Unpack tuple (canvas, tile_w)
            vis_edges, _ = RoiDetector.create_debug_visualization(edges)

            filename_edges = str(output_dir / f"rois_edges_{timestamp}.jpg")
            cv2.imwrite(filename_edges, vis_edges)

        response.success = True
        response.message = (
            f"Detected {len(bars)} bars and {len(squares)} squares. Edges saved."
        )
        response.debug_image_path = filename_edges if filename_edges else filename_main
        response.bars_detected = len(bars)
        response.squares_detected = len(squares)

        return response
