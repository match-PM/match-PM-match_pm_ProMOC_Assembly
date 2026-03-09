"""Domain data models for planar-motor runtime."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bounds3D:
    """Simple positional bounds model in meters."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
