"""
Validation Utilities for ProMOC Assembly
=========================================

This module provides common validation and range-checking functions
used across different nodes and components. All functions are designed
to be simple, predictable, and easy to test.

Quick Start
-----------
The most common use cases:

1. **Check if a value is in range:**
   
   >>> from promoc_core.validation import is_in_range
   >>> is_in_range(5.0, min_val=0.0, max_val=10.0)
   True

2. **Clamp a value to stay within limits:**
   
   >>> from promoc_core.validation import clamp
   >>> clamp(15.0, min_val=0.0, max_val=10.0)  # Returns 10.0
   10.0

3. **Validate a 3D/6D position:**
   
   >>> from promoc_core.validation import validate_position_3d
   >>> is_valid, error = validate_position_3d(x=0.5, y=0.5, z=0.5, ...)
   >>> if not is_valid:
   ...     print(f"Invalid position: {error}")

4. **Check collision risk:**
   
   >>> from promoc_core.validation import check_collision_risk
   >>> is_safe, warning = check_collision_risk(
   ...     axis_position=50.0, 
   ...     other_axis_position=5.0, 
   ...     collision_threshold=10.0
   ... )

Available Functions
-------------------
- is_in_range()         Check if value is within bounds
- clamp()               Constrain value to range  
- validate_position_3d  Validate 3D position against bounds
- validate_position_6d  Validate 6D position (x,y,z,rx,ry,rz)
- validate_positive     Check if value > 0
- validate_non_negative Check if value >= 0
- validate_id_range     Check if ID is valid (e.g., XBot ID 0-15)
- check_collision_risk  Check if motion is safe

Available Classes
-----------------
- Bounds1D              1D bounds for single axis (e.g., linear axis)
- Bounds3D              3D bounding box for position validation
"""

from dataclasses import dataclass
from typing import Tuple, Optional, List, Union


@dataclass
class Bounds3D:
    """
    3D bounding box for position validation.

    Use this when you need to repeatedly check if positions are
    within the same 3D volume (e.g., workspace limits).

    Attributes:
        x_min, x_max: X-axis limits (in meters or mm, be consistent)
        y_min, y_max: Y-axis limits
        z_min, z_max: Z-axis limits

    Example:
        >>> # Define workspace boundaries
        >>> workspace = Bounds3D(x_min=0, x_max=0.5, y_min=0, y_max=0.3, z_min=0, z_max=0.1)
        >>> 
        >>> # Check if a point is inside
        >>> workspace.contains(0.1, 0.1, 0.05)
        True
        >>> 
        >>> # Clamp a point to the workspace
        >>> workspace.clamp_position(0.6, 0.1, 0.05)
        (0.5, 0.1, 0.05)  # x was clamped from 0.6 to 0.5
    """
    x_min: float = 0.0
    x_max: float = 1.0
    y_min: float = 0.0
    y_max: float = 1.0
    z_min: float = 0.0
    z_max: float = 1.0

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if point is within bounds."""
        return (self.x_min <= x <= self.x_max and
                self.y_min <= y <= self.y_max and
                self.z_min <= z <= self.z_max)

    def clamp_position(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """Clamp position to bounds."""
        return (
            clamp(x, self.x_min, self.x_max),
            clamp(y, self.y_min, self.y_max),
            clamp(z, self.z_min, self.z_max)
        )


@dataclass
class Bounds1D:
    """
    1D bounds for single-axis validation (e.g., linear axis).

    Use this when you need to repeatedly check if values are
    within the same 1D range (e.g., linear axis travel limits).

    Attributes:
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Example:
        >>> # Define linear axis limits (in mm)
        >>> z_axis = Bounds1D(min_val=0.0, max_val=100.0)
        >>> 
        >>> # Check if position is valid
        >>> z_axis.contains(50.0)
        True
        >>> z_axis.contains(150.0)
        False
        >>> 
        >>> # Clamp to safe range
        >>> z_axis.clamp(150.0)
        100.0
    """
    min_val: float = 0.0
    max_val: float = 100.0

    def contains(self, value: float) -> bool:
        """Check if value is within bounds."""
        return self.min_val <= value <= self.max_val

    def clamp(self, value: float) -> float:
        """Clamp value to bounds."""
        return clamp(value, self.min_val, self.max_val)


def is_in_range(value: float, min_val: float, max_val: float) -> bool:
    """
    Check if a value is within the specified range (inclusive).

    This is the most basic validation function. Use it when you need
    a simple yes/no answer about whether a value is within bounds.

    How it works:
        1. Compares value against min_val and max_val
        2. Returns True if min_val <= value <= max_val
        3. Returns False otherwise (value too low or too high)

    Args:
        value: The value to check
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)

    Returns:
        True if value is within range, False otherwise

    Example:
        >>> # Check if position is within axis limits
        >>> is_in_range(50.0, min_val=0.0, max_val=100.0)
        True
        >>> is_in_range(150.0, min_val=0.0, max_val=100.0)
        False
        >>> is_in_range(-10.0, min_val=0.0, max_val=100.0)
        False
    """
    return min_val <= value <= max_val


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Constrain a value to be within the specified range.

    Use this when you want to "clip" a value to stay within limits,
    rather than rejecting it. Common for user inputs or calculations
    that might slightly exceed bounds.

    How it works:
        1. If value < min_val → returns min_val
        2. If value > max_val → returns max_val  
        3. Otherwise → returns value unchanged

    Args:
        value: The value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        The clamped value, guaranteed to be within [min_val, max_val]

    Example:
        >>> # Value in range - returned unchanged
        >>> clamp(5.0, min_val=0.0, max_val=10.0)
        5.0
        >>> 
        >>> # Value too high - clamped to max
        >>> clamp(15.0, min_val=0.0, max_val=10.0)
        10.0
        >>> 
        >>> # Value too low - clamped to min
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
    Validate a 3D position against bounds.

    Use this when you need to check if a position is valid AND get
    a descriptive error message if it's not. Perfect for service
    callbacks that need to explain why a position was rejected.

    How it works:
        1. Checks each axis (X, Y, Z) against its min/max bounds
        2. Collects all violations into an error message
        3. Returns (True, None) if all axes are valid
        4. Returns (False, error_message) if any axis is out of range

    Args:
        x, y, z: Position coordinates to validate
        x_min, x_max: X-axis bounds
        y_min, y_max: Y-axis bounds
        z_min, z_max: Z-axis bounds

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if position is within all bounds
        - error_message: None if valid, otherwise describes the violations

    Example:
        >>> # Valid position
        >>> valid, error = validate_position_3d(
        ...     x=0.1, y=0.1, z=0.05,
        ...     x_min=0, x_max=0.5, y_min=0, y_max=0.3, z_min=0, z_max=0.1
        ... )
        >>> valid
        True
        >>> error is None
        True
        >>> 
        >>> # Invalid position (X too high)
        >>> valid, error = validate_position_3d(
        ...     x=0.6, y=0.1, z=0.05,  # X exceeds 0.5
        ...     x_min=0, x_max=0.5, y_min=0, y_max=0.3, z_min=0, z_max=0.1
        ... )
        >>> valid
        False
        >>> error
        'X=0.6000 out of range [0.0000, 0.5000]'
    """
    # Step 1: Check each axis and collect errors
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
    Validate a 6D position (x, y, z, rx, ry, rz) against bounds.

    Args:
        position: List of 6 position values [x, y, z, rx, ry, rz]
        bounds: List of 6 (min, max) tuples for each axis
        axis_names: Optional axis names for error messages

    Returns:
        Tuple of (is_valid, error_message)

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
    Validate that a value is positive (> 0).

    Args:
        value: The value to check
        name: Name for error message

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value <= 0:
        return False, f"{name} must be positive, got {value}"
    return True, None


def validate_non_negative(value: float, name: str = "value") -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is non-negative (>= 0).

    Args:
        value: The value to check
        name: Name for error message

    Returns:
        Tuple of (is_valid, error_message)
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
    Validate an ID value is within allowed range.

    Args:
        id_value: The ID to validate
        min_id: Minimum allowed ID
        max_id: Maximum allowed ID
        name: Name for error message

    Returns:
        Tuple of (is_valid, error_message)

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
    Check if there's a collision risk between two axes.

    This is specifically designed for scenarios where one axis
    (e.g., camera Z-axis) cannot move safely when another axis
    (e.g., linear axis) is extended beyond a certain threshold.

    How it works:
        1. If other axis position is unknown (None) → assume safe (with warning)
        2. If other axis position > threshold → NOT safe (collision risk)
        3. If other axis position <= threshold → safe to move

    Typical Use Case (Camera + Linear Axis):
        - Linear axis carries something that could collide with camera
        - If linear axis is extended (high position), camera cannot go down
        - Threshold defines the safe limit for the other axis

    Args:
        axis_position: Position of the axis we want to move (for logging)
        other_axis_position: Position of the other axis (None if unknown)
        collision_threshold: Maximum safe position for the other axis

    Returns:
        Tuple of (is_safe, message)
        - is_safe: True if movement is allowed, False if blocked
        - message: Warning or error description (None if clearly safe)

    Example:
        >>> # Other axis is retracted (safe)
        >>> safe, msg = check_collision_risk(
        ...     axis_position=10.0,
        ...     other_axis_position=5.0,   # Below threshold
        ...     collision_threshold=8.0
        ... )
        >>> safe
        True
        >>> 
        >>> # Other axis is extended (NOT safe)
        >>> safe, msg = check_collision_risk(
        ...     axis_position=10.0,
        ...     other_axis_position=15.0,  # Above threshold!
        ...     collision_threshold=8.0
        ... )
        >>> safe
        False
        >>> msg
        'Collision risk: other axis at 15.00mm exceeds threshold 8.00mm'
    """
    # Step 1: Handle unknown position
    if other_axis_position is None:
        # Can't check - assume safe but warn the caller
        return True, "Other axis position unknown, proceeding with caution"

    # Step 2: Check if other axis is in safe zone
    if other_axis_position > collision_threshold:
        return False, (
            f"Collision risk: other axis at {other_axis_position:.2f}mm "
            f"exceeds threshold {collision_threshold:.2f}mm"
        )

    # Step 3: Safe to proceed
    return True, None
