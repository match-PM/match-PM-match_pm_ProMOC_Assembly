#!/usr/bin/env python3
r"""
ROS2 Node for Camera Image Processing and Autofocus.

This module implements the CameraNode, which orchestrates camera operations
like autofocus and MTF measurement.

Canonical entry point for the `camera_nodes` runtime package.

Architecture Overview:
======================
The node follows a dependency injection pattern for flexibility:

    CameraNode (Orchestrator)
        │
        ├── CameraDriver (Abstraction)
        │     ├── AravisCameraDriver  → Real camera via camera_aravis2
        │     └── SimulatedCameraDriver → Simulator for testing
        │
        ├── CameraImageProcessing  → Image processing algorithms (MTF)
        └── CameraServiceHandlers → Service business logic (Autofocus, MTF, Exposure)

Driver Selection:
=================
The active driver is chosen via a ROS parameter:
    use_simulator = True  → SimulatedCameraDriver
    use_simulator = False → AravisCameraDriver

Core Features:
==============
1. Autofocus:
   - Hybrid algorithm: Coarse search + multi-level refinement.
   - Controls a Z-axis for focus optimization.
   - Uses the Tenengrad sharpness metric.

2. MTF Measurement:
   - Implements the Slanted Edge Method (ISO 12233).
   - Allows ROI selection for the measurement area.
   - Exports results to a CSV file.

3. Exposure Control:
   - Manual setting of camera exposure time.
   - Communicates with the underlying camera_aravis2 driver.

Startup Sequence:
=================
1. Load parameters (e.g., use_simulator, pixel_size_um).
2. Select the appropriate driver based on the 'use_simulator' parameter.
3. Instantiate components:
   - CameraDriver (Simulated or Aravis)
   - CameraImageProcessing for algorithms.
   - CameraServiceHandlers for service logic.
4. Create a subscriber for the raw camera image stream.
5. Register services (autofocus, measure_mtf, select_roi, etc.).

Usage:
======
    # With a real camera:
    ros2 run camera_nodes camera_node

    # With the simulator:
    ros2 run camera_nodes camera_node --ros-args -p use_simulator:=true

Example Service Calls:
======================
    # Perform autofocus:
    ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus \
        "{start_position: 0.0, end_position: 30.0, focus_mode: 0}"

    # Measure MTF:
    ros2 service call /promoc/camera/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF
"""

from cv_bridge import CvBridge
from promoc_assembly_interfaces.srv import (
    AutoFocus,
    MeasureMTF,
    SetExposure,
    DetectRois,
)
from promoc_assembly_interfaces.msg import LinearAxisInfo
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from std_srvs.srv import Trigger

# Local imports
from .domain.logic import CameraImageProcessing
from .config import (
    declare_camera_parameters,
    load_camera_runtime_config,
)
from .services import CameraServiceHandlers

# Driver abstraction
from .drivers import AravisCameraDriver, CameraDriver, SimulatedCameraDriver

from promoc_core.logging import TaggedLogger, LogTags


class CameraNode(Node):
    """
    Central ROS2 node for camera operations.

    Orchestrates all image processing and camera components.

    Architecture:
    - Phase 1: Load parameters
    - Phase 2: Select and initialize driver (simulator or real)
    - Phase 3: Create components (ImageProcessing, ServiceHandlers)
    - Phase 4: Register subscriber and publisher
    - Phase 5: Register services (autofocus, MTF, exposure)

    Attributes:
        bridge (CvBridge): ROS-OpenCV converter
        camera_driver (CameraDriver): Camera driver abstraction
        image_processor (CameraImageProcessing): Image processing algorithms
        service_handlers (CameraServiceHandlers): Service business logic
        latest_image_msg: Last received image from subscriber
    """

    def __init__(self):
        """
        Initialize the camera node.

        Steps:
        1. Create ROS2 node
        2. Declare and load parameters
        3. Select driver based on use_simulator parameter
        4. Create components (ImageProcessing, ServiceHandlers)
        5. Register image subscriber
        6. Register services
        """
        super().__init__("camera_node")

        # Setup TaggedLogger for this node
        self.log = TaggedLogger(self.get_logger(), LogTags.CAM)

        # Phase 1: Load parameters via centralized declaration/typed loader
        declare_camera_parameters(self)
        self.runtime_config = load_camera_runtime_config(self)
        self.use_simulator = self.runtime_config.core.use_simulator

        self.log.info(
            f"Camera Node starting in {'SIMULATOR' if self.use_simulator else 'REAL'} mode..."
        )

        # Phase 2: Select driver

        self.bridge = CvBridge()
        self.camera_driver: CameraDriver = self._create_driver()

        # Connect to driver
        self.camera_driver.connect()

        # Phase 3: Create components

        self.image_processor = CameraImageProcessing(
            self.log,
            pixel_size_um=self.runtime_config.core.pixel_size_um,
        )
        self.service_handlers = CameraServiceHandlers(self, self.camera_driver)

        self.latest_image_msg = None
        self.latest_camera_info = None
        self.current_axis_position = -1.0

        # Phase 4: Register subscribers/publishers

        self.assembly_image_sub = self.create_subscription(
            Image,
            "/promoc/assembly_camera/stream0/image_raw",
            self.assembly_image_callback,
            10,
        )

        axis_name = self.runtime_config.core.x_axis_node_name
        self.axis_pos_sub = self.create_subscription(
            LinearAxisInfo,
            f"/promoc/linear_axis/{axis_name}/position",
            self.axis_position_callback,
            10,
        )

        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            "/promoc/assembly_camera/stream0/camera_info",
            self.camera_info_callback,
            10,
        )

        self.processed_assembly_pub = self.create_publisher(
            Image, "/camera/assembly/processed", 10
        )

        # Debug image publisher with crosshair overlay
        self.debug_image_pub = self.create_publisher(Image, "/camera/image_debug", 10)

        # Phase 5: Register services

        self.cb_group = ReentrantCallbackGroup()

        self.select_roi_service = self.create_service(
            Trigger,
            "/promoc/camera/select_roi",
            self.service_handlers.mtf.select_roi_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_service = self.create_service(
            AutoFocus,
            "/promoc/camera/autofocus",
            self.service_handlers.autofocus.autofocus_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_comparison_service = self.create_service(
            AutoFocus,
            "/promoc/camera/autofocus_comparison",
            self.service_handlers.autofocus.autofocus_comparison_callback,
            callback_group=self.cb_group,
        )
        self.mtf_service = self.create_service(
            MeasureMTF,
            "/promoc/camera/measure_mtf",
            self.service_handlers.mtf.measure_mtf_callback,
            callback_group=self.cb_group,
        )
        self.detect_rois_service = self.create_service(
            DetectRois,
            "/promoc/camera/detect_rois",
            self.service_handlers.mtf.detect_rois_callback,
            callback_group=self.cb_group,
        )

        # Exposure service only for real hardware
        if not self.use_simulator and self.camera_driver.is_connected:
            self.set_exposure_service = self.create_service(
                SetExposure,
                "/promoc/camera/set_exposure",
                self.service_handlers.exposure.manual_set_exposure_callback,
                callback_group=self.cb_group,
            )

        self.log.info("Camera Node initialized successfully")

    # DRIVER CREATION

    def _create_driver(self) -> CameraDriver:
        """
        Creates the appropriate camera driver based on the 'use_simulator' parameter.

        Returns:
            CameraDriver: An instance of the selected driver (Simulated or Aravis).
        """
        if self.use_simulator:
            self.log.info("Using SimulatedCameraDriver")
            return SimulatedCameraDriver(TaggedLogger(self.get_logger(), LogTags.MOCK))
        self.log.info("Using AravisCameraDriver")
        return AravisCameraDriver(self, self.log)

    # IMAGE CALLBACKS

    def assembly_image_callback(self, msg: Image):
        """
        Stores the latest received camera image.

        Processing is triggered by services, not automatically. This callback
        only stores the image for later access.
        """
        # Enhanced debugging with connection monitoring
        if not hasattr(self, "_image_count"):
            self._image_count = 0
            self._last_log_time = 0.0
            import time

            self._start_time = time.time()

        self._image_count += 1

        # Log every 50 images or every 10 seconds for connection health checks (DEBUG level)
        import time

        current_time = time.time()
        if (self._image_count % 50 == 0) or (current_time - self._last_log_time > 10.0):
            runtime = current_time - self._start_time
            fps = self._image_count / runtime if runtime > 0 else 0
            self.log.debug(
                f"Camera active: {self._image_count} images, "
                f"{fps:.1f} FPS, Size: {msg.width}x{msg.height}"
            )
            self._last_log_time = current_time

        self.latest_image_msg = msg

        # Pass the image to the driver for caching (used by Aravis driver)
        if hasattr(self.camera_driver, "set_latest_image"):
            try:
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                self.camera_driver.set_latest_image(cv_image)
            except Exception as e:
                self.get_logger().warning(f"Image conversion failed: {e}")

        # Publish debug image with crosshair overlay if enabled
        if self.runtime_config.core.enable_debug_overlay:
            try:
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                cv_image_with_crosshair = self.image_processor.draw_crosshair(cv_image)
                debug_msg = self.bridge.cv2_to_imgmsg(
                    cv_image_with_crosshair, encoding="bgr8"
                )
                debug_msg.header = msg.header  # Preserve timestamp and frame_id
                self.debug_image_pub.publish(debug_msg)
            except Exception as e:
                self.log.warning(f"Failed to publish debug image: {e}")

    def axis_position_callback(self, msg):
        """Receive and cache axis position from canonical LinearAxisInfo topic."""
        if hasattr(msg, "axis_position"):
            self.current_axis_position = msg.axis_position
            return
        self.log.warning(f"Unknown axis position message type: {type(msg)}")

    def camera_info_callback(self, msg: CameraInfo):
        """Receive and cache camera calibration info."""
        self.latest_camera_info = msg


def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()
    executor = MultiThreadedExecutor()
    executor.add_node(camera_node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        camera_node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass  # Already shut down


if __name__ == "__main__":
    main()
