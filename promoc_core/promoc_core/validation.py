"""\
Validation Utilities for ProMOC Assembly
=========================================

This module contains central validation and range-checking functions that are
reused across different nodes and components. The focus is on being:
**simple**, **predictable**, and **highly testable**.

Quickstart
----------
The most common use cases:

1) **Check if a value is within a range:**

    >>> from promoc_core.validation import is_in_range
    >>> is_in_range(5.0, min_val=0.0, max_val=10.0)
    True

2) **Clamp a value to a range:**

    >>> from promoc_core.validation import clamp
    >>> clamp(15.0, min_val=0.0, max_val=10.0)  # Result: 10.0
    10.0

3) **Validate a 3D/6D position:**

    >>> from promoc_core.validation import validate_position_3d
    >>> is_valid, error = validate_position_3d(x=0.5, y=0.5, z=0.5, ...)
    >>> if not is_valid:
    ...     print(f"Invalid position: {error}")

4) **Check for collision risk:**

    >>> from promoc_core.validation import check_collision_risk
    >>> is_safe, warning = check_collision_risk(
    ...     axis_position=50.0,
    ...     other_axis_position=5.0,
    ...     collision_threshold=10.0
    ... )

Available Functions
---------------------
- is_in_range()         Checks if a value is within bounds.
- clamp()               Clamps a value to a specified range.
- validate_position_3d  Validates a 3D position against limits.
- validate_position_6d  Validates a 6D pose (x,y,z,rx,ry,rz).
- validate_positive     Checks if a value is > 0.
- validate_non_negative Checks if a value is >= 0.
- validate_id_range     Checks ID ranges (e.g., XBot ID 0-15).
- check_collision_risk  Checks if a movement is likely to be safe.

Available Classes
------------------
- Bounds1D              1D bounds for a single axis.
- Bounds3D              3D box for position validation.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, List, Union


@dataclass
class Bounds3D:
    """
    3D bounding box for position validation.

    Useful for repeatedly checking if positions are within the same
    workspace (e.g., workspace limits).

    Attributes:
        x_min, x_max: X-axis limits (in m or mm - please be consistent).
        y_min, y_max: Y-axis limits.
        z_min, z_max: Z-axis limits.

    Example:
        >>> workspace = Bounds3D(x_min=0, x_max=0.5, y_min=0, y_max=0.3, z_min=0, z_max=0.1)
        >>> workspace.contains(0.1, 0.1, 0.05)
        True
        >>> workspace.clamp_position(0.6, 0.1, 0.05)
        (0.5, 0.1, 0.05)
    """
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

    def clamp_position(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """Clamps a position to the valid range."""
        return (
            clamp(x, self.x_min, self.x_max),
            clamp(y, self.y_min, self.y_max),
            clamp(z, self.z_min, self.z_max)
        )


@dataclass
class Bounds1D:
    """
    1D bounds for single-axis validation (e.g., a linear stage).

    Useful for repeatedly checking if values are within the same
    1D range (e.g., travel limits).

    Attributes:
        min_val: The minimum allowed value.
        max_val: The maximum allowed value.

    Example:
        >>> z_axis = Bounds1D(min_val=0.0, max_val=100.0)
        >>> z_axis.contains(50.0)
        True
        >>> z_axis.contains(150.0)
        False
        >>> z_axis.clamp(150.0)
        100.0
    """

    min_val: float = 0.0
    max_val: float = 100.0

    def contains(self, value: float) -> bool:
        """Checks if the value is within the bounds."""
        return self.min_val <= value <= self.max_val

    def clamp(self, value: float) -> float:
        """Clamps the value to the bounds."""
        return clamp(value, self.min_val, self.max_val)


def is_in_range(value: float, min_val: float, max_val: float) -> bool:
    """
    Checks if a value is within a range (inclusive of boundaries).

    This is the simplest validation function: if you just need a yes/no
    answer on whether a value is in the allowed range, this is the right choice.

    Procedure:
        1) Compares against `min_val` and `max_val`.
        2) Returns True if `min_val <= value <= max_val`.
        3) Otherwise, returns False.

    Args:
        value: The value to check.
        min_val: The lower bound (inclusive).
        max_val: The upper bound (inclusive).

    Returns:
        True if the value is within the range, False otherwise.

    Example:
        >>> is_in_range(50.0, min_val=0.0, max_val=100.0)
        True
        >>> is_in_range(150.0, min_val=0.0, max_val=100.0)
        False
    """
    return min_val <= value <= max_val


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamps a value to ensure it stays safely within a range.

    Use this when you want to "clip" a value instead of rejecting it.
    Typical for user inputs or calculations that might slightly exceed boundaries.

    Procedure:
        1) If value < min_val → returns min_val.
        2) If value > max_val → returns max_val.
        3) Otherwise, returns the value unchanged.

    Args:
        value: The value to clamp.
        min_val: The lower bound.
        max_val: The upper bound.

    Returns:
        The clamped value (guaranteed to be within [min_val, max_val]).

    Example:
        >>> clamp(5.0, min_val=0.0, max_val=10.0)
        5.0
        >>> clamp(15.0, min_val=0.0, max_val=10.0)
        10.0
        >>> clamp(-5.0, min_val=0.0, max_val=10.0)
        0.0
    """
    return max(min_val, min(max_val, value))


def validate_position_3d(
    x: float, y: float, z: float,
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    z_min: float, z_max: float
) -> Tuple[bool, Optional[str]]:
    """
    Validates a 3D position against specified boundaries.

    Use this when you need not just a "valid/invalid" check, but also a
    human-readable error message (e.g., in service callbacks to explain why
    a position was rejected).

    Procedure:
        1) Checks each axis (X, Y, Z) against its min/max limits.
        2) Collects all violations into an error message.
        3) Returns (True, None) if everything is within limits.
        4) Returns (False, error_message) if anything is out of bounds.

    Args:
        x, y, z: The coordinates to check.
        x_min, x_max: X-axis limits.
        y_min, y_max: Y-axis limits.
        z_min, z_max: Z-axis limits.

    Returns:
        A tuple (is_valid, error_message).
        - is_valid: True if the position is within all boundaries.
        - error_message: None if valid, otherwise a description of the violations.

    Example:
        >>> valid, error = validate_position_3d(
        ...     x=0.1, y=0.1, z=0.05,
        ...     x_min=0, x_max=0.5, y_min=0, y_max=0.3, z_min=0, z_max=0.1
        ... )
        >>> valid
        True
        >>> error is None
        True
    """
    # Step 1: Check axes and collect errors
    errors = []

    if not is_in_range(x, x_min, x_max):
        errors.append(f"X={x:.4f} out of range [{x_min:.4f}, {x_max:.4f}]")
    if not is_in_range(y, y_min, y_max):
        errors.append(f"Y={y:.4f} out of range [{y_min:.4f}, {y_max:.4f}]")
    if not is_in_range(z, z_min, z_max):
        errors.append(f"Z={z:.4f} out of range [{z_min:.4f}, {z_max:.4f}]")

    # Step 2: Return result
    if errors:
        return False, "; ".join(errors)
    return True, None


def validate_position_6d(
    position: List[float],
    bounds: List[Tuple[float, float]],
    axis_names: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validates a 6D position (x, y, z, rx, ry, rz) against boundaries.

    This is a generic function for arbitrary 6D poses. It checks all 6
    components against a (min, max) interval and combines any deviations
    into a single error message.

    Args:
        position: A list of 6 position values [x, y, z, rx, ry, rz].
        bounds: A list of 6 (min, max) tuples for each axis.
        axis_names: Optional: axis names for error messages.

    Returns:
        A tuple (is_valid, error_message).

    Example:
        >>> pos = [0.1, 0.1, 0.002, 0, 0, 0]
        >>> bounds = [(0, 0.5), (0, 0.2), (0, 0.005), (-0.1, 0.1), (-0.1, 0.1), (-3.14, 3.14)]
        >>> valid, error = validate_position_6d(pos, bounds)
    """
    if axis_names is None:
        axis_names = ['X', 'Y', 'Z', 'RX', 'RY', 'RZ']

    if len(position) != 6 or len(bounds) != 6:
        return False, "Position and bounds must have 6 elements"

    errors = []
    for i, (val, (min_val, max_val), name) in enumerate(zip(position, bounds, axis_names)):
        if not is_in_range(val, min_val, max_val):
            errors.append(
                f"{name}={val:.4f} out of range [{min_val:.4f}, {max_val:.4f}]")

    if errors:
        return False, "; ".join(errors)
    return True, None


def validate_positive(value: float, name: str = "value") -> Tuple[bool, Optional[str]]:
    """
    Checks if a value is positive (> 0).

    Args:
        value: The value to check.
        name: The name to use in the error message.

    Returns:
        A tuple (is_valid, error_message).
    """
    if value <= 0:
        return False, f"{name} must be positive, got {value}"
    return True, None


def validate_non_negative(value: float, name: str = "value") -> Tuple[bool, Optional[str]]:
    """
    Checks if a value is non-negative (>= 0).

    Args:
        value: The value to check.
        name: The name to use in the error message.

    Returns:
        A tuple (is_valid, error_message).
    """
    if value < 0:
        return False, f"{name} must be non-negative, got {value}"
    return True, None


def validate_id_range(
    id_value: int,
    min_id: int = 0,
    max_id: int = 15,
    name: str = "ID"
) -> Tuple[bool, Optional[str]]:
    """
    Checks if an ID is within the allowed range.

    Args:
        id_value: The ID to check.
        min_id: The minimum allowed ID.
        max_id: The maximum allowed ID.
        name: The name to use in the error message.

    Returns:
        A tuple (is_valid, error_message).

    Example:
        >>> valid, error = validate_id_range(5, 0, 15, "XBot ID")
        >>> valid
        True
    """
    if not isinstance(id_value, int):
        return False, f"{name} must be an integer, got {type(id_value).__name__}"
    if not (min_id <= id_value <= max_id):
        return False, f"{name} must be between {min_id} and {max_id}, got {id_value}"
    return True, None


def check_collision_risk(
    axis_position: float,
    other_axis_position: Optional[float],
    collision_threshold: float
) -> Tuple[bool, Optional[str]]:
    """
    Checks for a collision risk between two axes.

    Intended for scenarios where one axis (e.g., camera Z) cannot move safely
    if another axis (e.g., a linear stage) is extended beyond a certain threshold.

    Procedure:
        1) If the other axis position is unknown (None) → assume it's "safe"
           but return a warning.
        2) If other_axis_position > threshold → NOT safe (risk).
        3) If other_axis_position <= threshold → safe.

    Typical Use Case (Camera + Linear Axis):
        - A linear axis carries an object that could collide with the camera.
        - If the linear axis is extended far out, the camera should not lower.
        - The threshold defines the "safe zone" of the other axis.

    Args:
        axis_position: The position of the axis that intends to move (for logging).
        other_axis_position: The position of the other axis (None if unknown).
        collision_threshold: The maximum safe position of the other axis.

    Returns:
        A tuple (is_safe, message).
        - is_safe: True if movement is allowed, False if blocked.
        - message: A warning/error message (None if clearly safe).

    Example:
        >>> safe, msg = check_collision_risk(
        ...     axis_position=10.0,
        ...     other_axis_position=5.0,   # Below threshold
        ...     collision_threshold=8.0
        ... )
        >>> safe
        True
    """
    # Step 1: Unknown position
    if other_axis_position is None:
        # Can't check - assume safe but warn the caller
        return True, "Other axis position unknown, proceeding with caution"

    # Step 2: Check risk
    if other_axis_position > collision_threshold:
        return False, (
            f"Collision risk: other axis at {other_axis_position:.2f}mm "
            f"exceeds threshold {collision_threshold:.2f}mm"
        )

    # Step 3: Safe
    return True, None
