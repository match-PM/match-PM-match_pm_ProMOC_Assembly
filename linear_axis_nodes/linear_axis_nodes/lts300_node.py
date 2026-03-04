r"""
ROS2 Node for Thorlabs LTS300 Linear Axis Control.

This module implements the LTS300Node, which is the central orchestrator
for controlling a Thorlabs LTS300 linear stage (300mm travel).

Architecture Overview:
======================
The node follows a dependency injection pattern similar to the mover_node:

    LTS300Node (Orchestrator)
        │
    ├── Config (LTS300NodeConfig) → Typed ROS parameter configuration
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
    ros2 service call /promoc/linear_axis/lts300_x_axis/move_absolute \
        promoc_assembly_interfaces/srv/MoveAbsolute "{axis_position: 150.0}"

    # Perform homing:
    ros2 service call /promoc/linear_axis/lts300_x_axis/home promoc_assembly_interfaces/srv/Home
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
    MoveRelative,
    Stop,
    SetVelocityParameters,
    ShutdownLinearAxis,
)
import rclpy
from rclpy.node import Node

from .config import LTS300NodeConfig
from .helpers.lts300_interface import Lts300Interface
from .services.callbacks import ServiceCallbacks
from promoc_core.logging import TaggedLogger, LogTags
from promoc_core.service_alias import register_service_alias_pair


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
        config (LTS300NodeConfig): Typed node configuration.
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
        super().__init__("lts300_node")

        # Setup TaggedLogger for this node
        self.log = TaggedLogger(self.get_logger(), LogTags.LTS)

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: Load Configuration
        # ══════════════════════════════════════════════════════════════════════
        self.config = self._load_config()

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: Create Components
        # ══════════════════════════════════════════════════════════════════════
        # Interface gets [LTS:CONN] logger
        self.interface = Lts300Interface(
            TaggedLogger(self.get_logger(), LogTags.LTS_CONN), self.config
        )
        # Callbacks gets raw logger (wraps it internally with [LTS:MOVE])
        self.callbacks = ServiceCallbacks(self.log, self.interface, self.config)
        self._service_alias_handles = []

        try:
            # ══════════════════════════════════════════════════════════════════
            # PHASE 3: Establish Connection
            # ══════════════════════════════════════════════════════════════════
            if not self.interface.connect():
                self.log.error("Shutting down node due to connection failure.")
                self.log.error("Node initialization failed, exiting...")
                return
            self.log.info("Connection successful, continuing initialization...")

            # ══════════════════════════════════════════════════════════════════
            # PHASE 4: Set up ROS2 Communication
            # ══════════════════════════════════════════════════════════════════
            self.other_axis_position = None
            self._setup_ros_communication()

            # ══════════════════════════════════════════════════════════════════
            # PHASE 5: Post-Initialization Setup
            # ══════════════════════════════════════════════════════════════════
            try:
                # Set initial velocity parameters beim Start
                self.log.info(
                    "Setting initial velocity parameters: min_vel=0.0, accel=0.002, max_vel=10"
                )
                request = SetVelocityParameters.Request()
                request.min_velocity = 0.0
                request.acceleration = 0.002
                request.max_velocity = 10.0
                response = SetVelocityParameters.Response()
                self.callbacks.callback_set_velocity_parameters(request, response)

                if response.success:
                    self.log.info(
                        f"Initial velocity parameters set successfully: {response.status_message}"
                    )
                else:
                    self.log.warn(
                        f"Failed to set initial velocity parameters: {response.status_message}"
                    )

            except Exception as e:
                self.log.warn(f"Failed to set initial velocity parameters: {e}")

            self.log.info(
                f"{self.get_name()} with S/N {self.config.serial_number} is running."
            )
            self.log.info("Node initialization complete!")

        except Exception as e:
            self.log.error(f"Exception during initialization: {e}")
            self.log.error("Node initialization failed, exiting...")
            raise

    def _load_config(self) -> LTS300NodeConfig:
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
            LTS300NodeConfig: Typed configuration object.
        """
        if not self.has_parameter("use_sim_time"):
            self.declare_parameter("use_sim_time", False)
        self.declare_parameter("serial_port", "/dev/ttyUSB0")
        self.declare_parameter("serial_number", "00000000")
        self.declare_parameter("collision_threshold", 300.0)
        self.declare_parameter("namespace", "promoc_assembly")
        self.declare_parameter("max_position", 300.0)
        self.declare_parameter("min_position", 0.0)
        self.declare_parameter("max_single_move", 300.0)
        self.declare_parameter("homing_timeout", 180.0)
        self.declare_parameter("velocity_conversion_factor", 0.018)
        self.declare_parameter("position_poll_interval_s", 0.1)

        return LTS300NodeConfig(
            use_sim_time=bool(self.get_parameter("use_sim_time").value),
            serial_port=str(self.get_parameter("serial_port").value),
            serial_number=str(self.get_parameter("serial_number").value),
            collision_threshold=float(self.get_parameter("collision_threshold").value),
            namespace=str(self.get_parameter("namespace").value),
            max_position=float(self.get_parameter("max_position").value),
            min_position=float(self.get_parameter("min_position").value),
            max_single_move=float(self.get_parameter("max_single_move").value),
            homing_timeout=float(self.get_parameter("homing_timeout").value),
            velocity_conversion_factor=float(
                self.get_parameter("velocity_conversion_factor").value
            ),
            position_poll_interval_s=float(
                self.get_parameter("position_poll_interval_s").value
            ),
        )

    def _setup_ros_communication(self):
        """
        Sets up all ROS2 communication components.

        Creates:
        --------
        1. Publisher:
           - Canonical: `/promoc/linear_axis/{node_name}/position`
           - Legacy: `/{namespace}/{node_name}/position`

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
            self.log.info(f"Setting up ROS communication for {node_name}...")

            # ── Publisher & Timer ──
            self.position_publisher = self.create_publisher(
                LinearAxisInfo,
                f"/{self.config.namespace}/{node_name}/position",
                10,
            )
            self.position_publisher_canonical = self.create_publisher(
                LinearAxisInfo,
                f"/promoc/linear_axis/{node_name}/position",
                10,
            )
            self.position_timer = self.create_timer(0.1, self.publish_position)
            self.log.info("Publisher and timer created")

            # ── Subscriber for Collision Avoidance ──
            # Subscribes to the position of the other axis (X<->Z).
            axis_type = self.interface.driver.get_axis_type()
            other_axis = "z" if axis_type == "x" else "x"
            self.other_axis_subscription = self.create_subscription(
                LinearAxisInfo,
                f"/promoc/linear_axis/lts300_{other_axis}_axis/position",
                self.other_axis_position_callback,
                10,
            )
            self.other_axis_subscription_legacy = self.create_subscription(
                LinearAxisInfo,
                f"/{self.config.namespace}/lts300_{other_axis}_axis/position",
                self.other_axis_position_callback_legacy,
                10,
            )
            self.log.info(f"Subscriber created for {other_axis}-axis")

            # ── Services ──
            # The other_axis_position is passed to move callbacks for collision checking.
            self._create_service_alias_pair(
                node_name,
                MoveAbsolute,
                "move_absolute",
                lambda req, res: self.callbacks.callback_move_absolute(
                    req,
                    res,
                    self.other_axis_position,
                ),
            )
            self._create_service_alias_pair(
                node_name,
                MoveRelative,
                "move_relative",
                lambda req, res: self.callbacks.callback_move_relative(
                    req,
                    res,
                    self.other_axis_position,
                ),
            )
            self._create_service_alias_pair(
                node_name, Home, "home", self.callbacks.callback_home
            )
            self._create_service_alias_pair(
                node_name,
                GetPosition,
                "get_position",
                self.callbacks.callback_get_position,
            )
            self._create_service_alias_pair(
                node_name,
                GetOperationStatus,
                "get_operation_status",
                self.callbacks.callback_get_operation_status,
            )
            self._create_service_alias_pair(
                node_name,
                SetVelocityParameters,
                "set_velocity_parameters",
                self.callbacks.callback_set_velocity_parameters,
            )
            self._create_service_alias_pair(
                node_name,
                GetVelocityParameters,
                "get_velocity_parameters",
                self.callbacks.callback_get_velocity_parameters,
            )
            self._create_service_alias_pair(
                node_name,
                ShutdownLinearAxis,
                "shutdown",
                self.callbacks.callback_shutdown,
            )
            self._create_service_alias_pair(
                node_name,
                EmergencyStop,
                "emergency_stop",
                self.callbacks.callback_emergency_stop,
            )
            self._create_service_alias_pair(
                node_name, Stop, "stop", self.callbacks.callback_stop
            )
            self._create_service_alias_pair(
                node_name, JogAxis, "jog_axis", self.callbacks.callback_jog_axis
            )
            self.log.info("All services created")

        except Exception as e:
            self.log.error(f"Error in _setup_ros_communication: {e}")
            raise

    def publish_position(self):
        """Publishes the current axis position."""
        if not self.interface.is_connected:
            self.log.debug("Skipping position publish - interface not connected")
            return
        try:
            msg = LinearAxisInfo()
            driver = self.interface.driver

            # Get position (this is usually reliable)
            msg.axis_position = driver.get_position()
            msg.serial_number = driver.get_serial_number()

            # Set axis_type based on node name instead of relying on the driver method.
            node_name = self.get_name()
            if "x_axis" in node_name:
                msg.axis_type = "x"
            elif "z_axis" in node_name:
                msg.axis_type = "z"
            else:
                msg.axis_type = "unknown"

            # Use our internal operation status, which is more reliable than the hardware's is_moving().
            operation_status, _ = self.callbacks.get_operation_status()
            msg.operation_status = operation_status.value

            self.position_publisher.publish(msg)
            self.position_publisher_canonical.publish(msg)
            self.log.debug(
                f"Published position: {msg.axis_position:.2f}mm, "
                f"status: {operation_status.value}"
            )

        except Exception as e:
            # Reduce error logging frequency to avoid spamming the console.
            if not hasattr(self, "_last_publish_error_time"):
                self._last_publish_error_time = 0

            import time

            current_time = time.time()
            if current_time - self._last_publish_error_time > 5.0:
                # Log the error at most once every 5 seconds.
                self.log.error(f"Error publishing position: {e}")
                self._last_publish_error_time = current_time
            else:
                self.log.debug(f"Position publish error (suppressed): {e}")

    def _create_service_alias_pair(
        self, node_name: str, service_type, suffix: str, callback
    ):
        legacy_path = f"{node_name}/{suffix}"
        canonical_path = f"/promoc/linear_axis/{node_name}/{suffix}"
        canonical_service, legacy_service = register_service_alias_pair(
            node=self,
            service_type=service_type,
            canonical_path=canonical_path,
            legacy_path=legacy_path,
            callback=callback,
            warn=self.log.warning,
        )
        self._service_alias_handles.extend((canonical_service, legacy_service))

    def other_axis_position_callback(self, msg):
        """Stores the position of the other axis."""
        self.other_axis_position = msg.axis_position

    def other_axis_position_callback_legacy(self, msg):
        """Release N compatibility for legacy cross-axis topic."""
        if not hasattr(self, "_legacy_cross_axis_topic_warned"):
            self._legacy_cross_axis_topic_warned = False
        if not self._legacy_cross_axis_topic_warned:
            axis_type = self.interface.driver.get_axis_type()
            other_axis = "z" if axis_type == "x" else "x"
            self.log.warning(
                f"Deprecated topic '/{self.config.namespace}/lts300_{other_axis}_axis/position' received. "
                f"Use '/promoc/linear_axis/lts300_{other_axis}_axis/position' instead."
            )
            self._legacy_cross_axis_topic_warned = True
        self.other_axis_position_callback(msg)

    def shutdown_device(self):
        """Performs a clean shutdown of the device."""
        self.log.info("Shutting down device...")
        try:
            # Check if interface exists and driver is connected
            if not hasattr(self, "interface"):
                self.log.warn("No interface found during shutdown")
                return

            if not hasattr(self.interface, "driver"):
                self.log.warn("No driver found during shutdown")
                return

            # Check connection status
            if not self.interface.driver.connected:
                self.log.warn("Driver not connected during shutdown")
                return

            self.log.info("Device is connected, starting shutdown sequence...")

            # Move to 15mm before homing (to speed up shutdown)
            try:
                current_pos = self.interface.driver.get_position()
                self.log.info(f"Current position: {current_pos:.2f}mm")
                self.log.info("Moving to 15.0mm before homing...")

                success = self.interface.driver.move_absolute(15.0, wait=True)
                if success:
                    final_pos = self.interface.driver.get_position()
                    self.log.info(
                        f"Successfully moved to 15.0mm (actual: {final_pos:.2f}mm)"
                    )
                else:
                    self.log.warn("move_absolute returned False")
            except Exception as e:
                self.log.error(f"Failed to move to 15.0mm: {e}", exc_info=True)

            # Homing
            try:
                self.log.info("Starting homing sequence...")
                self.interface.driver.home()
                self.log.info("Homing completed")
            except Exception as e:
                self.get_logger().error(f"Homing failed: {e}", exc_info=True)

        except Exception as e:
            self.get_logger().error(
                f"Error during shutdown sequence: {e}", exc_info=True
            )
        finally:
            if hasattr(self, "interface"):
                self.get_logger().info("Disconnecting interface...")
                self.interface.disconnect()
                self.get_logger().info("Interface disconnected")


def main(args=None):
    rclpy.init(args=args)
    node = LTS300Node()

    # Check if the node was initialized successfully.
    # CHANGED: Check the driver's 'connected' property directly instead of interface.is_connected.
    try:
        connected = (
            hasattr(node, "interface")
            and hasattr(node.interface, "driver")
            and node.interface.driver.connected
        )
        if connected:
            node.log.info("Node successfully initialized, starting spin...")
            try:
                rclpy.spin(node)
            except KeyboardInterrupt:
                node.log.info("Keyboard interrupt, shutting down...")
            finally:
                node.log.info("Final shutdown procedure...")
                node.shutdown_device()
                node.destroy_node()
                if rclpy.ok():
                    rclpy.shutdown()
        else:
            node.get_logger().error("Node initialization failed, exiting...")
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
    except Exception as e:
        node.get_logger().error(f"Error in main: {e}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
