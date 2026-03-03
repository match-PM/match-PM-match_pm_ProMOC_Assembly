#!/usr/bin/env python3
"""
Camera Simulator Node for Testing and Development.

This module provides a standalone ROS2 node that uses the
`SimulatedCameraDriver` to publish synthetic camera images.

Note:
    Image generation is handled by `SimulatedCameraDriver` in
    `drivers/simulated_camera_driver.py` to avoid code duplication.

Usage:
    ros2 run camera_nodes camera_simulator

Topics:
    - Publishes: /promoc/assembly_camera/stream0/image_raw (sensor_msgs/Image)
    - Subscribes: /promoc/linear_axis/lts300_x_axis/position (LinearAxisInfo)
"""

from cv_bridge import CvBridge
from promoc_assembly_interfaces.msg import LinearAxisInfo
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

from .drivers import SimulatedCameraDriver


class CameraSimulator(Node):
    """Camera simulator node for autofocus testing."""

    def __init__(self):
        super().__init__("camera_simulator")

        # Create the driver (reusing code from drivers/)
        self.driver = SimulatedCameraDriver(self.get_logger())
        self.driver.connect()

        # ROS2 Communication
        self.bridge = CvBridge()

        self.publisher = self.create_publisher(
            Image, "/promoc/assembly_camera/stream0/image_raw", 10
        )

        self.subscription = self.create_subscription(
            LinearAxisInfo,
            "/promoc/linear_axis/lts300_x_axis/position",
            self.position_callback,
            10,
        )
        self.subscription_legacy = self.create_subscription(
            LinearAxisInfo,
            "/promoc_assembly/lts300_x_axis/position",
            self.position_callback_legacy,
            10,
        )

        # Timer for image publication (10 Hz)
        self.timer = self.create_timer(0.1, self.timer_callback)

        self.get_logger().info("Camera Simulator started")

    def position_callback(self, msg):
        """Updates the focus position in the driver."""
        self.driver.set_focus_position(msg.axis_position)

    def position_callback_legacy(self, msg):
        """Release N compatibility for legacy linear-axis topic."""
        if not hasattr(self, "_legacy_axis_topic_warned"):
            self._legacy_axis_topic_warned = False
        if not self._legacy_axis_topic_warned:
            self.get_logger().warning(
                "Deprecated topic '/promoc_assembly/lts300_x_axis/position' received. "
                "Use '/promoc/linear_axis/lts300_x_axis/position' instead."
            )
            self._legacy_axis_topic_warned = True
        self.position_callback(msg)

    def timer_callback(self):
        """Gets an image from the driver and publishes it."""
        image = self.driver.capture_image()
        if image is None:
            return

        ros_image = self.bridge.cv2_to_imgmsg(image, "bgr8")
        ros_image.header.stamp = self.get_clock().now().to_msg()
        ros_image.header.frame_id = "assembly_camera_frame"
        self.publisher.publish(ros_image)


def main(args=None):
    rclpy.init(args=args)
    camera_simulator = CameraSimulator()
    try:
        rclpy.spin(camera_simulator)
    except KeyboardInterrupt:
        pass
    finally:
        camera_simulator.driver.disconnect()
        camera_simulator.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
