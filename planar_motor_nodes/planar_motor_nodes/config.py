"""Typed configuration model for the planar motor node."""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class MoverNodeConfig:
    driver_mode: str
    xbot_id: int
    publish_rate: float
    pmc_ip: str
    auto_activate: bool
    movement_timeout: float
    mock_xbot_count: int
    xy_tolerance: float
    six_d_tolerance: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
    default_xy_vel: float
    default_xy_max_accel: float
    default_z_vel: float
    default_z_max_accel: float
    default_rx_vel: float
    default_ry_vel: float
    default_rz_vel: float

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "MoverNodeConfig":
        """Build typed config from ROS parameter values."""
        return cls(
            driver_mode=str(values["driver_mode"]),
            xbot_id=int(values["xbot_id"]),
            publish_rate=float(values["publish_rate"]),
            pmc_ip=str(values["pmc_ip"]),
            auto_activate=bool(values["auto_activate"]),
            movement_timeout=float(values["movement_timeout"]),
            mock_xbot_count=int(values["mock_xbot_count"]),
            xy_tolerance=float(values["xy_tolerance"]),
            six_d_tolerance=float(values["six_d_tolerance"]),
            x_min=float(values["x_min"]),
            x_max=float(values["x_max"]),
            y_min=float(values["y_min"]),
            y_max=float(values["y_max"]),
            z_min=float(values["z_min"]),
            z_max=float(values["z_max"]),
            default_xy_vel=float(values["default_xy_vel"]),
            default_xy_max_accel=float(values["default_xy_max_accel"]),
            default_z_vel=float(values["default_z_vel"]),
            default_z_max_accel=float(values["default_z_max_accel"]),
            default_rx_vel=float(values["default_rx_vel"]),
            default_ry_vel=float(values["default_ry_vel"]),
            default_rz_vel=float(values["default_rz_vel"]),
        )


DEFAULT_MOVER_NODE_PARAMETERS = {
    "driver_mode": "hardware",
    "xbot_id": 0,
    "publish_rate": 10.0,
    "pmc_ip": "192.168.10.100",
    "auto_activate": True,
    "movement_timeout": 10.0,
    "mock_xbot_count": 1,
    "xy_tolerance": 0.001,
    "six_d_tolerance": 0.001,
    "x_min": 0.055,
    "x_max": 0.420,
    "y_min": 0.055,
    "y_max": 0.180,
    "z_min": 0.0,
    "z_max": 0.004,
    "default_xy_vel": 0.05,
    "default_xy_max_accel": 0.2,
    "default_z_vel": 0.01,
    "default_z_max_accel": 0.05,
    "default_rx_vel": 0.17453292519943295,
    "default_ry_vel": 0.17453292519943295,
    "default_rz_vel": 0.2617993877991494,
}
