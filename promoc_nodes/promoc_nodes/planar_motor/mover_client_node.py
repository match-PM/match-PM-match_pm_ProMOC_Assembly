import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import LinearMotionSi, SixDofMotion, ActivateXbots, LevitationXbots

class MoverClientNode(Node):
    def __init__(self):
        super().__init__('mover_service_node')

        # Create clients for the services
        self.linear_motion_client = self.create_client(LinearMotionSi, '/planar_motor/linear_mover_motion')
        self.six_d_motion_client = self.create_client(SixDofMotion, '/planar_motor/six_d_mover_motion')
        self.activate_xbots_client = self.create_client(ActivateXbots, '/planar_motor/activate_xbots')
        self.levitation_xbots_client = self.create_client(LevitationXbots, '/planar_motor/levitation_xbots')

        # Subscriber for XBotInfo
        self.xbot_position_subscriber = self.create_subscription(XBotInfo, "xbot_info", self.xbot_position_callback, 10)

        # Call the test function to send requests
        self.test_services()


    def wait_for_services(self):
        self.get_logger().info('Waiting for services to be available...')
        self.linear_motion_client.wait_for_service()
        self.six_d_motion_client.wait_for_service()
        self.activate_xbots_client.wait_for_service()
        self.levitation_xbots_client.wait_for_service()
        self.get_logger().info('All services are available!')    

    def send_linear_request(self, xbot_id, x_pos, y_pos, xy_max_speed, xy_max_accl):
        request = LinearMotionSi.Request()
        request.xbot_id = xbot_id
        request.x_pos = x_pos
        request.y_pos = y_pos
        request.xy_max_speed = xy_max_speed
        request.xy_max_accl = xy_max_accl
        future = self.linear_motion_client.call_async(request)
        future.add_done_callback(self.callback)

    def send_six_d_motion_request(self, x_pos, y_pos, z_pos, rx_pos, ry_pos, rz_pos, 
                                  xy_max_speed, xy_max_accl, z_max_speed, rx_max_speed, ry_max_speed, rz_max_speed):
        request = SixDofMotion.Request()
        request.x_pos = x_pos
        request.y_pos = y_pos
        request.z_pos = z_pos
        request.rx_pos = rx_pos
        request.ry_pos = ry_pos
        request.rz_pos = rz_pos
        request.xy_max_speed = xy_max_speed
        request.xy_max_accl = xy_max_accl
        request.z_max_speed = z_max_speed
        request.rx_max_speed = rx_max_speed
        request.ry_max_speed = ry_max_speed
        request.rz_max_speed = rz_max_speed
        future = self.six_d_motion_client.call_async(request)
        future.add_done_callback(self.callback)

    def send_xbot_activation_request(self, xbot_id, activate):
        request = ActivateXbots.Request()
        request.xbot_id = xbot_id
        request.activation_status = activate
        future = self.activate_xbots_client.call_async(request)
        future.add_done_callback(self.callback)

    def send_levitation_request(self, xbot_id, levitate):
        request = LevitationXbots.Request()
        request.xbot_id = xbot_id
        request.levitation = levitate
        future = self.levitation_xbots_client.call_async(request)
        future.add_done_callback(self.callback)

    def callback(self, future):
        try:
            response = future.result()
            self.get_logger().info(f'Service call successful: {response}')
        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")

    def xbot_position_callback(self, msg):
        self.get_logger().info(f'XBot Position: {msg}')


    def test_services(self):
        # 1. Send request for Linear Motion
        self.get_logger().info('Sending Linear Motion Request...')
        self.send_linear_request(xbot_id=1, x_pos=10.0, y_pos=20.0, xy_max_speed=5.0, xy_max_accl=2.0)

        # 2. Send request for Six Degree Motion
        self.get_logger().info('Sending Six-Degree Motion Request...')
        self.send_six_d_motion_request(
            x_pos=10.0, y_pos=20.0, z_pos=30.0,
            rx_pos=0.0, ry_pos=0.0, rz_pos=0.0,
            xy_max_speed=5.0, xy_max_accl=2.0,
            z_max_speed=2.0, rx_max_speed=1.0, ry_max_speed=1.0, rz_max_speed=1.0
        )

        # 3. Send request to activate XBot
        self.get_logger().info('Sending XBot Activation Request...')
        self.send_xbot_activation_request(xbot_id=1, activate=True)

        # 4. Send request for Levitation
        self.get_logger().info('Sending Levitation Request...')
        self.send_levitation_request(xbot_id=1, levitate=True)


def main(args=None):
    rclpy.init(args=args)
    # Create the client node
    move_client = MoverClientNode()
    # Spin the client to handle service responses
    rclpy.spin(move_client)
    # Destroy the node when done
    move_client.destroy_node()
    rclpy.shutdown()    

if __name__ == '__main__':
    main()

