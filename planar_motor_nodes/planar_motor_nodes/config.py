"""Typed configuration model for the planar motor node."""

from dataclasses import dataclass


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
