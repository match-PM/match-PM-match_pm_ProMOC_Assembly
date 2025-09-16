#!/usr/bin/env python3
"""
Camera Manager Node for ProMOC Assembly System
Integrates with camera_aravis2 via ROS 2 topics/services
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from std_srvs.srv import Trigger
from cv_bridge import CvBridge
import cv2
import numpy as np


class CameraManager(Node):
    """Manages IDS cameras for ProMOC Assembly operations"""
    
    def __init__(self):
        super().__init__('camera_manager')
        
        self.bridge = CvBridge()
        self.get_logger().info("🎥 Camera Manager starting...")
        
        # Subscribe to camera_aravis2 topics
        self.assembly_image_sub = self.create_subscription(
            Image,
            '/assembly_camera/image_raw',  # Topic from camera_aravis2
            self.assembly_image_callback,
            10
        )
        
        self.inspection_image_sub = self.create_subscription(
            Image,
            '/inspection_camera/image_raw',  # Topic from camera_aravis2
            self.inspection_image_callback,
            10
        )
        
        # Publishers for processed images
        self.processed_assembly_pub = self.create_publisher(
            Image,
            '/camera/assembly/processed',
            10
        )
        
        # Services for your ProMOC system
        self.trigger_assembly_capture = self.create_service(
            Trigger,
            'camera/trigger_assembly_capture',
            self.trigger_assembly_capture_callback
        )
        
        # Store latest images
        self.latest_assembly_image = None
        
        self.get_logger().info("✅ Camera Manager initialized")
    
    def assembly_image_callback(self, msg: Image):
        """Process assembly camera images from camera_aravis2"""
        try:
            # Convert ROS Image to OpenCV - NO DIRECT IMPORT NEEDED!
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
            # Store for triggered capture
            self.latest_assembly_image = cv_image.copy()
            
            # Process image
            processed = self.process_assembly_image(cv_image)
            
            # Publish back to ROS
            processed_msg = self.bridge.cv2_to_imgmsg(processed, "bgr8")
            processed_msg.header = msg.header
            self.processed_assembly_pub.publish(processed_msg)
            
        except Exception as e:
            self.get_logger().error(f"❌ Assembly image processing failed: {e}")
    
    def inspection_image_callback(self, msg: Image):
        """Process inspection images"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.get_logger().info("🔍 Received inspection image")
        except Exception as e:
            self.get_logger().error(f"❌ Inspection image processing failed: {e}")
    
    def process_assembly_image(self, image):
        """Assembly-specific image processing"""
        # Example: Edge detection for part positioning
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    def trigger_assembly_capture_callback(self, request, response):
        """Trigger assembly camera capture and return result"""
        try:
            if self.latest_assembly_image is not None:
                self.get_logger().info("📸 Assembly camera capture triggered")
                response.success = True
                response.message = "Assembly camera capture successful"
            else:
                response.success = False
                response.message = "No assembly image available"
        except Exception as e:
            self.get_logger().error(f"❌ Assembly capture failed: {e}")
            response.success = False
            response.message = f"Assembly capture failed: {str(e)}"
        return response


def main(args=None):
    rclpy.init(args=args)
    camera_manager = CameraManager()
    
    try:
        rclpy.spin(camera_manager)
    except KeyboardInterrupt:
        pass
    finally:
        camera_manager.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
