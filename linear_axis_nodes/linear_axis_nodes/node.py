r"""
ROS2 node for Thorlabs LTS300 linear-axis control.

Canonical entry point for the `linear_axis_nodes` runtime package.
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
from .drivers import create_linear_axis_driver, connect_linear_axis_driver
from .services import ServiceHandlers
from promoc_core.logging import TaggedLogger, LogTags


class LTS300Node(Node):
    """ROS2 node for controlling a single LTS300 axis."""

    def __init__(self):
        super().__init__("lts300_node")

        self.log = TaggedLogger(self.get_logger(), LogTags.LTS)
        self.config = self._load_config()
        self.driver = create_linear_axis_driver(
            TaggedLogger(self.get_logger(), LogTags.LTS_CONN),
            self.config,
        )
        self.callbacks = ServiceHandlers(self.log, self.driver, self.config)

        try:
            if not connect_linear_axis_driver(self.driver, self.log, self.config):
                self.log.error("Shutting down node due to connection failure.")
                return

            self.log.info("Connection successful, continuing initialization...")
            self.other_axis_position = None
            self._setup_ros_communication()

            try:
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
            except Exception as exc:
                self.log.warn(f"Failed to set initial velocity parameters: {exc}")

            self.log.info(
                f"{self.get_name()} with S/N {self.config.serial_number} is running."
            )
            self.log.info("Node initialization complete!")
        except Exception as exc:
            self.log.error(f"Exception during initialization: {exc}")
            self.log.error("Node initialization failed, exiting...")
            raise

    def _load_config(self) -> LTS300NodeConfig:
        if not self.has_parameter("use_sim_time"):
            self.declare_parameter("use_sim_time", False)
        self.declare_parameter("serial_port", "/dev/ttyUSB0")
        self.declare_parameter("serial_number", "00000000")
        self.declare_parameter("collision_threshold", 300.0)
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
        node_name = self.get_name()
        self.log.info(f"Setting up ROS communication for {node_name}...")

        self.position_publisher = self.create_publisher(
            LinearAxisInfo,
            f"/promoc/linear_axis/{node_name}/position",
            10,
        )
        self.position_timer = self.create_timer(0.1, self.publish_position)

        axis_type = self.driver.get_axis_type()
        other_axis = "z" if axis_type == "x" else "x"
        self.other_axis_subscription = self.create_subscription(
            LinearAxisInfo,
            f"/promoc/linear_axis/lts300_{other_axis}_axis/position",
            self.other_axis_position_callback,
            10,
        )

        service_specs = [
            (
                MoveAbsolute,
                "move_absolute",
                lambda req, res: self.callbacks.callback_move_absolute(
                    req,
                    res,
                    self.other_axis_position,
                ),
            ),
            (
                MoveRelative,
                "move_relative",
                lambda req, res: self.callbacks.callback_move_relative(
                    req,
                    res,
                    self.other_axis_position,
                ),
            ),
            (Home, "home", self.callbacks.callback_home),
            (GetPosition, "get_position", self.callbacks.callback_get_position),
            (
                GetOperationStatus,
                "get_operation_status",
                self.callbacks.callback_get_operation_status,
            ),
            (
                SetVelocityParameters,
                "set_velocity_parameters",
                self.callbacks.callback_set_velocity_parameters,
            ),
            (
                GetVelocityParameters,
                "get_velocity_parameters",
                self.callbacks.callback_get_velocity_parameters,
            ),
            (ShutdownLinearAxis, "shutdown", self.callbacks.callback_shutdown),
            (EmergencyStop, "emergency_stop", self.callbacks.callback_emergency_stop),
            (Stop, "stop", self.callbacks.callback_stop),
            (JogAxis, "jog_axis", self.callbacks.callback_jog_axis),
        ]

        for service_type, suffix, callback in service_specs:
            self.create_service(
                service_type,
                f"/promoc/linear_axis/{node_name}/{suffix}",
                callback,
            )
        self.log.info("All services created")

    def publish_position(self):
        if not getattr(self.driver, "connected", False):
            self.log.debug("Skipping position publish - driver not connected")
            return
        try:
            msg = LinearAxisInfo()
            msg.axis_position = self.driver.get_position()
            msg.serial_number = self.driver.get_serial_number()

            node_name = self.get_name()
            if "x_axis" in node_name:
                msg.axis_type = "x"
            elif "z_axis" in node_name:
                msg.axis_type = "z"
            else:
                msg.axis_type = "unknown"

            operation_status, _ = self.callbacks.get_operation_status()
            msg.operation_status = operation_status.value

            self.position_publisher.publish(msg)
            self.log.debug(
                f"Published position: {msg.axis_position:.2f}mm, "
                f"status: {operation_status.value}"
            )
        except Exception as exc:
            if not hasattr(self, "_last_publish_error_time"):
                self._last_publish_error_time = 0
            import time
            current_time = time.time()
            if current_time - self._last_publish_error_time > 5.0:
                self.log.error(f"Error publishing position: {exc}")
                self._last_publish_error_time = current_time
            else:
                self.log.debug(f"Position publish error (suppressed): {exc}")

    def other_axis_position_callback(self, msg):
        self.other_axis_position = msg.axis_position

    def shutdown_device(self):
        self.log.info("Shutting down device...")
        try:
            if not hasattr(self, "driver") or not getattr(self.driver, "connected", False):
                self.log.warn("Driver not connected during shutdown")
                return

            self.log.info("Device is connected, starting shutdown sequence...")
            try:
                current_pos = self.driver.get_position()
                self.log.info(f"Current position: {current_pos:.2f}mm")
                self.log.info("Moving to 15.0mm before homing...")
                self.driver.move_absolute(15.0)
                final_pos = self.driver.get_position()
                self.log.info(
                    f"Successfully moved to 15.0mm (actual: {final_pos:.2f}mm)"
                )
            except Exception as exc:
                self.log.error(f"Failed to move to 15.0mm: {exc}", exc_info=True)

            try:
                self.log.info("Starting homing sequence...")
                self.driver.home()
                self.log.info("Homing completed")
            except Exception as exc:
                self.get_logger().error(f"Homing failed: {exc}", exc_info=True)
        except Exception as exc:
            self.get_logger().error(
                f"Error during shutdown sequence: {exc}", exc_info=True
            )
        finally:
            if hasattr(self, "driver"):
                self.get_logger().info("Disconnecting driver...")
                self.driver.disconnect()
                self.get_logger().info("Driver disconnected")


def main(args=None):
    rclpy.init(args=args)
    node = LTS300Node()

    try:
        connected = hasattr(node, "driver") and getattr(node.driver, "connected", False)
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
    except Exception as exc:
        node.get_logger().error(f"Error in main: {exc}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
