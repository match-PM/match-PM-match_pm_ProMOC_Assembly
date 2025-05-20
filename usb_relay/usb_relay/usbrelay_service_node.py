#!/home/pm_control/Documents/PyVenv/promocVenv/bin/python

import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.msg import RelayInfo
from promoc_assembly_interfaces.srv import SetRelay
import hid
import time




class USBrelayServiceNode(Node):
    def __init__(self):
        """
        Initialize the USBrelayServiceNode class
        
        This function sets up the ROS node, creates publishers and service servers for commands,
        initializes the connection to the usb relay, and starts a timer to periodically publish relay states.
        """

        super().__init__("usbrelay_node")

        self.initialize_relay_parameters()
        
        # Setup ROS publishers and services
        self.setup_relay_publishers()
        self.setup_relay_services()
        
        # Initialize connections
        self.startup_relay_connection()

        # Start timers
        self.setup_relay_timers()
    
    # Initialization functions

    def initialize_relay_parameters(self):

        self.relay_state = [
            False,      # initial status of relay 1
            False,      # initial status of relay 2
            True,       # initial status of relay 3
            False,      # initial status of relay 4
            False,      # initial status of relay 5
            False,      # initial status of relay 6
            False,      # initial status of relay 7
            False]      # initial status of relay 8
        
        self.VENDOR_ID = 0x16c0
        self.PRODUCT_ID = 0x05df
    
    def setup_relay_publishers(self):
        """Create ROS publishers for relay information."""
        self.usbrelay_state_publisher_ = self.create_publisher(
            RelayInfo, "relay_info", 10)

    def setup_relay_services(self):
        """Define and create ROS services for control relay states."""
        self.switch_relay_server = self.create_service(
            SetRelay, f"{self.get_name()}/switch_relay", self.callback_set_relay_state
        )

    def setup_relay_timers(self):
        """
        Set up periodic timers for the node's recurring tasks.
        
        This function initializes timers that trigger callback functions at specified intervals.
        Currently, it creates a timer that publishes the relay state information every 0.1 seconds.
        
        Parameters:
            None
            
        Returns:
            None
        """
        self.relay_state_timer = self.create_timer(
            1.0, self.relay_state_publisher)

    def startup_relay_connection(self):
        self.device = hid.device()
        self.device.open(self.VENDOR_ID, self.PRODUCT_ID)
        self.set_relay_state(1, self.relay_state[0])
        self.set_relay_state(2, self.relay_state[1])
        self.set_relay_state(3, self.relay_state[2])
        self.set_relay_state(4, self.relay_state[3])
        self.set_relay_state(5, self.relay_state[4])
        self.set_relay_state(6, self.relay_state[5])
        self.set_relay_state(7, self.relay_state[6])
        self.set_relay_state(8, self.relay_state[7])
        
        # self.set_relay_state(self.device, 1, self.status_relay_1)
        # self.set_relay_state(self.device, 2, self.status_relay_2)
        # self.set_relay_state(self.device, 3, self.status_relay_3)
        # self.set_relay_state(self.device, 4, self.status_relay_4)
        # self.set_relay_state(self.device, 5, self.status_relay_5)
        # self.set_relay_state(self.device, 6, self.status_relay_6)
        # self.set_relay_state(self.device, 7, self.status_relay_7)
        # self.set_relay_state(self.device, 8, self.status_relay_8)
        #return device

    # Timer callback functions

    def relay_state_publisher(self):
        """
        This function publishes the current states of the relay to a ROS topic.

        Parameters:
        None

        Returns:
        None

        The function initializes an RelayInfo message, retrieves the current state of the relay.
        Finally, the message is published to the
        `relay_state_publisher_` topic.
        """
        msg = RelayInfo()

        msg.status_relay1 = self.relay_state[0]
        msg.status_relay2 = self.relay_state[1]
        msg.status_relay3 = self.relay_state[2]
        msg.status_relay4 = self.relay_state[3]
        msg.status_relay5 = self.relay_state[4]
        msg.status_relay6 = self.relay_state[5]
        msg.status_relay7 = self.relay_state[6]
        msg.status_relay8 = self.relay_state[7]


        self.usbrelay_state_publisher_.publish(msg=msg)
        self.get_logger().info("\nStatus relay 1: " + str(msg.status_relay1) + 
                               "\nStatus relay 2: " + str(msg.status_relay2) +
                               "\nStatus relay 3: " + str(msg.status_relay3) +
                               "\nStatus relay 4: " + str(msg.status_relay4) +
                               "\nStatus relay 5: " + str(msg.status_relay5) +
                               "\nStatus relay 6: " + str(msg.status_relay6) +
                               "\nStatus relay 7: " + str(msg.status_relay7) +
                               "\nStatus relay 8: " + str(msg.status_relay8))
    # Callback functions for ROS2 services

    def callback_set_relay_state(self, request, response):
        if request.relay_status == True:
            self.device.write([0, 0xFF, request.relay_number, 0, 0, 0, 0, 0, 1])
            self.relay_state[request.relay_number - 1] = True
            if request.activation_time > 0.0:
                time.sleep(request.activation_time)
                self.device.write([0, 0xFD, request.relay_number, 0, 0, 0, 0, 0, 1])
                self.relay_state[request.relay_number - 1] = False
        elif request.relay_status == False:
            self.device.write([0, 0xFD, request.relay_number, 0, 0, 0, 0, 0, 1])
            self.relay_state[request.relay_number - 1] = False
            if request.activation_time > 0.0:
                time.sleep(request.activation_time)
                self.device.write([0, 0xFF, request.relay_number, 0, 0, 0, 0, 0, 1])
                self.relay_state[request.relay_number - 1] = True

    # Helper functions

    def destroy_node(self):
        self.get_logger().info("Shutting down USBRelayServiceNode")
        try:
            self.get_logger().info("Close connection to usb relay")
            self.device.close()
            self.get_logger().info("Close connection Successfully")
        except Exception as e:
            self.get_logger().error(f"Error close connection to usb relay: {e}")
        finally:
            super().destroy_node()

    def set_relay_state(self, relay_number, state):
        if state:
            self.device.write([0, 0xFF, relay_number, 0, 0, 0, 0, 0, 1])
        else:
            self.device.write([0, 0xFD, relay_number, 0, 0, 0, 0, 0, 1])

    def set_all_on(self):
        self.device.write([0, 0xFE, 0, 0, 0, 0, 0, 0, 1])

    def set_all_off(self):
        self.device.write([0, 0xFC, 0, 0, 0, 0, 0, 0, 1])



def main(args=None):
    rclpy.init(args=args)
    node = USBrelayServiceNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except rclpy.exceptions.RCLError:
                pass  # Ignore the shutdown error


if __name__ == '__main__':
    main()