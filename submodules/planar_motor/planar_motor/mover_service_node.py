#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from pmclib import system_commands as sys   # PMC System related commands
from pmclib import xbot_commands as bot     # PMC Mover related commands
from pmclib import pmc_types                # PMC API Types

from planar_motor_interfaces.msg import XBotInfo
from planar_motor_interfaces.srv import LinearMotionSi
from planar_motor_interfaces.srv import SixDofMotion
from planar_motor_interfaces.srv import ActivateXbots
from planar_motor_interfaces.srv import LevitationXbots

import time

class MoverServiceNode(Node): 
    def __init__(self):
        super().__init__("mover_node")
        

        self.xbot_id = 1

        #Publisher
        self.xbot_pos_publisher_ = self.create_publisher(XBotInfo, "xbot_info", 10)
        
        
        # Services
        self.linear_movement_server = self.create_service(LinearMotionSi,f"{self.get_name()}/linear_mover_motion",self.callback_linear_motion_si)
        self.six_d_movement_server = self.create_service(SixDofMotion,f"{self.get_name()}/six_d_mover_motion",self.callback_six_d_motion)
        self.xbot_activation_server = self.create_service(ActivateXbots,f"{self.get_name()}/activate_xbots",self.callback_activate_xbot)
        #self.xbot_levitation_server = self.create_service(LevitationXbots, f"{self.get_name()}/levitation_xbots", self.callback_levitation_xbot)
        

        #Timer
        self.xbot_position_timer =self.create_timer(0.1,self.xbot_postition_publisher)

        

        self.get_logger().info("Mover Node Started")

        self.get_logger().info("Connecting to PMC...")
        input_id = 1
        success = False

        while not success:
            success = sys.connect_to_pmc("192.168.10.100")
        self.get_logger().info("Connected")

        
        

        # %% Activating the system
        # On bootup, all the movers within the system will be in a
        # "Deactivated" state. Which means that they are not actively
        # position controlled. To start controlling the system, the
        # "activate" command must be sent.
        bot.activate_xbots()
        self.get_logger().info("XBot Activated")

        # Now we wait for the movers to be levitated and fully controlled.
        # This can be done by periodically polling for the PMC status.
        maxTime = time.time() + 60  # Set timeout of 60s
        while sys.get_pmc_status() is not pmc_types.PmcStatus.PMC_FULLCTRL:
            time.sleep(0.5)
            if time.time() > maxTime:
                raise TimeoutError("PMC Activation timeout")
            



    def xbot_postition_publisher(self):
        xbot_data_list=bot.get_all_xbot_info(0)
        msg=XBotInfo()
        msg.x_pos = float(xbot_data_list[0].x_pos)
        msg.y_pos = float(xbot_data_list[0].y_pos)
        msg.z_pos = float(xbot_data_list[0].z_pos)
        msg.rx_pos = float(xbot_data_list[0].rx_pos)
        msg.ry_pos = float(xbot_data_list[0].ry_pos)
        msg.rz_pos = float(xbot_data_list[0].rz_pos)
        self.xbot_pos_publisher_.publish(msg)


    def callback_linear_motion_si(self, request, response):
        xbot_id = request.xbot_id
        x_pos  = request.x_pos  
        y_pos = request.y_pos
        xy_max_speed = request.xy_max_speed
        xy_max_accl = request.xy_max_accl

    

        travel_time_sec=bot.linear_motion_si(xbot_id,
                             x_pos/1000,
                             y_pos/1000,
                             xy_max_speed,
                             xy_max_accl
                             )
    
        if travel_time_sec > 0.0:
            response.finished = True
        else:
            response.finished = False
        
        return response


    def callback_six_d_motion(self,request,response):

        xbot_id = 1
        x_pos = request.x_pos  
        y_pos = request.y_pos
        z_pos = request.z_pos
        rx_pos = request.rx_pos
        ry_pos = request.ry_pos
        rz_pos = request.rz_pos
        xy_max_speed = request.xy_max_speed
        xy_max_accl = request.xy_max_accl
        z_max_speed = request.z_max_speed
        rx_max_speed = request.rx_max_speed
        ry_max_speed = request.ry_max_speed
        rz_max_speed = request.rz_max_speed

        response.finished = False


        #TODO Vergleich mover postition mit ziel position return True wenn equal  

        bot.six_d_of_motion(xbot_id,
                            x_pos/1000,
                            y_pos/1000,
                            z_pos/1000,
                            rx_pos/1000,
                            ry_pos/1000,
                            rz_pos/1000,
                            xy_max_speed,
                            xy_max_accl,
                            z_max_speed,
                            rx_max_speed,
                            ry_max_speed,
                            rz_max_speed
        )


        response.finished =True

        return response
         

    def callback_activate_xbot(self,request,response):
         if request.activation_status == True:
            bot.activate_xbots()
            response.activation_status = True 
         if request.activation_status == False:
            bot.deactivate_xbots()
            response.activation_status = False
         return response
    
    
    def callback_levitation_xbot(self, request, response):
        #xbot_id = request.xbot_id
        if request.levitation == True:
            bot.levitation_command(request.xbot_id, pmc_types.LevitateOptions.LEVITATE)
            response.levitation = True
        else:
            bot.levitation_command(request.xbot_id, pmc_types.LevitateOptions.LAND)
            response.levitation = False


         
def main(args=None):
    rclpy.init(args=args)   
    node = MoverServiceNode()   
    rclpy.spin(node)
    rclpy.shutdown()

    



if __name__ == "__main__":
    main()

# %%
