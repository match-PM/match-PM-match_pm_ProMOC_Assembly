#!/usr/bin/env python3
"""ROS2 runtime node for camera services."""

import time
from cv_bridge import CvBridge

from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import (
    AutoFocus,
    AutoFocusROI,
    MeasureMTF,
    SetExposure,
)
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
from .services.camera_format import CameraFormatController
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
        self.camera_image_topic = self._param_str(
            "camera.image_topic",
            "/promoc/promoc_camera/stream0/image_raw",
        )
        self.camera_info_topic = self._param_str(
            "camera.camera_info_topic",
            "/promoc/promoc_camera/stream0/camera_info",
        )

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
        self._startup_capture_logged = False
        self._startup_capture_attempts = 0
        self._startup_capture_max_attempts = 3
        self._format_controller = CameraFormatController(self)

        self.cb_group = ReentrantCallbackGroup()
        self._create_subscriptions()
        self._create_publishers()
        self._create_services()
        self._startup_capture_timer = self.create_timer(
            2.0,
            self._log_startup_capture_state,
        )

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
            self.camera_image_topic,
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
            self.camera_info_topic,
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
        self.autofocus_roi_service = self.create_service(
            AutoFocusROI,
            "/promoc/camera/autofocus_roi",
            self.autofocus_handler.autofocus_roi_callback,
            callback_group=self.cb_group,
        )
        self.mtf_center_service = self.create_service(
            MeasureMTF,
            "/promoc/camera/measure_mtf_center",
            self.mtf_handler.measure_mtf_center_callback,
            callback_group=self.cb_group,
        )
        self.mtf_roi_service = self.create_service(
            MeasureMTF,
            "/promoc/camera/measure_mtf_roi",
            self.mtf_handler.measure_mtf_roi_callback,
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

    def _log_startup_capture_state(self):
        """Log the actual camera capture state once after startup."""
        if self._startup_capture_logged:
            return

        self._startup_capture_attempts += 1
        state = self._format_controller.read_capture_state()
        state_values = dict((state or {}).get("values", {}))
        state_width = int(state_values.get("width", 0) or 0)
        state_height = int(state_values.get("height", 0) or 0)
        if state is None:
            live_width = int(getattr(self.latest_image_msg, "width", 0) or 0)
            live_height = int(getattr(self.latest_image_msg, "height", 0) or 0)
            if (
                live_width > 0
                and live_height > 0
                and self._startup_capture_attempts >= 1
            ):
                expected_width = int(self._param_float("camera.expected_width", 0.0))
                expected_height = int(self._param_float("camera.expected_height", 0.0))
                expected_exposure_us = self._param_float(
                    "camera.default_exposure_us",
                    0.0,
                )
                parts = [
                    "Camera capture readback unavailable via parameter services",
                    f"live_stream={live_width}x{live_height}",
                ]
                if expected_width > 0 and expected_height > 0:
                    parts.append(f"requested={expected_width}x{expected_height}")
                if expected_exposure_us > 0:
                    parts.append(
                        "requested_exp="
                        + self._format_controller._format_exposure_us(
                            expected_exposure_us
                        )
                    )
                self.log.warning(
                    ", ".join(parts)
                    + " [driver does not currently expose Width/Height readback as ROS parameters]"
                )
                self._startup_capture_logged = True
                self._cancel_startup_capture_timer()
                return

            if self._startup_capture_attempts >= self._startup_capture_max_attempts:
                self.log.warning(
                    "Camera capture readback unavailable via parameter services; "
                    "continuing without startup format readback."
                )
                self._startup_capture_logged = True
                self._cancel_startup_capture_timer()
            return

        if state_width <= 0 or state_height <= 0:
            live_width = int(getattr(self.latest_image_msg, "width", 0) or 0)
            live_height = int(getattr(self.latest_image_msg, "height", 0) or 0)
            if (
                live_width > 0
                and live_height > 0
                and self._startup_capture_attempts >= 1
            ):
                expected_width = int(self._param_float("camera.expected_width", 0.0))
                expected_height = int(self._param_float("camera.expected_height", 0.0))
                expected_exposure_us = self._param_float(
                    "camera.default_exposure_us",
                    0.0,
                )
                parts = [
                    "Camera capture readback unavailable via parameter services",
                    f"live_stream={live_width}x{live_height}",
                ]
                if expected_width > 0 and expected_height > 0:
                    parts.append(f"requested={expected_width}x{expected_height}")
                if expected_exposure_us > 0:
                    parts.append(
                        "requested_exp="
                        + self._format_controller._format_exposure_us(
                            expected_exposure_us
                        )
                    )
                self.log.warning(
                    ", ".join(parts)
                    + " [driver does not currently expose Width/Height readback as ROS parameters]"
                )
                self._startup_capture_logged = True
                self._cancel_startup_capture_timer()
                return

            if self._startup_capture_attempts >= self._startup_capture_max_attempts:
                self.log.warning(
                    "Camera capture readback unavailable via parameter services; "
                    "continuing without startup format readback."
                )
                self._startup_capture_logged = True
                self._cancel_startup_capture_timer()
            return

        values = dict(state_values)
        width = int(values.get("width", 0) or 0)
        height = int(values.get("height", 0) or 0)
        expected_width = int(self._param_float("camera.expected_width", 0.0))
        expected_height = int(self._param_float("camera.expected_height", 0.0))
        expected_exposure_us = self._param_float("camera.default_exposure_us", 0.0)
        actual_exposure_us = values.get("exposure_time")

        parts = [
            "Camera capture state: "
            + self._format_controller._format_values(values),
        ]
        if expected_width > 0 and expected_height > 0:
            parts.append(f"requested={expected_width}x{expected_height}")
        if actual_exposure_us is not None and expected_exposure_us > 0:
            parts.append(
                "requested_exp="
                + self._format_controller._format_exposure_us(expected_exposure_us)
            )

        same_geometry = (
            expected_width <= 0
            or expected_height <= 0
            or (width == expected_width and height == expected_height)
        )
        message = ", ".join(parts)
        if same_geometry:
            self.log.info(message)
        else:
            self.log.warning(
                message
                + " [stream geometry differs from requested full-frame target]"
            )

        self._startup_capture_logged = True
        self._cancel_startup_capture_timer()

    def _cancel_startup_capture_timer(self):
        """Stop the one-shot startup capture timer once a final log was emitted."""
        if self._startup_capture_timer is not None:
            self._startup_capture_timer.cancel()
            self._startup_capture_timer = None

    def _log_stream_health(self, msg: Image):
        self._image_count += 1
        now = time.time()
        should_log = self._image_count % 50 == 0 or now - self._last_stream_log_time > 10.0
        if not should_log:
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
    # Autofocus/MTF issue nested service calls while image and axis callbacks
    # are still active; force extra executor threads so these callbacks can
    # make progress instead of deadlocking on synchronous client calls.
    executor = MultiThreadedExecutor(num_threads=4)
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
