#!/usr/bin/env python3
"""
Main ROS2 Node file for the camera_nodes package.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

# Import local modules
from .camera_image_processing import CameraImageProcessing
from .camera_aravis_interface import CameraAravisInterface
from .camera_service_callbacks import CameraServiceCallbacks

# Import service types
from std_srvs.srv import Trigger
from promoc_assembly_interfaces.srv import SetExposure, AutoFocus


class CameraNode(Node):
    """The main camera node, orchestrating all components."""
    
    def __init__(self):
        super().__init__('camera_node')
        
        # Declare and get parameters
        self.declare_parameter('use_simulator', False)
        self.declare_parameter('mtf_csv_path', '')
        self.use_simulator = self.get_parameter('use_simulator').get_parameter_value().bool_value

        # Initialize components
        self.bridge = CvBridge()
        self.image_processor = CameraImageProcessing()
        self.aravis_interface = CameraAravisInterface(self)
        self.service_callbacks = CameraServiceCallbacks(self, self.aravis_interface)
        
        self.latest_image_msg = None
        self.get_logger().info(f"🎥 Camera Node starting in {'SIMULATOR' if self.use_simulator else 'REAL'} mode...")

        # --- Subscribers ---
        self.assembly_image_sub = self.create_subscription(
            Image, '/promoc/assembly_camera/stream0/image_raw', self.assembly_image_callback, 10)
        
        # --- Publishers ---
        self.processed_assembly_pub = self.create_publisher(
            Image, '/camera/assembly/processed', 10)

        # --- Service Providers ---
        self.select_roi_service = self.create_service(
            Trigger, '~/select_roi', self.service_callbacks.select_roi_callback)
        self.autofocus_service = self.create_service(
            AutoFocus, '~/autofocus', self.service_callbacks.autofocus_callback)

        if not self.use_simulator and self.aravis_interface._client is not None:
            self.manual_set_exposure_service = self.create_service(
                SetExposure, '~/set_exposure', self.service_callbacks.manual_set_exposure_callback)

        self.get_logger().info("✅ Camera Node initialized")
    
    def assembly_image_callback(self, msg: Image):
        """Stores the latest image message received from the camera."""
        self.latest_image_msg = msg
        # Processing is now triggered by services, so we just store the image here.
        pass

def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()
    try:
        rclpy.spin(camera_node)
    except KeyboardInterrupt:
        pass
    finally:
        camera_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()