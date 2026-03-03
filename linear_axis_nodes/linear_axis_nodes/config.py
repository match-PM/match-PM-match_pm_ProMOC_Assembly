"""Typed configuration model for the LTS300 node stack."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LTS300NodeConfig:
    use_sim_time: bool
    serial_port: str
    serial_number: str
    collision_threshold: float
    namespace: str
    max_position: float
    min_position: float
    max_single_move: float
    homing_timeout: float
    velocity_conversion_factor: float
    position_poll_interval_s: float
