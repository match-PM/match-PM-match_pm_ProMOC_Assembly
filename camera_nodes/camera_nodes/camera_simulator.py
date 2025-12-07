#!/usr/bin/env python3
"""
Kamera-Simulator Node fuer Test und Entwicklung.

Dieses Modul stellt eine eigenstaendige ROS2-Node bereit, die
den SimulatedCameraDriver verwendet, um synthetische Bilder
zu publizieren.

Hinweis:
    Die Bildgenerierung erfolgt ueber SimulatedCameraDriver in
    drivers/simulated_camera_driver.py - KEINE Code-Duplizierung!

Verwendung:
    ros2 run camera_nodes camera_simulator

Topics:
    Publiziert: /assembly_camera/image_raw (sensor_msgs/Image)
    Abonniert: /promoc_assembly/lts300_x_axis/position (LinearAxisInfo)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from promoc_assembly_interfaces.msg import LinearAxisInfo
from .drivers import SimulatedCameraDriver


class CameraSimulator(Node):
    """Kamera-Simulator Node fuer Autofokus-Tests."""

    def __init__(self):
        super().__init__('camera_simulator')

        # Treiber erstellen (wiederverwendet Code aus drivers/)
        self.driver = SimulatedCameraDriver(self.get_logger())
        self.driver.connect()

        # ROS2-Kommunikation
        self.bridge = CvBridge()

        self.publisher = self.create_publisher(
            Image, '/assembly_camera/image_raw', 10)

        self.subscription = self.create_subscription(
            LinearAxisInfo,
            '/promoc_assembly/lts300_x_axis/position',
            self.position_callback, 10)

        # Timer fuer Bild-Publikation (10 Hz)
        self.timer = self.create_timer(0.1, self.timer_callback)

        self.get_logger().info("Camera Simulator gestartet")

    def position_callback(self, msg):
        """Aktualisiert Fokusposition im Treiber."""
        self.driver.set_focus_position(msg.axis_position)

    def timer_callback(self):
        """Holt Bild vom Treiber und publiziert es."""
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


if __name__ == '__main__':
    main()
