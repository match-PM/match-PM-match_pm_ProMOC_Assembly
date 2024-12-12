import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool  # If your service has a different type, adjust accordingly

from pmclib import system_commands as sys   # PMC System related commands
from pmclib import xbot_commands as bot     # PMC Mover related commands
from pmclib import pmc_types                # PMC API Types


from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import LinearMotionSi
from promoc_assembly_interfaces.srv import SixDofMotion
from promoc_assembly_interfaces.srv import ActivateXbots
from promoc_assembly_interfaces.srv import LevitationXbots

import time

class MoverClientNode(Node):
    def __init__(self):
        super().__init__('mover_service_node')


       # Create clients
        self.linear_motion_client = self.create_client(LinearMotionSi, 'linear_mover_motion')
        self.six_d_motion_client = self.create_client(SixDofMotion, 'six_d_mover_motion')

        self.xbot_postion_subscriber = self.create_subscription(XBotInfo,"xbot_info",self.xbot_postion_callback,10)

        # Wait for the services to be available
        try:
            while not self.linear_motion_client.wait_for_service(timeout_sec=1.0) or not self.six_d_motion_client.wait_for_service(timeout_sec=1.0):
                self.get_logger().info('One or more services not available, waiting...')
            
            self.get_logger().info('Both services available, ready to send requests')

        except Exception as e:
            self.get_logger().error(f'Error while waiting for services: {e}')

    def send_linear_request(self, xbot_id, x_pos, y_pos, xy_max_speed, xy_max_accl):
        # Create a request object (replace with your actual request fields)
        
        request = LinearMotionSi.Request()
        request.xbot_id = xbot_id
        request.x_pos = x_pos
        request.y_pos = y_pos
        request.xy_max_speed = xy_max_speed
        request.xy_max_accl = xy_max_accl


        # Call the service asynchronously
        future = self.linear_motion_client.call_async(request)
        future.add_done_callback(self.callback)

    def send_six_d_motion_request(self,x_pos,y_pos,z_pos,rx_pos,ry_pos,rz_pos,xy_max_speed,xy_max_accl,z_max_speed,rx_max_speed,ry_max_speed,rz_max_speed):
        request = SixDofMotion.Request()
        request.x_pos = x_pos
        request.y_pos = y_pos
        request.z_pos = float(z_pos)
        request.rx_pos = rx_pos
        request.ry_pos = ry_pos
        request.rz_pos = rz_pos
        request.xy_max_speed = xy_max_speed
        request.xy_max_accl = xy_max_accl
        request.z_max_speed = z_max_speed
        request.rx_max_speed = rx_max_speed
        request.ry_max_speed = ry_max_speed
        request.rz_max_speed = rz_max_speed

        


        # Call the service asynchronously
        future = self.six_d_motion_client.call_async(request)
        future.add_done_callback(self.callback)

    def xbot_activation_request(self, xbot_id, activate):
        request = ActivateXbots.Request()
        request.xbot_id = xbot_id
        request.activation_status=activate

        # Call the service asynchronously
        future = self.linear_motion_client.call_async(request)
        future.add_done_callback(self.callback)

    def levitation_request(self, xbot_id, levitate):
        request = LevitationXbots.Request()
        request.xbot_id = xbot_id
        request.levitation_status=levitate

        # Call the service asynchronously
        future = self.linear_motion_client.call_async(request)
        future.add_done_callback(self.callback)

    def callback(self, future):
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")

    def xbot_postion_callback(self,msg):
        self.xpos=msg

    


        

def main(args=None):
    rclpy.init(args=args)
    # Create the client node
    move_client = MoverClientNode()
    # Spin the client to handle service responses
    rclpy.spin(move_client)

    # Shutdown when done
    rclpy.shutdown()

if __name__ == '__main__':
    main()
