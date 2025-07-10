import sys
import time
from typing import Tuple, Optional

# ROS 2 imports
import rclpy  # type:ignore
from rclpy.node import Node  # type:ignore
from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import (
    MoveAbsolute,
    MoveRelativ,
    Home,
    ShutdownLinearAxis,
    GetPosition,
    SetVelocityParameters,
    GetVelocityParameters
)

from .drivers.linear_axis_driver import LinearAxisDriver
from .drivers.thorlabs_lts300_driver import ThorlabsLTS300Driver
from .drivers.simulated_linear_axis_driver import SimulatedLinearAxisDriver
from .drivers.gazebo_linear_axis_driver import GazeboLinearAxisDriver


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

        The node is first created with a temporary name because the actual nod0e name
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

        # Initialize the driver based on the use_sim_time parameter
        if self.use_sim_time:
            # Check if we should use Gazebo integration
            self.declare_parameter('use_gazebo', True)
            use_gazebo = self.get_parameter('use_gazebo').value

            if use_gazebo:
                self.driver: LinearAxisDriver = GazeboLinearAxisDriver(self)
                self.get_logger().info("🚀 Using Gazebo-integrated simulation driver")
            else:
                self.driver: LinearAxisDriver = SimulatedLinearAxisDriver()
                self.get_logger().info("🔧 Using basic simulation driver")
        else:
            self.driver: LinearAxisDriver = ThorlabsLTS300Driver()
            self.get_logger().info("🔌 Using Thorlabs LTS300 hardware driver")

        # Connect to the physical LTS300 device or simulated device
        connected = self.driver.connect(
            self.serial_port,
            self.x_axis_serial,
            self.z_axis_serial,
            self.debug_mode
        )

        # Change the node name after connection
        if connected:
            self.node_name = f'lts300_{self.driver.get_axis_type()}_axis'
            if self.debug_mode:
                self.get_logger().info(
                    f'Changing node name to {self.node_name}')
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
        if connected:
            self.get_logger().info(f'✅ {self.node_name} initialized')
        else:
            self.get_logger().error(f'❌ Error initializing {self.node_name}')

    def initialize_parameters(self):
        """
        Initialize parameters and member variables for the node.

        This method declares and retrieves ROS parameters and initializes
        member variables used throughout the node.
        """
        # Initialize member variables
        self.client_connected: bool = False
        self.other_axis_position: float = None
        self.other_axis: str = None
        self.driver: LinearAxisDriver = None  # Will be initialized in __init__

        self.declare_parameter('debug_mode', False)
        
        # use_sim_time might already be declared by ROS2 globally
        try:
            self.declare_parameter('use_sim_time', False)
        except Exception:
            pass

        self.debug_mode = self.get_parameter(
            'debug_mode').get_parameter_value().bool_value
        self.use_sim_time = self.get_parameter(
            'use_sim_time').get_parameter_value().bool_value

        # Declare parameters with default values
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('x_axis_serial', '45456044')
        self.declare_parameter('z_axis_serial', '45407924')
        self.declare_parameter('collision_threshold', 300.0)
        self.declare_parameter('node_name', 'lts300_x_axis_node')
        self.declare_parameter('namespace', 'promoc_assembly')
        self.declare_parameter('standard_velocity', (0.0, 0.2, 536.5))  # mm/s

        # Get parameter values
        self.serial_port: str = self.get_parameter('serial_port').value
        self.x_axis_serial: str = self.get_parameter('x_axis_serial').value
        self.z_axis_serial: str = self.get_parameter('z_axis_serial').value
        self.collision_threshold: float = self.get_parameter(
            'collision_threshold').value
        self.namespace: str = self.get_parameter('namespace').value

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
        
        self.set_velocity_service = self.create_service(
            SetVelocityParameters, f'{self.node_name}/set_velocity_parameters', self.set_velocity_callback)
        
        self.get_velocity_service = self.create_service(
            GetVelocityParameters, f'{self.node_name}/get_velocity_parameters',self.get_velocity_callback)

    def setup_publishers(self):
        """Set up ROS2 publishers for the node."""
        # Get the namespace from the node

        # Use absolute topic name to ensure correct namespace
        topic_name = f'/{self.namespace}/{self.node_name}/position'
        if self.debug_mode:
            self.get_logger().debug(
                f"🔧 Setting up publisher for topic: {topic_name}")

        self.position_publisher = self.create_publisher(
            LinearAxisInfo, topic_name, 10)

        # Create a timer to publish position at regular intervals
        self.position_timer = self.create_timer(0.1, self.publish_position)

    def publish_position(self):
        """Publish the current position of the axis."""
        if not self.driver:
            return

        msg = LinearAxisInfo()
        position = self.driver.get_position()

        # Debug logging
        if self.debug_mode:
            self.get_logger().debug(f"🔧 Position update: {position}")

        # Ensure we have a valid position value
        if position is not None:
            msg.axis_position = position
        else:
            # Use the last known position or default to 0.0
            msg.axis_position = 0.0  # Fallback to 0.0 if driver returns None or error
            self.get_logger().warn("Using fallback position value")

        msg.axis_type = self.driver.get_axis_type()
        msg.is_moving = self.driver.is_moving()
        msg.serial_number = self.driver.get_serial_number()

        self.position_publisher.publish(msg)

    def setup_subscribers(self):
        """Set up ROS2 subscribers for the node."""
        # Use absolute topic name for subscription
        topic_name = f'/{self.namespace}/lts300_{self.other_axis}_axis/position'
        if self.debug_mode:
            self.get_logger().debug(f"🔧 Subscribing to topic: {topic_name}")

        self.other_axis_subscription = self.create_subscription(
            LinearAxisInfo,
            topic_name,
            self.other_axis_position_callback,
            10)

    def other_axis_position_callback(self, msg):
        """Store the position of the other axis when received."""
        if self.other_axis_position is None:
            if self.debug_mode:
                self.get_logger().debug(
                    f"🔧 Received first position update from {self.other_axis}-axis: {msg.axis_position} mm")
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
                response.status_message = f"⚠️ Collision risk detected: {self.other_axis}-axis is at {self.other_axis_position} mm (threshold: {self.collision_threshold} mm)"

                self.get_logger().warn(response.status_message)
                return response
            if self.debug_mode:
                self.get_logger().debug(
                    f'🔧 Moving to position: {target_position} mm')
            self.driver.move_absolute(target_position)
            response.success = True
            response.status_message = f"✅ Successfully moved to position {self.driver.get_position()} mm"
        except Exception as e:
            self.get_logger().error(f'❌ Error moving to position: {e}')
            response.success = False
            response.status_message = f"❌ Error: {str(e)}"

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
            # Collision Check
            if self.other_axis_position is not None and self.other_axis_position > self.collision_threshold:
                response.success = False
                response.status_message = f"⚠️ Collision risk detected: {self.other_axis}-axis is at {self.other_axis_position} mm (threshold: {self.collision_threshold} mm)"
                self.get_logger().warn(response.status_message)
                return response
            if self.debug_mode:
                self.get_logger().debug(
                    f'🔧 Moving relatively by: {request.axis_position} mm')
            self.driver.move_relative(request.axis_position)
            response.success = True
            response.status_message = f"✅ Successfully moved to position {self.driver.get_position()} mm"

        except Exception as e:
            self.get_logger().error(f'❌ Error moving to position: {e}')
            response.success = False
            response.status_message = f"❌ Error: {str(e)}"

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

            self.driver.home()

            response.success = True
            response.status_message = "✅ Homing completed successfully"

        except Exception as e:
            self.get_logger().error(f'❌ Error during homing: {e}')
            response.success = False
            response.status_message = f"❌ Error: {str(e)}"

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
            response.status_message = "✅ Successfully shutdown device"
        except Exception as e:
            self.get_logger().error(f'❌ Error moving to position: {e}')
            response.success = False
            response.status_message = f"Error: {str(e)}"

        return response

    def get_position_callback(self, request, response):
        try:
            response.axis_position = self.driver.get_position()
            response.success = True
            response.status_message = "✅ Successfully retrieved position"
            return response
        except Exception as e:
            response.axis_position = -1.0
            response.success = False
            response.status_message = f"❌ Error getting position: {str(e)}"
            return response
    def set_velocity_callback(self, request, response):
        """Handle velocity parameter setting requests."""
        try:
            min_vel = None if request.min_velocity < 0 else request.min_velocity
            accel = None if request.acceleration < 0 else request.acceleration
            max_vel = None if request.max_velocity < 0 else request.max_velocity
            
            if self.debug_mode:
                self.get_logger().info(f'🔧 Setting velocity parameters: min={min_vel}, accel={accel}, max={max_vel}')
            
            result = self.driver.set_velocity_parameters(min_vel, accel, max_vel)
            
            response.success = True
            response.status_message = "✅ Velocity parameters updated successfully"
            response.actual_min_velocity = result[0]
            response.actual_acceleration = result[1] 
            response.actual_max_velocity = result[2]
            
        except Exception as e:
            self.get_logger().error(f'❌ Error setting velocity parameters: {e}')
            response.success = False
            response.status_message = f"❌ Error: {str(e)}"
            response.actual_min_velocity = 0.0
            response.actual_acceleration = 0.0
            response.actual_max_velocity = 0.0
            
        return response

    def get_velocity_callback(self, request, response):
        """Handle velocity parameter query requests."""
        try:
            params = self.driver.get_velocity_parameters()
            
            response.success = True
            response.status_message = "✅ Velocity parameters retrieved successfully"
            response.min_velocity = params[0]
            response.acceleration = params[1]
            response.max_velocity = params[2]
            
        except Exception as e:
            self.get_logger().error(f'❌ Error getting velocity parameters: {e}')
            response.success = False
            response.status_message = f"❌ Error: {str(e)}"
            response.min_velocity = 0.0
            response.acceleration = 0.0
            response.max_velocity = 0.0
            
        return response

    # Helper functions
    def shutdown(self):
        """
        Properly shutdown the device connection.

        This ensures the device is left in a good state and resources are released.
        """
        if self.driver:
            try:
                self.driver.disconnect()
                self.get_logger().info('✅ Device disconnected')
            except Exception as e:
                self.get_logger().error(f'❌ Error during shutdown: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = LTS300ServiceNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Received keyboard interrupt, shutting down...')
    finally:
        node.get_logger().info('Preparing for shutdown...')
        if node.driver:
            try:
                node.get_logger().info('Homing device before shutdown...')
                node.driver.home()
                node.get_logger().info('Homing completed successfully')
            except Exception as e:
                node.get_logger().error(
                    f'❌ Error during homing before shutdown: {e}')
            finally:
                try:
                    node.shutdown()
                except Exception as e:
                    node.get_logger().error(
                        f'❌ Error during device shutdown: {e}')
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()


# Todo implement change of movement and homing speed parameters
