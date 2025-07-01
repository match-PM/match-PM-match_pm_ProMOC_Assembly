#!/usr/bin/env python3
"""
Quick test script to check the XBot position publisher.
"""

import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.msg import XBotInfo

class TestSubscriber(Node):
    def __init__(self):
        super().__init__('test_xbot_subscriber')
        
        self.subscription = self.create_subscription(
            XBotInfo,
            '/xbot_position',
            self.xbot_callback,
            10
        )
        
        self.get_logger().info("🔄 Listening for XBot position messages...")
        
    def xbot_callback(self, msg):
        self.get_logger().info(
            f"📍 XBot Position: x={msg.x_pos:.3f}, y={msg.y_pos:.3f}, z={msg.z_pos:.3f}, "
            f"rx={msg.rx_pos:.3f}, ry={msg.ry_pos:.3f}, rz={msg.rz_pos:.3f}, "
            f"state={msg.xbot_state}"
        )

def main(args=None):
    rclpy.init(args=args)
    
    test_subscriber = TestSubscriber()
    
    try:
        rclpy.spin(test_subscriber)
    except KeyboardInterrupt:
        pass
    finally:
        test_subscriber.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
