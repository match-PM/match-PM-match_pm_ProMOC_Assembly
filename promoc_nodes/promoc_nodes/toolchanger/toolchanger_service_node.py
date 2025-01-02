import rclpy
from rclpy.node import Node



class ToolchangerServiceNode(Node):
    def __init__():
        super().__init__("toolchanger_node")

        self.toolchanger_activation_server = self.create_service(ActivateToolchanger,f"{self.get_name()}/activate_toolchanger",self.callback_activate_toolchanger)
    
    
    def getStatus_toolchanger(self):
        # get the status of the toolchanger
        #statusToolchanger = ???
        pass
        #return statusToolchanger


    def setStatus_toolchanger(self, statusToolchanger):
        if statusToolchanger:
            self.get_logger().info("Switch status of toolchanger to close/active")
            # set value of toolchager to true
        else:
            self.get_logger().info("Switch status of toolchanger to open")
            # set valve of toolchager to false
        
        statusToolchanger = self.getStatus_toolchanger()

        return statusToolchanger
    


def main(args=None):
    rclpy.init(args=args)
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