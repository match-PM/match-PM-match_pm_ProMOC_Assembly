#!/usr/bin/env python3
r"""
ROS2 Node for Camera Image Processing and Autofocus.

This module implements the CameraNode, which orchestrates camera operations
like autofocus and MTF measurement.

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
        └── CameraServiceCallbacks → Service business logic (Autofocus, MTF)

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
   - CameraServiceCallbacks for service logic.
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
    ros2 service call /camera_node/autofocus promoc_assembly_interfaces/srv/AutoFocus \
        "{start_position: 0.0, end_position: 30.0, step_size: 1.0}"

    # Measure MTF:
    ros2 service call /camera_node/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF
"""
from cv_bridge import CvBridge
from promoc_assembly_interfaces.srv import AutoFocus, MeasureMTF, SetExposure
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

# Local imports
from .camera_image_processing import CameraImageProcessing
from .camera_service_callbacks import CameraServiceCallbacks

# Driver abstraction
from .drivers import AravisCameraDriver, CameraDriver, SimulatedCameraDriver


class CameraNode(Node):
    """
    Central ROS2 node for camera operations.

    Orchestrates all image processing and camera components.

    Architecture:
    - Phase 1: Load parameters
    - Phase 2: Select and initialize driver (simulator or real)
    - Phase 3: Create components (ImageProcessing, ServiceCallbacks)
    - Phase 4: Register subscriber and publisher
    - Phase 5: Register services (autofocus, MTF, exposure)

    Attributes:
        bridge (CvBridge): ROS-OpenCV converter
        camera_driver (CameraDriver): Camera driver abstraction
        image_processor (CameraImageProcessing): Image processing algorithms
        service_callbacks (CameraServiceCallbacks): Service business logic
        latest_image_msg: Last received image from subscriber
    """

    def __init__(self):
        """
        Initialize the camera node.

        Steps:
        1. Create ROS2 node
        2. Declare and load parameters
        3. Select driver based on use_simulator parameter
        4. Create components (ImageProcessing, ServiceCallbacks)
        5. Register image subscriber
        6. Register services
        """
        super().__init__('camera_node')


        # Phase 1: Load parameters

        self.declare_parameter('use_simulator', False)
        self.declare_parameter('mtf_csv_path', '')
        self.declare_parameter('pixel_size_um', 3.45)
        self.declare_parameter('default_roi_width', 200)
        self.declare_parameter('default_roi_height', 200)
        # Name of z-axis node for autofocus
        self.declare_parameter('z_axis_node_name', 'lts300_z_axis')
        
        # Measurement parameters
        self.declare_parameter('measurement.username', '')

        # Autofocus refinement parameters
        self.declare_parameter('autofocus.refinement_samples', 51)
        self.declare_parameter('autofocus.min_step_mm', 0.01)  # 10um
        self.declare_parameter('autofocus.refinement_shrink_factor', 0.35)
        
        # Measurement conditions for scientific documentation
        self.declare_parameter('measurement_conditions.coaxial_light_voltage', 0.0)
        self.declare_parameter('measurement_conditions.coaxial_light_current', 0.0)
        self.declare_parameter('measurement_conditions.camera_objective', 'unknown')
        self.declare_parameter('measurement_conditions.notes', '')

        self.use_simulator = self.get_parameter(
            'use_simulator').get_parameter_value().bool_value

        self.get_logger().info(
            f"Camera Node starting in {'SIMULATOR' if self.use_simulator else 'REAL'} mode...")


        # Phase 2: Select driver

        self.bridge = CvBridge()
        self.camera_driver: CameraDriver = self._create_driver()

        # Connect to driver
        self.camera_driver.connect()


        # Phase 3: Create components

        self.image_processor = CameraImageProcessing(self.get_logger())
        self.service_callbacks = CameraServiceCallbacks(
            self, self.camera_driver)

        self.latest_image_msg = None


        # Phase 4: Register subscribers/publishers

        self.assembly_image_sub = self.create_subscription(
            Image, '/promoc/assembly_camera/stream0/image_raw', self.assembly_image_callback, 10)

        self.processed_assembly_pub = self.create_publisher(
            Image, '/camera/assembly/processed', 10)


        # Phase 5: Register services

        self.cb_group = ReentrantCallbackGroup()

        self.select_roi_service = self.create_service(
            Trigger,
            '~/select_roi',
            self.service_callbacks.select_roi_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_service = self.create_service(
            AutoFocus,
            '~/autofocus',
            self.service_callbacks.autofocus_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_parabolic_service = self.create_service(
            AutoFocus,
            '~/autofocus_parabolic',
            self.service_callbacks.autofocus_parabolic_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_fast_service = self.create_service(
            AutoFocus,
            '~/autofocus_fast',
            self.service_callbacks.autofocus_fast_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_comparison_service = self.create_service(
            AutoFocus,
            '~/autofocus_comparison_test',
            self.service_callbacks.autofocus_comparison_test_callback,
            callback_group=self.cb_group,
        )
        self.mtf_service = self.create_service(
            MeasureMTF,
            '~/measure_mtf',
            self.service_callbacks.measure_mtf_callback,
            callback_group=self.cb_group,
        )

        # Exposure service only for real hardware
        if not self.use_simulator and self.camera_driver.is_connected:
            self.manual_set_exposure_service = self.create_service(
                SetExposure,
                '~/set_exposure',
                self.service_callbacks.manual_set_exposure_callback,
                callback_group=self.cb_group,
            )

        self.get_logger().info('✓ Camera Node initialized')


    # DRIVER CREATION


    def _create_driver(self) -> CameraDriver:
        """
        Creates the appropriate camera driver based on the 'use_simulator' parameter.

        Returns:
            CameraDriver: An instance of the selected driver (Simulated or Aravis).
        """
        if self.use_simulator:
            self.get_logger().info('📷 Using SimulatedCameraDriver')
            return SimulatedCameraDriver(self.get_logger())
        else:
            self.get_logger().info('📷 Using AravisCameraDriver')
            return AravisCameraDriver(self, self.get_logger())


    # IMAGE CALLBACKS


    def assembly_image_callback(self, msg: Image):
        """
        Stores the latest received camera image.

        Processing is triggered by services, not automatically. This callback
        only stores the image for later access.
        """
        # Enhanced debugging with connection monitoring
        if not hasattr(self, '_image_count'):
            self._image_count = 0
            self._last_log_time = 0.0
            import time
            self._start_time = time.time()
        
        self._image_count += 1
        
        # Log every 50 images or every 10 seconds for connection verification (DEBUG level)
        import time
        current_time = time.time()
        if (self._image_count % 50 == 0) or (current_time - self._last_log_time > 10.0):
            runtime = current_time - self._start_time
            fps = self._image_count / runtime if runtime > 0 else 0
            self.get_logger().debug(
                f"📷 Camera active: {self._image_count} images, "
                f"{fps:.1f} FPS, Size: {msg.width}x{msg.height}"
            )
            self._last_log_time = current_time
        
        self.latest_image_msg = msg

        # For the Aravis driver, pass the image to the driver to be cached.
        if hasattr(self.camera_driver, 'set_latest_image'):
            try:
                cv_image = self.bridge.imgmsg_to_cv2(
                    msg, desired_encoding='bgr8')
                self.camera_driver.set_latest_image(cv_image)
            except Exception as e:
                self.get_logger().warning(
                    f'Image conversion failed: {e}')


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


if __name__ == '__main__':
    main()
