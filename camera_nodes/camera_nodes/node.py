#!/usr/bin/env python3
"""ROS2 runtime node for camera services."""

import time

from cv_bridge import CvBridge
from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import AutoFocus, MeasureMTF, SetExposure
from promoc_core.logging import LogTags, TaggedLogger
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

from .config import declare_camera_parameters, get_camera_param
from .drivers import AravisCameraDriver, CameraDriver
from .preview import ros_image_to_bgr8_preview
from .services import AutofocusHandler, ExposureHandler, MTFHandler
from .services.image_processing import CameraImageProcessing


X_AXIS_TOPIC = "/promoc/linear_axis/lts300_x_axis/position"


class CameraNode(Node):
    """Wire camera driver, subscriptions, and service handlers together."""

    def __init__(self):
        super().__init__("camera_node")

        self.log = TaggedLogger(self.get_logger(), LogTags.CAM)
        declare_camera_parameters(self)

        self.bridge = CvBridge()
        self.pixel_size_um = self._param_float("pixel_size_um", 2.40)
        self.enable_debug_overlay = self._param_bool("enable_debug_overlay", False)

        self.log.info("Camera node starting in hardware mode")

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
        self._warned_preview_failures: set[str] = set()

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
            X_AXIS_TOPIC,
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
        self.autofocus_service = self.create_service(
            AutoFocus,
            "/promoc/camera/autofocus",
            self.autofocus_handler.autofocus_callback,
            callback_group=self.cb_group,
        )
        self.mtf_service = self.create_service(
            MeasureMTF,
            "/promoc/camera/measure_mtf",
            self.mtf_handler.measure_mtf_callback,
            callback_group=self.cb_group,
        )
        self.set_exposure_service = self.create_service(
            SetExposure,
            "/promoc/camera/set_exposure",
            self.exposure_handler.manual_set_exposure_callback,
            callback_group=self.cb_group,
        )

    def _warn_once(self, key: str, message: str):
        """Log one warning per repeated preview/debug conversion failure."""
        if key in self._warned_preview_failures:
            return
        self._warned_preview_failures.add(key)
        self.log.warning(message)

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
            try:
                cv_image = ros_image_to_bgr8_preview(msg, self.bridge.imgmsg_to_cv2)
            except Exception as fallback_exc:
                encoding = str(getattr(msg, "encoding", "") or "unknown")
                self._warn_once(
                    f"cache_driver_image:{encoding}",
                    "Image conversion failed for driver cache "
                    f"(encoding={encoding}, direct={exc}, fallback={fallback_exc}).",
                )
                return None

        self.camera_driver.set_latest_image(cv_image)
        return cv_image

    def _publish_debug_image(self, msg: Image, cv_image=None):
        if not self.enable_debug_overlay:
            return

        try:
            if cv_image is None:
                try:
                    cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                except Exception:
                    cv_image = ros_image_to_bgr8_preview(msg, self.bridge.imgmsg_to_cv2)
            overlay = self.image_processor.draw_crosshair(cv_image)
            debug_msg = self.bridge.cv2_to_imgmsg(overlay, encoding="bgr8")
            debug_msg.header = msg.header
            self.debug_image_pub.publish(debug_msg)
        except Exception as exc:
            encoding = str(getattr(msg, "encoding", "") or "unknown")
            self._warn_once(
                f"publish_debug_image:{encoding}",
                f"Failed to publish debug image (encoding={encoding}): {exc}",
            )

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
