#!/usr/bin/env python3
"""
Node to simulate a camera by repeatedly publishing a generated test image.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
from promoc_assembly_interfaces.msg import LinearAxisInfo

class CameraSimulator(Node):
    """ Publishes a synthetically generated image for testing purposes. """

    def __init__(self):
        super().__init__('camera_simulator')
        self.publisher = self.create_publisher(Image, '/assembly_camera/image_raw', 10)
        self.bridge = CvBridge()
        
        self.focal_plane_position = 15.0
        self.current_axis_position = 0.0
        
        self.subscription = self.create_subscription(
            LinearAxisInfo,
            '/promoc_assembly/lts300_x_axis/position',
            self.position_callback,
            10)
        
        # Create a timer to publish the image at 10 Hz
        timer_period = 0.1  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        self.get_logger().info("📷 Camera Simulator started.")
        self.get_logger().info("Publishing a synthetic slanted-edge image on /assembly_camera/image_raw")

    def position_callback(self, msg):
        self.current_axis_position = msg.axis_position

    def _generate_slanted_edge_image(self, width, height, blur_amount):
        """Creates a synthetic grayscale image with a slanted white box."""
        image = np.zeros((height, width), dtype=np.uint8)
        
        # Define a white rectangle to be rotated
        rect_width, rect_height = 200, 400
        box_coords = np.array([
            [-rect_width / 2, -rect_height / 2],
            [rect_width / 2, -rect_height / 2],
            [rect_width / 2, rect_height / 2],
            [-rect_width / 2, rect_height / 2]
        ])

        # Image center
        center_x, center_y = width // 2, height // 2

        # Create rotation matrix for 5 degrees
        M = cv2.getRotationMatrix2D((0, 0), 5, 1.0)

        # Rotate the coordinates
        rotated_coords = box_coords @ M[:, :2].T

        # Shift the rotated coordinates to the image center
        rotated_coords[:, 0] += center_x
        rotated_coords[:, 1] += center_y

        # Fill the rotated rectangle with white
        cv2.fillConvexPoly(image, np.int32(rotated_coords), 255)

        if blur_amount > 0:
            kernel_size = int(blur_amount) * 2 + 1
            image = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

        # Convert to BGR for compatibility, as many ROS tools expect color
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    def timer_callback(self):
        """Called by the timer to publish one image frame."""
        blur_amount = abs(self.current_axis_position - self.focal_plane_position)
        
        # Clamp blur amount for realistic simulation
        blur_amount = min(blur_amount, 10)

        test_image = self._generate_slanted_edge_image(640, 480, blur_amount)

        # Convert the OpenCV image to a ROS Image message
        ros_image = self.bridge.cv2_to_imgmsg(test_image, "bgr8")
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
        camera_simulator.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()