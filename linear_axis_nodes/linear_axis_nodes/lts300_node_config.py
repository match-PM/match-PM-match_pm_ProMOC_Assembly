import dataclasses

@dataclasses.dataclass
class Lts300Config:
    """
    A dataclass to hold all parameters for the LTS300 node,
    loaded from the ROS 2 parameter server.
    """
    use_sim_time: bool
    serial_port: str
    serial_number: str
    collision_threshold: float
    namespace: str
    max_position: float 
    min_position: float 
    max_single_move: float
    homing_timeout: float
    # Velocity conversion factor (from device units to mm/s)
    # Based on measurements: 500 device units ≈ 9.0 mm/s, 100 device units ≈ 1.85 mm/s
    # Therefore: conversion factor ≈ 0.018 mm/s per device unit
    velocity_conversion_factor: float = 0.018