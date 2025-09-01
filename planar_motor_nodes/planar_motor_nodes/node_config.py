import dataclasses

@dataclasses.dataclass
class NodeConfig:
    """
    A simple dataclass to hold all node parameters.
    This makes passing configuration around clean and explicit.
    """
    debug_mode: bool
    xy_tolerance: float
    six_d_tolerance: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
