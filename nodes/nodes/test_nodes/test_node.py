import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.msg import Test

class TestNode(Node):
    def __init__(self):
        super().__init__('test_node')
        self.get_logger().info("Planar Motor Node gestartet")
        # Create the publisher
        self.publisher = self.create_publisher(Test, 'test_topic', 10)

        # Create a timer to publish messages periodically
        self.timer = self.create_timer(1.0, self.publish_message)

        # Initialize a counter for demonstration purposes
        self.counter = 0


    def publish_message(self):
        # Create a new Test message
        msg = Test()
        msg.message = f"Test message {self.counter}"
        
        # Publish the message
        self.publisher.publish(msg)
        
        # Log the published message
        self.get_logger().info(f'Publishing: "{msg.message}"')
        
        # Increment the counter
        self.counter += 1


def main():
    rclpy.init()
    node = TestNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()