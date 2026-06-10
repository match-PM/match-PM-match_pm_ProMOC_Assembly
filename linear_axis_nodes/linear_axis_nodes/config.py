"""Configuration for the unified linear-axis node."""

from __future__ import annotations

from dataclasses import dataclass

from rclpy.node import Node


@dataclass(frozen=True)
class LinearAxisConfig:
    """Typed runtime configuration for one axis instance."""

    axis_id: str
    driver_mode: str
    serial_number: str
    serial_port: str
    min_position: float
    max_position: float
    default_velocity: float
    default_acceleration: float
    movement_timeout: float
    homing_timeout: float
    state_publish_rate_hz: float

    @classmethod
    def from_node(cls, node: Node) -> "LinearAxisConfig":
        """Declare and load the parameters required by the unified axis node."""
        if not node.has_parameter("use_sim_time"):
            node.declare_parameter("use_sim_time", False)
        node.declare_parameter("axis_id", "")
        node.declare_parameter("driver_mode", "hardware")
        node.declare_parameter("serial_number", "")
        node.declare_parameter("serial_port", "")
        node.declare_parameter("min_position", 0.0)
        node.declare_parameter("max_position", 300.0)
        node.declare_parameter("default_velocity", 5.0)
        node.declare_parameter("default_acceleration", 1.0)
        node.declare_parameter("movement_timeout", 60.0)
        node.declare_parameter("homing_timeout", 180.0)
        node.declare_parameter("state_publish_rate_hz", 10.0)

        return cls(
            axis_id=str(node.get_parameter("axis_id").value),
            driver_mode=str(node.get_parameter("driver_mode").value),
            serial_number=str(node.get_parameter("serial_number").value),
            serial_port=str(node.get_parameter("serial_port").value),
            min_position=float(node.get_parameter("min_position").value),
            max_position=float(node.get_parameter("max_position").value),
            default_velocity=float(node.get_parameter("default_velocity").value),
            default_acceleration=float(
                node.get_parameter("default_acceleration").value
            ),
            movement_timeout=float(node.get_parameter("movement_timeout").value),
            homing_timeout=float(node.get_parameter("homing_timeout").value),
            state_publish_rate_hz=float(
                node.get_parameter("state_publish_rate_hz").value
            ),
        )

    def validate(self) -> None:
        """Raise ValueError when the configuration cannot be used safely."""
        if self.axis_id not in {"x", "z"}:
            raise ValueError("axis_id must be 'x' or 'z'")
        if self.driver_mode not in {"hardware", "mock"}:
            raise ValueError("driver_mode must be 'hardware' or 'mock'")
        if self.max_position <= self.min_position:
            raise ValueError("max_position must be greater than min_position")
        if self.default_velocity <= 0.0:
            raise ValueError("default_velocity must be greater than 0")
        if self.default_acceleration <= 0.0:
            raise ValueError("default_acceleration must be greater than 0")
        if self.movement_timeout <= 0.0:
            raise ValueError("movement_timeout must be greater than 0")
        if self.homing_timeout <= 0.0:
            raise ValueError("homing_timeout must be greater than 0")
        if self.state_publish_rate_hz <= 0.0:
            raise ValueError("state_publish_rate_hz must be greater than 0")
