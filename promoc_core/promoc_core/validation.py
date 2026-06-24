"""Small validation helpers shared by the ROS nodes."""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Bounds3D:
    """3D bounds for workspace checks."""

    x_min: float = 0.0
    x_max: float = 1.0
    y_min: float = 0.0
    y_max: float = 1.0
    z_min: float = 0.0
    z_max: float = 1.0

    def contains(self, x: float, y: float, z: float) -> bool:
        """Checks if the point is within the bounds."""
        return (
            self.x_min <= x <= self.x_max
            and self.y_min <= y <= self.y_max
            and self.z_min <= z <= self.z_max
        )

    def clamp_position(
        self, x: float, y: float, z: float
    ) -> Tuple[float, float, float]:
        """Clamps a position to the valid range."""
        return (
            clamp(x, self.x_min, self.x_max),
            clamp(y, self.y_min, self.y_max),
            clamp(z, self.z_min, self.z_max),
        )


@dataclass
class Bounds1D:
    """1D bounds for a single axis."""

    min_val: float = 0.0
    max_val: float = 100.0

    def contains(self, value: float) -> bool:
        """Checks if the value is within the bounds."""
        return self.min_val <= value <= self.max_val

    def clamp(self, value: float) -> float:
        """Clamps the value to the bounds."""
        return clamp(value, self.min_val, self.max_val)


def is_in_range(value: float, min_val: float, max_val: float) -> bool:
    """Return True when value is inside the inclusive range."""
    return min_val <= value <= max_val


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value into the inclusive range."""
    return max(min_val, min(max_val, value))


def validate_position_3d(
    x: float,
    y: float,
    z: float,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    z_min: float,
    z_max: float,
) -> Tuple[bool, Optional[str]]:
    """Validate a 3D position and return an error message when invalid."""
    errors = []

    if not is_in_range(x, x_min, x_max):
        errors.append(f"X={x:.4f} out of range [{x_min:.4f}, {x_max:.4f}]")
    if not is_in_range(y, y_min, y_max):
        errors.append(f"Y={y:.4f} out of range [{y_min:.4f}, {y_max:.4f}]")
    if not is_in_range(z, z_min, z_max):
        errors.append(f"Z={z:.4f} out of range [{z_min:.4f}, {z_max:.4f}]")

    if errors:
        return False, "; ".join(errors)
    return True, None


def validate_position_6d(
    position: List[float],
    bounds: List[Tuple[float, float]],
    axis_names: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str]]:
    """Validate a 6D pose against per-axis bounds."""
    if axis_names is None:
        axis_names = ["X", "Y", "Z", "RX", "RY", "RZ"]

    if len(position) != 6 or len(bounds) != 6:
        return False, "Position and bounds must have 6 elements"

    errors = []
    for val, (min_val, max_val), name in zip(position, bounds, axis_names):
        if not is_in_range(val, min_val, max_val):
            errors.append(
                f"{name}={val:.4f} out of range [{min_val:.4f}, {max_val:.4f}]"
            )

    if errors:
        return False, "; ".join(errors)
    return True, None


def validate_positive(value: float, name: str = "value") -> Tuple[bool, Optional[str]]:
    """Validate that value is greater than zero."""
    if value <= 0:
        return False, f"{name} must be positive, got {value}"
    return True, None


def validate_non_negative(
    value: float, name: str = "value"
) -> Tuple[bool, Optional[str]]:
    """Validate that value is zero or greater."""
    if value < 0:
        return False, f"{name} must be non-negative, got {value}"
    return True, None


def validate_id_range(
    id_value: int, min_id: int = 0, max_id: int = 15, name: str = "ID"
) -> Tuple[bool, Optional[str]]:
    """Validate that an ID is an integer inside the configured range."""
    if not isinstance(id_value, int):
        return False, f"{name} must be an integer, got {type(id_value).__name__}"
    if not (min_id <= id_value <= max_id):
        return False, f"{name} must be between {min_id} and {max_id}, got {id_value}"
    return True, None


def check_collision_risk(
    axis_position: float,
    other_axis_position: Optional[float],
    collision_threshold: float,
) -> Tuple[bool, Optional[str]]:
    """Check whether another axis position blocks the requested movement."""
    if other_axis_position is None:
        return True, "Other axis position unknown, proceeding with caution"

    if other_axis_position > collision_threshold:
        return False, (
            f"Collision risk: other axis at {other_axis_position:.2f}mm "
            f"exceeds threshold {collision_threshold:.2f}mm"
        )

    return True, None
