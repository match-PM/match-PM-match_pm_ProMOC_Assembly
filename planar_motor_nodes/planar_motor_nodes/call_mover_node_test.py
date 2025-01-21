import rclpy
from rclpy.executors import MultiThreadedExecutor
from promoc_assembly_interfaces.srv import LinearMotionSi, SixDofMotion, ActivateXbots, LevitationXbots
from promoc_assembly_interfaces.msg import XBotInfo
from mover_client_node import MoverClientNode  # Import the existing MoverClientNode class


def main(args=None):
    # Initialize rclpy
    rclpy.init(args=args)

    # Create the client node
    client_node = MoverClientNode()

    # Wait for services to be available
    client_node.linear_motion_client.wait_for_service()
    client_node.six_d_motion_client.wait_for_service()
    client_node.activate_xbots_client.wait_for_service()
    client_node.levitation_xbots_client.wait_for_service()

    # Send requests to all services

    # Test Linear Motion service
    client_node.send_linear_request(xbot_id=1, x_pos=100.0, y_pos=200.0, xy_max_speed=1.0, xy_max_accl=2.0)
    
    # Test Six-Degree Motion service
    client_node.send_six_d_motion_request(
        x_pos=120.0, y_pos=120.0, z_pos=3.0,
        rx_pos=0.5, ry_pos=0.5, rz_pos=0.5,
        xy_max_speed=1.0, xy_max_accl=5.0,
        z_max_speed=1.0, rx_max_speed=1.0, ry_max_speed=1.0, rz_max_speed=1.0
    )
    client_node.send_six_d_motion_request(
        x_pos=120.0, y_pos=120.0, z_pos=1.5,
        rx_pos=0.0, ry_pos=0.0, rz_pos=0.0,
        xy_max_speed=1.0, xy_max_accl=5.0,
        z_max_speed=1.0, rx_max_speed=1.0, ry_max_speed=1.0, rz_max_speed=1.0
    )
    # Test Levitation service
    client_node.send_levitation_request(xbot_id=1, levitate=False)
    client_node.send_levitation_request(xbot_id=1, levitate=True)
    # Test XBot activation
    client_node.send_xbot_activation_request(xbot_id=1, activate=False)
    client_node.send_xbot_activation_request(xbot_id=1, activate=True)
    client_node.send_xbot_activation_request(xbot_id=1, activate=False)

    

    # Use a MultiThreadedExecutor to handle all the async service calls simultaneously
    executor = MultiThreadedExecutor()
    executor.add_node(client_node)

    try:
        executor.spin()  # Keeps the node alive to process service responses
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        client_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
