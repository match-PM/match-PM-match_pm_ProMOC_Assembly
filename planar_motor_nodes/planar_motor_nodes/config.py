"""Typed configuration model for the planar mover node stack."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MoverNodeConfig:
    use_mock: bool
    xbot_id: int
    publish_rate: float
    pmc_ip: str
    xy_tolerance: float
    six_d_tolerance: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
