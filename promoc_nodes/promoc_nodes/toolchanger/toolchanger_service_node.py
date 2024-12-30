import rclpy
from rclpy.node import Node



class Toolchanger():
    def __init__():

        self.toolchanger_activation_server = self.create_service(ActivateToolchanger,f"{self.get_name()}/activate_toolchanger",self.callback_activate_toolchanger)
        



def setStatus_toolchanger(self, statusToolchanger):
    if statusToolchanger:
        self.get_logger().info("Switch status of toolchanger to close/active")
    else:
        self.get_logger().info("Switch status of toolchanger to open")

    #set valve of toolchager


def main(args=None):
      
    node = ToolchangerServiceNode()   
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure that the cleanup function is called when the node shuts down
        node.destroy_node()

    



if __name__ == "__main__":
    main()