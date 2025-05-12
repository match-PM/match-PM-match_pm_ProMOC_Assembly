import sys
import time

# Try to import Thorlabs library
try:
    from pylablib.devices import Thorlabs
except ImportError as e:
    print(f"Error importing Thorlabs: {e}")

# ROS 2 imports
import rclpy  # type:ignore
from rclpy.node import Node  # type:ignore
from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import (
    MoveAbsolute, 
    MoveRelativ, 
    Home, 
    ShutdownLinearAxis, 
    GetPosition
)



class LTS300ServiceNode(Node):
    def __init__(self):
        """
        Initialize the LTS300ServiceNode.
        
        This constructor initializes the ROS2 node for controlling a Thorlabs LTS300 linear stage.
        It performs the following steps:
        1. Creates a temporary node
        2. Initializes parameters and connects to the physical device
        3. Reinitializes the node with the proper name based on the detected axis type
        4. Sets up services, publishers, and subscribers
        
        The node is first created with a temporary name because the actual node name
        depends on the detected axis type (X or Z), which is determined during the
        connection process.
        
        Parameters:
            None
            
        Returns:
            None: The constructor initializes the node but does not return any values.
                 Sets up the node's internal state and ROS2 communication interfaces.
        """
        # Initialize the ROS2 node with a temporary name
        super().__init__('lts300_service_node_temp')

        # Initialize core parameters and member variables
        self.initialize_parameters()

        # Connect to the physical LTS300 device
        self.connect()

        # Change the node name after connection
        if self.connected:
            self.get_logger().info(f'Changing node name to {self.node_name}')
            self.get_node_names_and_namespaces()  # This is required to update the node name
            rclpy.shutdown()
            rclpy.init()
            super().__init__(self.node_name)
            

        # Set up ROS2 services
        self.setup_services()

        # Set up ROS2 publishers and subscribers
        self.setup_publishers()
        self.setup_subscribers()

        # Log initialization status
        if self.connected:
            self.get_logger().info(f'{self.node_name} initialized')
        else:
            self.get_logger().error(f'Error initializing {self.node_name}')
    
    
    def initialize_parameters(self):
        """
        Initialize parameters and member variables for the node.
        
        This method declares and retrieves ROS parameters and initializes
        member variables used throughout the node.
        """
        # Initialize member variables
        self.connected:bool = False
        self.device:Thorlabs.KinesisMotor = None
        self.serial_no:str = None
        self.axis_type:str = None
        self.node_name:str = None
        self.client_connected:bool = False
        self.other_axis_position:float = None
        self.other_axis:str = None

        # Declare parameters with default values
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('x_axis_serial', '45456044')
        self.declare_parameter('z_axis_serial', '45407924')
        self.declare_parameter('device_units_per_mm', 409600.0)
        self.declare_parameter('collision_threshold', 10.0)
        self.declare_parameter('node_name', 'lts300_x_axis_node')
        self.declare_parameter('namespace', 'promoc_assembly')
        
        # Get parameter values
        self.serial_port:str = self.get_parameter('serial_port').value
        self.x_axis_serial:str = self.get_parameter('x_axis_serial').value
        self.z_axis_serial:str = self.get_parameter('z_axis_serial').value
        self.device_units_per_mm:float = self.get_parameter('device_units_per_mm').value
        self.collision_threshold:float = self.get_parameter('collision_threshold').value
        self.namespace:str = self.get_parameter('namespace').value

    def connect(self):
        """
        Establish a connection to the LTS300 linear stage device.
        
        This method initializes the connection to the Thorlabs LTS300 linear stage
        using the configured serial port. It retrieves the device's serial number,
        determines the axis type (X or Z), sets the node name accordingly, and
        performs an initial homing operation to calibrate the device.
        
        Parameters:
            None
            
        Returns:
            None: The method updates instance variables to reflect the connection
                  status and device information, but does not return any values.
                  Sets self.connected to True on success, False on failure.
        """
        try:
            self.get_logger().info(f'Connecting to LTS300 on port {self.serial_port}...')
            
            self.device = Thorlabs.KinesisMotor(self.serial_port, scale="m")
            
            # Read the serial number
            self.serial_no = str(self.device.get_device_info()[0])
            self.get_logger().info(f'Detected serial number: {self.serial_no}')
            
            # Determine the axis type
            self.axis_type = self.determine_axis(self.serial_no)
            self.other_axis = 'z' if self.axis_type == 'x' else 'x'

            # Set the node name based on the axis type
            self.node_name = f'lts300_{self.axis_type}_axis'
            
            self.get_logger().info(f'Connected to {self.axis_type.upper()}-axis (SN: {self.serial_no})')
    
            self.connected = True
    
            # Home the device
            self.device.home()
            while self.device.is_moving():
                time.sleep(0.1)
            self.update_position()
    
        except Exception as e:
            self.get_logger().error(f'Error connecting: {e}')
            self.connected = False
        


    def setup_services(self):
        """
        Set up ROS2 services for controlling the LTS300 linear stage.

        This function creates and registers all the service endpoints that allow
        external nodes to interact with the linear stage. Services include
        movement control (absolute and relative), homing operations, parameter
        configuration, position queries, and shutdown functionality.

        Parameters:
            None

        Returns:
            None: The function registers service handlers with the ROS2 node
                 but does not return any values.
        """
        # Create service for moving
        self.move_absolute_service = self.create_service(
            MoveAbsolute, f'{self.node_name}/move_absolute', self.move_absolute_callback)

        self.move_relative_service = self.create_service(
            MoveRelativ, f'{self.node_name}/move_relative', self.move_relative_callback)

        # Create service for homing the device
        self.home_service = self.create_service(
            Home, f'{self.node_name}/home', self.home_callback)

        self.shutdown_service = self.create_service(
            ShutdownLinearAxis, f'{self.node_name}/shutdown', self.shutdown_callback)

        self.get_position_service = self.create_service(
            GetPosition, f'{self.node_name}/get_position', self.get_position_callback)
    def setup_publishers(self):
        """Set up ROS2 publishers for the node."""
        # Get the namespace from the node
        
        self.get_logger().info(f"Node namespace: {self.namespace}")
        
        # Use absolute topic name to ensure correct namespace
        topic_name = f'/{self.namespace}/{self.node_name}/position'
        self.get_logger().info(f"Publishing to topic: {topic_name}")
        
        self.position_publisher = self.create_publisher(
            LinearAxisInfo, topic_name, 10)
        
        # Create a timer to publish position at regular intervals
        self.position_timer = self.create_timer(0.1, self.publish_position)

    def publish_position(self):
        """Publish the current position of the axis."""
        if not self.connected or not self.device:
            return
            
        msg = LinearAxisInfo()
        position = self.update_position()
        
        # Debug logging
        self.get_logger().debug(f"Position update: {position}")
        
        # Ensure we have a valid position value
        if position is not None:
            msg.axis_position = position
        else:
            # Use the last known position or default to 0.0
            msg.axis_position = getattr(self, 'position', 0.0)
            self.get_logger().warn("Using fallback position value")
            
        msg.axis_type = self.axis_type
        msg.is_moving = self.device.is_moving()
        msg.serial_number = self.serial_no
        
        self.position_publisher.publish(msg)
    def setup_subscribers(self):
        """Set up ROS2 subscribers for the node."""
        # Use absolute topic name for subscription
        topic_name = f'/{self.namespace}/lts300_{self.other_axis}_axis/position'
        self.get_logger().info(f"Subscribing to topic: {topic_name}")
        
        self.other_axis_subscription = self.create_subscription(
            LinearAxisInfo,
            topic_name,
            self.other_axis_position_callback,
            10)
    
    def other_axis_position_callback(self, msg):
        """Store the position of the other axis when received."""
        if self.other_axis_position is None:
            self.get_logger().info(f"Received first position update from {self.other_axis}-axis: {msg.axis_position} mm")
        self.other_axis_position = msg.axis_position


    # Callback functions for ROS services
    def move_absolute_callback(self, request, response):
        """
        Handle absolute movement requests.
        
        This callback moves the linear stage to an absolute position specified in mm.
        It performs collision checking before executing the movement.
        
        Parameters:
            request: The service request containing the target position
            response: The service response to be filled
            
        Returns:
            response: The filled service response with success status and message
        """
        try:
            target_position = request.axis_position
            
            # Collision Check
            if self.other_axis_position is not None and self.other_axis_position > self.collision_threshold:
                response.success = False
                response.error_message = f"Collision risk detected: {self.other_axis}-axis is at {self.other_axis_position} mm (threshold: {self.collision_threshold} mm)"

                self.get_logger().warn(response.error_message)
                return response
            
            self.get_logger().info(f'Moving to position: {target_position} mm')
            self.device.move_to(target_position*self.device_units_per_mm, scale=False)
            while self.device.is_moving():
                time.sleep(0.1)
            # Update the position after movement
            self.update_position()
            response.success = True
            response.error_message = f"Successfully moved to position {self.position} mm"
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response

    def move_relative_callback(self, request, response):
        """
        Handle relative movement requests.
        
        This callback moves the linear stage by a relative distance specified in mm.
        It performs collision checking before executing the movement.
        
        Parameters:
            request: The service request containing the relative movement distance
            response: The service response to be filled
            
        Returns:
            response: The filled service response with success status and message
        """
        try:
            relative_position = request.axis_position * self.device_units_per_mm
            current_position = self.device.get_position()
            target_position = current_position + relative_position

            # Collision Check
            if self.other_axis_position is not None and self.other_axis_position > self.collision_threshold:
                response.success = False
                response.error_message = f"Collision risk detected: {self.other_axis}-axis is at {self.other_axis_position} mm (threshold: {self.collision_threshold} mm)"
                self.get_logger().warn(response.error_message)
                return response
            
            self.get_logger().info(f'Moving relatively by: {request.axis_position} mm')
            self.device.move_to(target_position, scale=False)
            while self.device.is_moving():
                time.sleep(0.1)
            # Update the position after movement
            self.update_position()
            response.success = True
            response.error_message = f"Successfully moved to position {self.position} mm"
                
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response


    

    def home_callback(self, request, response):
        """
        Handle homing requests.
        
        This callback initiates the homing procedure for the linear stage.
        
        Parameters:
            request: The service request (empty)
            response: The service response to be filled
            
        Returns:
            response: The filled service response with success status and message
        """
        try:
            self.get_logger().info('Homing device...')

            self.device.home(force=True, timeout=60)
            self.update_position() 
    
            response.success = True
            response.error_message = "Homing completed successfully"
        
        except Exception as e:
            self.get_logger().error(f'Error during homing: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"

        return response

    def shutdown_callback(self, request, response):
        """
        Handle shutdown requests.
        
        This callback properly shuts down the device connection.
        
        Parameters:
            request: The service request (empty)
            response: The service response to be filled
            
        Returns:
            response: The filled service response with success status and message
        """
        try:
            self.shutdown()
            response.success = True
            response.error_message = "Successfully shutdown device"
        except Exception as e:
            self.get_logger().error(f'Error moving to position: {e}')
            response.success = False
            response.error_message = f"Error: {str(e)}"
        
        return response

    def get_position_callback(self, request, response):
        try:
            response.axis_position = self.update_position()
            response.success = True
            response.error_message = "Successfully retrieved position"
            return response
        except Exception as e:
            response.axis_position=-1.0
            response.success = False
            response.error_message = f"Error getting position: {str(e)}"
            return response 
        

    

    # Helper functions
    def shutdown(self):
        """
        Properly shutdown the device connection.

        This ensures the device is left in a good state and resources are released.
        """
        if self.connected and self.device:
            try:
                self.device.close()

                # Update connection state
                self.connected = False
                self.get_logger().info('Device disconnected')
            except Exception as e:
                self.get_logger().error(f'Error during shutdown: {e}')




    def determine_axis(self, serial_number:str):
        """
        Determine the axis type based on the device serial number.
        
        Parameters:
            serial_number (str): The serial number of the connected device
            
        Returns:
            str: 'x' for X-axis, 'z' for Z-axis, or 'unknown' if the serial number is not recognized
        """
        if serial_number == self.x_axis_serial:
            self.get_logger().info(f"Recognized X-axis with serial number: {serial_number}")
            return 'x'
        elif serial_number == self.z_axis_serial:
            self.get_logger().info(f"Recognized Z-axis with serial number: {serial_number}")
            return 'z'
        else:
            self.get_logger().warning(f"Unknown serial number: {serial_number}. Defaulting to 'unknown' axis.")
            return 'unknown'


    def update_position(self):
        """
        Update the internal position tracking variable with the current device position.
        
        This method queries the device for its current position and updates the internal
        tracking variable. It should be called after any movement operation completes.
        
        Returns:
            float: The updated position in mm
        """
        try:
            self.position = self.device.get_position()/self.device_units_per_mm
            return self.position
        except Exception as e:
            self.get_logger().error(f'Error updating position: {e}')
            return None
def main(args=None):
    rclpy.init(args=args)
    node = LTS300ServiceNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Received keyboard interrupt, shutting down...')
    finally:
        node.get_logger().info('Preparing for shutdown...')
        if node.connected and node.device:
            try:
                node.get_logger().info('Homing device before shutdown...')
                node.device.home(force=True, timeout=60)  # 60 second timeout
                node.update_position()  # Update position to the final home position
                node.get_logger().info('Homing completed successfully')
            except Exception as e:
                node.get_logger().error(
                    f'Error during homing before shutdown: {e}')
            finally:
                try:
                    node.shutdown()
                except Exception as e:
                    node.get_logger().error(
                        f'Error during device shutdown: {e}')
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()





#Todo implement change of movement and homing speed parameters