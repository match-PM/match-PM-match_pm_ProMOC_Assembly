import rclpy
from mover_client_node import MoverClientNode  # Import the MoverClientNode class
from rclpy.node import Node
from planar_motor_interfaces.srv import LinearMotionSi

def main():
    rclpy.init()

    # Create the client node
    move_client = MoverClientNode()


    

    # Example calls to the service with different parameters
    move_client.send_linear_request(xbot_id=1, x_pos=80.0, y_pos=60.0, xy_max_speed=0.5, xy_max_accl=1.0)
    move_client.send_linear_request(xbot_id=1, x_pos=180.0, y_pos=60.0, xy_max_speed=0.5, xy_max_accl=1.0)
    move_client.send_linear_request(xbot_id=1, x_pos=60.0, y_pos=180.0, xy_max_speed=0.5, xy_max_accl=1.0)
    move_client.send_linear_request(xbot_id=1, x_pos=60.0, y_pos=60.0, xy_max_speed=0.5, xy_max_accl=1.0)

    move_client.send_six_d_motion_request(x_pos=80.0, y_pos=60.0, z_pos=2.0,
                                          rx_pos=0.0, ry_pos=0.0, rz_pos=0.0,
                                          xy_max_speed=0.5, xy_max_accl=1.0, 
                                          z_max_speed=1.0, rx_max_speed=0.1, 
                                          ry_max_speed=0.1, rz_max_speed=0.1)

    move_client.send_six_d_motion_request(x_pos=180.0, y_pos=60.0, z_pos=3.0,
                                          rx_pos=0.0, ry_pos=0.0, rz_pos=0.0,
                                          xy_max_speed=0.5, xy_max_accl=1.0, 
                                          z_max_speed=1.0, rx_max_speed=0.1, 
                                          ry_max_speed=0.1, rz_max_speed=0.1)
    
    
    # Spin to handle incoming responses
    rclpy.spin(move_client)

    # Shutdown the ROS 2 client after use
    rclpy.shutdown()

if __name__ == '__main__':
    main()
