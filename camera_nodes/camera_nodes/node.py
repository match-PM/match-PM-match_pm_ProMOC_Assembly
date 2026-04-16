#!/usr/bin/env python3
"""ROS2 runtime node for camera services."""

import time

from cv_bridge import CvBridge
from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import AutoFocus, DetectRois, MeasureMTF, SetExposure
from promoc_core.logging import LogTags, TaggedLogger
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_srvs.srv import Trigger

from .config import declare_camera_parameters, get_camera_param
from .drivers import AravisCameraDriver, CameraDriver, SimulatedCameraDriver
from .services import AutofocusHandler, ExposureHandler, MTFHandler
from .services.image_processing import CameraImageProcessing


class CameraNode(Node):
    """Wire camera driver, subscriptions, and service handlers together."""

    def __init__(self):
        super().__init__("camera_node")

        self.log = TaggedLogger(self.get_logger(), LogTags.CAM)
        declare_camera_parameters(self)

        self.bridge = CvBridge()
        self.use_simulator = self._param_bool("use_simulator", False)
        self.pixel_size_um = self._param_float("pixel_size_um", 2.40)
        self.x_axis_name = self._param_str("x_axis_node_name", "lts300_x_axis")
        self.enable_debug_overlay = self._param_bool("enable_debug_overlay", False)

        mode = "SIMULATOR" if self.use_simulator else "REAL"
        self.log.info(f"Camera node starting in {mode} mode")

        self.camera_driver: CameraDriver = self._create_driver()
        self.camera_driver.connect()

        self.image_processor = CameraImageProcessing(
            self.log,
            pixel_size_um=self.pixel_size_um,
        )
        self.autofocus_handler = AutofocusHandler(self, self.camera_driver)
        self.mtf_handler = MTFHandler(self, self.camera_driver)
        self.exposure_handler = ExposureHandler(self, self.camera_driver)

        self.latest_image_msg = None
        self.latest_camera_info = None
        self.current_axis_position = -1.0
        self._image_count = 0
        self._stream_start_time = time.time()
        self._last_stream_log_time = 0.0

        self.cb_group = ReentrantCallbackGroup()
        self._create_subscriptions()
        self._create_publishers()
        self._create_services()

        self.log.info("Camera node initialized")

    def _param_bool(self, name: str, default: bool) -> bool:
        return bool(get_camera_param(self, name, default))

    def _param_float(self, name: str, default: float) -> float:
        try:
            return float(get_camera_param(self, name, default))
        except (TypeError, ValueError):
            return float(default)

    def _param_str(self, name: str, default: str = "") -> str:
        return str(get_camera_param(self, name, default))

    def _create_driver(self) -> CameraDriver:
        if self.use_simulator:
            self.log.info("Using simulated camera driver")
            return SimulatedCameraDriver(TaggedLogger(self.get_logger(), LogTags.MOCK))

        self.log.info("Using Aravis camera driver")
        return AravisCameraDriver(self, self.log)

    def _create_subscriptions(self):
        self.assembly_image_sub = self.create_subscription(
            Image,
            "/promoc/assembly_camera/stream0/image_raw",
            self.assembly_image_callback,
            10,
        )
        self.axis_pos_sub = self.create_subscription(
            LinearAxisInfo,
            f"/promoc/linear_axis/{self.x_axis_name}/position",
            self.axis_position_callback,
            10,
        )
        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            "/promoc/assembly_camera/stream0/camera_info",
            self.camera_info_callback,
            10,
        )

    def _create_publishers(self):
        self.processed_assembly_pub = self.create_publisher(
            Image,
            "/camera/assembly/processed",
            10,
        )
        self.debug_image_pub = self.create_publisher(Image, "/camera/image_debug", 10)

    def _create_services(self):
        self.select_roi_service = self.create_service(
            Trigger,
            "/promoc/camera/select_roi",
            self.mtf_handler.select_roi_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_service = self.create_service(
            AutoFocus,
            "/promoc/camera/autofocus",
            self.autofocus_handler.autofocus_callback,
            callback_group=self.cb_group,
        )
        self.autofocus_comparison_service = self.create_service(
            AutoFocus,
            "/promoc/camera/autofocus_comparison",
            self.autofocus_handler.autofocus_comparison_callback,
            callback_group=self.cb_group,
        )
        self.mtf_service = self.create_service(
            MeasureMTF,
            "/promoc/camera/measure_mtf",
            self.mtf_handler.measure_mtf_callback,
            callback_group=self.cb_group,
        )
        self.detect_rois_service = self.create_service(
            DetectRois,
            "/promoc/camera/detect_rois",
            self.mtf_handler.detect_rois_callback,
            callback_group=self.cb_group,
        )

        if not self.use_simulator and self.camera_driver.is_connected:
            self.set_exposure_service = self.create_service(
                SetExposure,
                "/promoc/camera/set_exposure",
                self.exposure_handler.manual_set_exposure_callback,
                callback_group=self.cb_group,
            )

    def _log_stream_health(self, msg: Image):
        self._image_count += 1
        now = time.time()
        should_log = (
            self._image_count % 50 == 0
            or now - self._last_stream_log_time > 10.0
        )
        if not should_log   :
            return

        runtime = now - self._stream_start_time
        fps = self._image_count / runtime if runtime > 0 else 0.0
        self.log.debug(
            f"Camera active: {self._image_count} images, "
            f"{fps:.1f} FPS, size={msg.width}x{msg.height}"
        )
        self._last_stream_log_time = now

    def _cache_driver_image(self, msg: Image):
        if not hasattr(self.camera_driver, "set_latest_image"):
            return None

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warning(f"Image conversion failed: {exc}")
            return None

        self.camera_driver.set_latest_image(cv_image)
        return cv_image

    def _publish_debug_image(self, msg: Image, cv_image=None):
        if not self.enable_debug_overlay:
            return

        try:
            if cv_image is None:
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            overlay = self.image_processor.draw_crosshair(cv_image)
            debug_msg = self.bridge.cv2_to_imgmsg(overlay, encoding="bgr8")
            debug_msg.header = msg.header
            self.debug_image_pub.publish(debug_msg)
        except Exception as exc:
            self.log.warning(f"Failed to publish debug image: {exc}")

    def assembly_image_callback(self, msg: Image):
        """Cache the latest image and publish optional debug overlay."""
        self._log_stream_health(msg)
        self.latest_image_msg = msg
        cv_image = self._cache_driver_image(msg)
        self._publish_debug_image(msg, cv_image=cv_image)

    def axis_position_callback(self, msg):
        """Receive and cache axis position from LinearAxisInfo."""
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
        camera_node.camera_driver.disconnect()
        camera_node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
