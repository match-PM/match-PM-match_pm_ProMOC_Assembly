"""Configuration for the unified linear-axis node."""

from __future__ import annotations

from dataclasses import dataclass

from rclpy.node import Node


DEFAULT_LINEAR_AXIS_PARAMETERS = {
    "axis_id": "",
    "driver_mode": "hardware",
    "serial_number": "",
    "serial_port": "",
    "min_position": 0.0,
    "max_position": 300.0,
    "default_velocity": 5.0,
    "default_acceleration": 1.0,
    "movement_timeout": 60.0,
    "homing_timeout": 180.0,
    "state_publish_rate_hz": 10.0,
}


@dataclass(frozen=True)
class LinearAxisConfig:
    """Typkonfiguration fuer eine Linearachsen-Instanz (X oder Z).

    Felder:
    - axis_id: "x" oder "z"
    - driver_mode: "hardware" (Thorlabs LTS300) oder "mock"
    - serial_number: Erwartete Seriennummer (leer = beliebig)
    - serial_port: Serieller Port (/dev/ttyUSB* oder /dev/serial/by-id/...)
    - min/max_position: Soft-Limits in mm
    - default_velocity/max_acceleration: Default-Bewegungsparameter
    - movement_timeout/homing_timeout: Timeouts in Sekunden
    - state_publish_rate_hz: Frequenz fuer Status-Publishing
    """
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
        """Deklariert und laedt alle ROS-Parameter fuer die Achsenkonfiguration."""
        if not node.has_parameter("use_sim_time"):
            node.declare_parameter("use_sim_time", False)
        for name, default in DEFAULT_LINEAR_AXIS_PARAMETERS.items():
            node.declare_parameter(name, default)

        values = {
            name: node.get_parameter(name).value
            for name in DEFAULT_LINEAR_AXIS_PARAMETERS
        }

        return cls(
            axis_id=str(values["axis_id"]).strip().lower(),
            driver_mode=str(values["driver_mode"]).strip().lower(),
            serial_number=str(values["serial_number"]),
            serial_port=str(values["serial_port"]),
            min_position=float(values["min_position"]),
            max_position=float(values["max_position"]),
            default_velocity=float(values["default_velocity"]),
            default_acceleration=float(values["default_acceleration"]),
            movement_timeout=float(values["movement_timeout"]),
            homing_timeout=float(values["homing_timeout"]),
            state_publish_rate_hz=float(values["state_publish_rate_hz"]),
        )

    def validate(self) -> None:
        """Validiert die Konfiguration (axis_id, driver_mode, Grenzen, positive Werte)."""
        if self.axis_id not in {"x", "z"}:
            raise ValueError("axis_id must be 'x' or 'z'")
        if self.driver_mode not in {"hardware", "mock"}:
            raise ValueError("driver_mode must be 'hardware' or 'mock'")
        if self.max_position <= self.min_position:
            raise ValueError("max_position must be greater than min_position")
        for name in (
            "default_velocity",
            "default_acceleration",
            "movement_timeout",
            "homing_timeout",
            "state_publish_rate_hz",
        ):
            if getattr(self, name) <= 0.0:
                raise ValueError(f"{name} must be greater than 0")
