import dataclasses

@dataclasses.dataclass
class Lts300Config:
    """
    A dataclass to hold all parameters for the LTS300 node,
    loaded from the ROS 2 parameter server.
    """
    debug_mode: bool
    use_sim_time: bool
    serial_port: str
    serial_number: str
    collision_threshold: float
    namespace: str
    max_position: float 
    min_position: float 
    max_single_move: float
    homing_timeout: float