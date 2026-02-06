#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import matplotlib.pyplot as plt
import time
import os
from typing import List, Tuple

from promoc_assembly_interfaces.srv import MoveAbsolute, GetOperationStatus
from verification.algorithms.image_metrics import ImageMetrics

class MTFVerificationNode(Node):
    def __init__(self):
        super().__init__('mtf_verification_node')
        
        # Parameters
        self.declare_parameter('axis_name', 'lts300_x_axis')
        self.declare_parameter('start_pos', 250.0)
        self.declare_parameter('end_pos', 300.0)
        self.declare_parameter('step_size', 1.0)
        self.declare_parameter('settle_time', 0.5)
        self.declare_parameter('camera_topic', '/promoc/assembly_camera/stream0/image_raw')
        self.declare_parameter('peak_shift_tolerance', 2.0) # mm
        
        self.axis_name = self.get_parameter('axis_name').value
        self.camera_topic = self.get_parameter('camera_topic').value
        
        # Clients
        self.cb_group = ReentrantCallbackGroup()
        self.move_client = self.create_client(MoveAbsolute, f'/{self.axis_name}/move_absolute', callback_group=self.cb_group)
        self.status_client = self.create_client(GetOperationStatus, f'/{self.axis_name}/get_operation_status', callback_group=self.cb_group)
        
        # Subscription
        self.bridge = CvBridge()
        self.latest_image = None
        self.image_sub = self.create_subscription(
            Image, 
            self.camera_topic, 
            self.image_callback, 
            10,
            callback_group=self.cb_group
        )
        
        self.get_logger().info('MTF Verification Node Initialized')

    def image_callback(self, msg):
        self.latest_image = msg

    def wait_for_services(self):
        self.get_logger().info('Waiting for services...')
        if not self.move_client.wait_for_service(timeout_sec=5.0):
             self.get_logger().error('Move service not available')
             return False
        if not self.status_client.wait_for_service(timeout_sec=5.0):
             self.get_logger().error('Status service not available')
             return False
        return True

    def get_fresh_image(self, timeout=2.0) -> np.ndarray:
        start_ts = time.time()
        # Simple logic: clear latest, wait for new
        self.latest_image = None
        while time.time() - start_ts < timeout:
            if self.latest_image is not None:
                try:
                    cv_img = self.bridge.imgmsg_to_cv2(self.latest_image, desired_encoding='bgr8')
                    return cv_img
                except Exception as e:
                    self.get_logger().error(f'CV Bridge error: {e}')
                    return None
            time.sleep(0.01)
        return None

    def move_to_and_wait(self, pos: float) -> bool:
        req = MoveAbsolute.Request()
        req.axis_position = float(pos)
        future = self.move_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        
        if not future.result() or not future.result().success:
            self.get_logger().error(f'Failed to move to {pos}')
            return False
            
        # Wait for idle
        while True:
            stat_future = self.status_client.call_async(GetOperationStatus.Request())
            rclpy.spin_until_future_complete(self, stat_future)
            res = stat_future.result()
            if res and res.operation_status == 'idle':
                break
            time.sleep(0.1)
        
        return True

    def run_scan(self):
        if not self.wait_for_services():
            return

        start_pos = self.get_parameter('start_pos').value
        end_pos = self.get_parameter('end_pos').value
        step_size = self.get_parameter('step_size').value
        settle_time = self.get_parameter('settle_time').value
        
        positions = np.arange(start_pos, end_pos + step_size, step_size)
        
        results_pos = []
        results_tenengrad = []
        results_mtf = []
        
        self.get_logger().info(f'Starting scan from {start_pos} to {end_pos} (step {step_size})')
        
        for pos in positions:
            self.get_logger().info(f'Moving to Z={pos:.2f}...')
            if not self.move_to_and_wait(pos):
                break
            
            time.sleep(settle_time)
            
            img = self.get_fresh_image()
            if img is None:
                self.get_logger().warn(f'No image at Z={pos}')
                continue
                
            # Calc Metrics
            tenengrad = ImageMetrics.calculate_tenengrad(img)
            mtf_score, angle = ImageMetrics.calculate_mtf_proxy(img)
            
            self.get_logger().info(f'  Z={pos:.2f}: Tenengrad={tenengrad:.1f}, MTF={mtf_score:.2f}, Angle={angle:.1f}°')
            
            results_pos.append(pos)
            results_tenengrad.append(tenengrad)
            results_mtf.append(mtf_score)
            
        self.analyze_and_report(results_pos, results_tenengrad, results_mtf)

    def analyze_and_report(self, pos, tenengrad, mtf):
        if not pos:
            return

        pos = np.array(pos)
        ten = np.array(tenengrad)
        mtf = np.array(mtf)
        
        # Normalize
        ten_norm = (ten - ten.min()) / (ten.max() - ten.min() + 1e-9)
        mtf_norm = (mtf - mtf.min()) / (mtf.max() - mtf.min() + 1e-9)
        
        # Find Peaks
        idx_ten = np.argmax(ten_norm)
        idx_mtf = np.argmax(mtf_norm)
        
        peak_ten = pos[idx_ten]
        peak_mtf = pos[idx_mtf]
        
        shift = peak_ten - peak_mtf
        tolerance = self.get_parameter('peak_shift_tolerance').value
        
        self.get_logger().info('='*40)
        self.get_logger().info(f'Peak Analysis:')
        self.get_logger().info(f'  AF Peak (Tenengrad): {peak_ten:.3f} mm')
        self.get_logger().info(f'  MTF Peak (Proxy):    {peak_mtf:.3f} mm')
        self.get_logger().info(f'  Shift:               {shift:.3f} mm')
        
        if abs(shift) > tolerance:
            self.get_logger().error(f'  [FAIL] Shift > {tolerance} mm')
        else:
            self.get_logger().info(f'  [PASS] Shift <= {tolerance} mm')
        self.get_logger().info('='*40)
        
        # Plot
        plt.figure(figsize=(10, 6))
        plt.plot(pos, ten_norm, label='Focus Metric (Tenengrad)', marker='o', linestyle='--')
        plt.plot(pos, mtf_norm, label='Quality Metric (MTF Proxy)', marker='x', linestyle='-')
        plt.axvline(peak_ten, color='b', linestyle=':', alpha=0.5, label=f'AF Peak {peak_ten:.2f}')
        plt.axvline(peak_mtf, color='orange', linestyle=':', alpha=0.5, label=f'MTF Peak {peak_mtf:.2f}')
        
        plt.title(f'AF vs MTF Peak Verification (Shift: {shift:.2f}mm)')
        plt.xlabel('Z Position [mm]')
        plt.ylabel('Normalized Score')
        plt.legend()
        plt.grid(True)
        
        output_file = 'verification_result.png'
        plt.savefig(output_file)
        self.get_logger().info(f'Plot saved to {os.path.abspath(output_file)}')

def main(args=None):
    rclpy.init(args=args)
    node = MTFVerificationNode()
    try:
        node.run_scan()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
