r"""
ROS2 Node for Thorlabs LTS300 Linear Axis Control.

This module implements the LTS300Node, which is the central orchestrator
for controlling a Thorlabs LTS300 linear stage (300mm travel).

Architecture Overview:
======================
The node follows a dependency injection pattern similar to the mover_node:

    LTS300Node (Orchestrator)
        │
    ├── Config (dict)      → Configuration from ROS parameters (serial number, limits, timeouts)
        ├── Lts300Interface    → Hardware abstraction (Real/Simulated)
        └── ServiceCallbacks   → Business logic (e.g., motion validation)

Startup Sequence:
==================
1. Node Initialization:
   └── Creates the ROS2 node and configures the logger.

2. Configuration Loading:
   └── Reads parameters (serial_port, collision_threshold, limits, etc.).

3. Hardware Interface Creation:
   └── Lts300Interface automatically selects between the real hardware driver or a simulation.

4. Connection Establishment:
   └── Connects to the axis via the specified serial port.

5. ROS2 Communication Setup:
   ├── Publisher: For 10 Hz position updates.
   ├── Subscriber: For the other axis's position (for collision avoidance).
   └── Services: For move_absolute, move_relative, home, etc.

6. Position Publishing:
   └── A timer publishes the current axis position every 100ms.

Special Features:
=================
- Collision Avoidance: Monitors the position of the other axis (X↔Z).
- Asynchronous Movements: Long-running operations do not block the node.
- Soft-Limits: Configurable motion boundaries.
- Homing: Automatic referencing with a timeout.

Usage:
======
    # Start as a ROS2 node:
    ros2 run linear_axis_nodes lts300_node

    # Start with simulation:
    ros2 run linear_axis_nodes lts300_node --ros-args -p use_sim_time:=true

Example Service Calls:
======================
    # Absolute movement (in mm):
    ros2 service call /lts300_x_axis/move_absolute \
        promoc_assembly_interfaces/srv/MoveAbsolute "{axis_position: 150.0}"

    # Perform homing:
    ros2 service call /lts300_x_axis/home promoc_assembly_interfaces/srv/Home
"""

from promoc_assembly_interfaces.msg import LinearAxisInfo
from promoc_assembly_interfaces.srv import (
    EmergencyStop,
    GetOperationStatus,
    GetPosition,
    GetVelocityParameters,
    Home,
    JogAxis,
    MoveAbsolute,
    MoveRelativ,
    SetVelocityParameters,
    ShutdownLinearAxis,
)
import rclpy
from rclpy.node import Node

from .lts300_interface import Lts300Interface
from .lts300_service_callbacks import ServiceCallbacks


class LTS300Node(Node):
    """
    Central ROS2 node for controlling the Thorlabs LTS300 linear axis.

    This class acts as the orchestrator—it creates and coordinates all
    other components but does not handle business logic itself.

    How it works:
    -------------
    The node proceeds through the following phases on startup:

    1. CONFIG-PHASE:
       - Loads configuration from ROS parameters.

    2. INTERFACE-PHASE:
       - Creates the hardware interface (which selects real or simulated hardware).
       - Establishes a connection to the device.

    3. COMMUNICATION-PHASE:
       - Registers ROS2 services.
       - Starts the position publisher.
       - Sets up a subscriber for the other axis's position.

    Attributes:
        config (dict): Configuration dictionary (limits, serial number, etc.).
        interface (Lts300Interface): Hardware abstraction layer.
        callbacks (ServiceCallbacks): Business logic for service callbacks.
        other_axis_position (float): Position of the other axis for collision avoidance.

    Example:
        >>> node = LTS300Node()
        >>> rclpy.spin(node)
    """

    def __init__(self):
        """
        Initializes the LTS300Node.

        Sequence of operations:
        -------------------------
        1. Creates the ROS2 node named "lts300_node".
        2. Loads configuration from ROS parameters.
        3. Creates the hardware interface.
        4. Connects to the linear axis.
        5. Sets up ROS2 communication.
        """
        super().__init__('lts300_node')

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: Load Configuration
        # ══════════════════════════════════════════════════════════════════════
        self.config = self._load_config()

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: Create Components
        # ══════════════════════════════════════════════════════════════════════
        self.interface = Lts300Interface(self.get_logger(), self.config)
        self.callbacks = ServiceCallbacks(
            self.get_logger(), self.interface, self.config)

        try:
            # ══════════════════════════════════════════════════════════════════
            # PHASE 3: Establish Connection
            # ══════════════════════════════════════════════════════════════════
            if not self.interface.connect():
                self.get_logger().error('Shutting down node due to connection failure.')
                self.get_logger().error('Node initialization failed, exiting...')
                return
            self.get_logger().info('Connection successful, continuing initialization...')

            # ══════════════════════════════════════════════════════════════════
            # PHASE 4: Set up ROS2 Communication
            # ══════════════════════════════════════════════════════════════════
            self.other_axis_position = None
            self._setup_ros_communication()

            self.get_logger().info(
                f"{self.get_name()} with S/N {self.config['serial_number']} is running.")
            self.get_logger().info('Node initialization complete!')

        except Exception as e:
            self.get_logger().error(f'Exception during initialization: {e}')
            self.get_logger().error('Node initialization failed, exiting...')
            raise

    def _load_config(self) -> dict:
        """
        Loads configuration from ROS parameters.

        Parameter Categories:
        ---------------------
        1. Connection:
           - serial_port: The serial port, e.g., /dev/ttyUSB0.
           - serial_number: Device serial number for identification.

        2. Safety:
           - collision_threshold: Position of the other axis beyond which
             movement is prohibited (in mm).
           - max_position/min_position: Software-defined motion limits.
           - max_single_move: Maximum allowed distance for a single move.

        3. Timing:
           - homing_timeout: Maximum duration for a homing operation.

        4. Conversion:
           - velocity_conversion_factor: Factor for velocity unit conversion.

        Returns:
            dict: A dictionary containing all configuration values.
        """
        self.declare_parameter('use_sim_time', False)
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('serial_number', '00000000')
        self.declare_parameter('collision_threshold', 300.0)
        self.declare_parameter('namespace', 'promoc_assembly')
        self.declare_parameter('max_position', 300.0)
        self.declare_parameter('min_position', 0.0)
        self.declare_parameter('max_single_move', 300.0)
        self.declare_parameter('homing_timeout', 180.0)
        self.declare_parameter('velocity_conversion_factor', 0.018)

        return {
            'use_sim_time': self.get_parameter('use_sim_time').value,
            'serial_port': self.get_parameter('serial_port').value,
            'serial_number': self.get_parameter('serial_number').value,
            'collision_threshold': self.get_parameter('collision_threshold').value,
            'namespace': self.get_parameter('namespace').value,
            'max_position': self.get_parameter('max_position').value,
            'min_position': self.get_parameter('min_position').value,
            'max_single_move': self.get_parameter('max_single_move').value,
            'homing_timeout': self.get_parameter('homing_timeout').value,
            'velocity_conversion_factor': self.get_parameter('velocity_conversion_factor').value,
        }

    def _setup_ros_communication(self):
        """
        Sets up all ROS2 communication components.

        Creates:
        --------
        1. Publisher:
           - `/{namespace}/{node_name}/position`: Publishes current position at 10 Hz.

        2. Subscriber:
           - Subscribes to the other axis's position for collision avoidance.

        3. Services:
           - `move_absolute`: Move to an absolute position.
           - `move_relative`: Move by a relative distance.
           - `home`: Perform the homing sequence.
           - `get_position`: Request the current position.
           - `get_operation_status`: Get the status of an ongoing operation.
           - `set/get_velocity_parameters`: Set or get velocity settings.
           - `shutdown`: Shut down the device.
           - `emergency_stop`: Immediately stop all motion.
           - `jog_axis`: Move incrementally.
        """
        try:
            node_name = self.get_name()
            self.get_logger().info(
                f'Setting up ROS communication for {node_name}...'
            )

            # ── Publisher & Timer ──
            self.position_publisher = self.create_publisher(
                LinearAxisInfo,
                f"/{self.config['namespace']}/{node_name}/position",
                10,
            )
            self.create_timer(0.1, self.publish_position)
            self.get_logger().info('Publisher and timer created')

            # ── Subscriber for Collision Avoidance ──
            # Subscribes to the position of the other axis (X↔Z).
            axis_type = self.interface.driver.get_axis_type()
            other_axis = 'z' if axis_type == 'x' else 'x'
            self.create_subscription(
                LinearAxisInfo,
                f"/{self.config['namespace']}/lts300_{other_axis}_axis/position",
                self.other_axis_position_callback,
                10)
            self.get_logger().info(f'Subscriber created for {other_axis}-axis')

            # ── Services ──
            # The other_axis_position is passed to move callbacks for collision checking.
            self.create_service(
                MoveAbsolute,
                f'{node_name}/move_absolute',
                lambda req, res: self.callbacks.callback_move_absolute(
                    req,
                    res,
                    self.other_axis_position,
                ),
            )
            self.create_service(
                MoveRelativ,
                f'{node_name}/move_relative',
                lambda req, res: self.callbacks.callback_move_relative(
                    req,
                    res,
                    self.other_axis_position,
                ),
            )
            self.create_service(
                Home, f'{node_name}/home', self.callbacks.callback_home)
            self.create_service(
                GetPosition, f'{node_name}/get_position', self.callbacks.callback_get_position)
            self.create_service(
                GetOperationStatus,
                f'{node_name}/get_operation_status',
                self.callbacks.callback_get_operation_status,
            )
            self.create_service(
                SetVelocityParameters,
                f'{node_name}/set_velocity_parameters',
                self.callbacks.callback_set_velocity_parameters,
            )
            self.create_service(
                GetVelocityParameters,
                f'{node_name}/get_velocity_parameters',
                self.callbacks.callback_get_velocity_parameters,
            )
            self.create_service(
                ShutdownLinearAxis, f'{node_name}/shutdown', self.callbacks.callback_shutdown)
            self.create_service(
                EmergencyStop,
                f'{node_name}/emergency_stop',
                self.callbacks.callback_emergency_stop,
            )
            self.create_service(
                JogAxis, f'{node_name}/jog_axis', self.callbacks.callback_jog_axis)
            self.get_logger().info('All services created')

        except Exception as e:
            self.get_logger().error(
                f'Error in _setup_ros_communication: {e}'
            )
            raise

    def publish_position(self):
        """Publishes the current axis position."""
        if not self.interface.is_connected:
            self.get_logger().debug('Skipping position publish - interface not connected')
            return
        try:
            msg = LinearAxisInfo()
            driver = self.interface.driver

            # Get position (this is usually reliable)
            msg.axis_position = driver.get_position()
            msg.serial_number = driver.get_serial_number()

            # Set axis_type based on node name instead of relying on the driver method.
            node_name = self.get_name()
            if 'x_axis' in node_name:
                msg.axis_type = 'x'
            elif 'z_axis' in node_name:
                msg.axis_type = 'z'
            else:
                msg.axis_type = 'unknown'

            # Use our internal operation status, which is more reliable than the hardware's is_moving().
            operation_status, _ = self.callbacks.get_operation_status()
            msg.operation_status = operation_status.value

            self.position_publisher.publish(msg)
            self.get_logger().debug(
                f'Published position: {msg.axis_position:.2f}mm, '
                f'status: {operation_status.value}'
            )

        except Exception as e:
            # Reduce error logging frequency to avoid spamming the console.
            if not hasattr(self, '_last_publish_error_time'):
                self._last_publish_error_time = 0

            import time
            current_time = time.time()
            if current_time - self._last_publish_error_time > 5.0:
                # Log the error at most once every 5 seconds.
                self.get_logger().error(f'Error publishing position: {e}')
                self._last_publish_error_time = current_time
            else:
                self.get_logger().debug(
                    f'Position publish error (suppressed): {e}'
                )

    def other_axis_position_callback(self, msg):
        """Stores the position of the other axis."""
        self.other_axis_position = msg.axis_position

    def shutdown_device(self):
        """Performs a clean shutdown of the device."""
        self.get_logger().info('Homing device before shutdown...')
        try:
            self.interface.driver.home()
        except Exception as e:
            self.get_logger().error(f'Error during homing on shutdown: {e}')
        finally:
            self.interface.disconnect()


def main(args=None):
    rclpy.init(args=args)
    node = LTS300Node()

    # Check if the node was initialized successfully.
    # CHANGED: Check the driver's 'connected' property directly instead of interface.is_connected.
    try:
        connected = (
            hasattr(node, 'interface')
            and hasattr(node.interface, 'driver')
            and node.interface.driver.connected
        )
        if connected:
            node.get_logger().info('Node successfully initialized, starting spin...')
            try:
                rclpy.spin(node)
            except KeyboardInterrupt:
                node.get_logger().info('Keyboard interrupt, shutting down...')
            finally:
                node.get_logger().info('Final shutdown procedure...')
                node.shutdown_device()
                node.destroy_node()
                if rclpy.ok():
                    rclpy.shutdown()
        else:
            node.get_logger().error('Node initialization failed, exiting...')
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
    except Exception as e:
        node.get_logger().error(f'Error in main: {e}')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
