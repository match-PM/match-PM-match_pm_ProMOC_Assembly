"""
Motion Utilities for ProMOC Assembly
=====================================

This module provides common motion-related utilities including:
- MotionStatus enum for tracking motion state
- Position tolerance checking
- Motion completion waiting logic

These utilities are designed to be **ROS-independent** so they can be
used across different node implementations without coupling to ROS.

Quick Start
-----------
1. **Track motion status:**
   
   >>> from promoc_core.motion import MotionStatus
   >>> status = MotionStatus.IDLE
   >>> if status == MotionStatus.COMPLETED:
   ...     print("Motion done!")

2. **Check if position is reached:**
   
   >>> from promoc_core.motion import check_position_reached
   >>> target = [0.1, 0.2, 0.003]
   >>> current = [0.1001, 0.2002, 0.00305]
   >>> check_position_reached(target, current, tolerance=0.001)
   True

3. **Wait for motion to complete:**
   
   >>> from promoc_core.motion import wait_for_position
   >>> result = wait_for_position(
   ...     target=[0.1, 0.2, 0.003],
   ...     get_position_fn=my_get_position_callback,
   ...     timeout_s=10.0
   ... )
   >>> if result.success:
   ...     print("Arrived!")

Available Classes
-----------------
- MotionStatus    Enum for motion states (IDLE, MOVING, COMPLETED, ERROR, etc.)
- MotionResult    Dataclass with result of motion operation
- VelocityParams  Dataclass for velocity/acceleration parameters

Available Functions
-------------------
- check_position_reached()  Check if current position matches target
- compute_position_error()  Calculate distance between positions
- wait_for_position()       Wait for position with polling
- wait_for_idle()           Wait for controller to become idle
- interpolate_position()    Linear interpolation between positions
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple
import time
import math


class MotionStatus(Enum):
    """
    Status of a motion operation.

    Used to track the state of motion commands across different
    motion controllers (linear axis, planar motor, etc.).

    States:
        UNKNOWN     Status cannot be determined (e.g., communication lost)
        IDLE        Controller is idle, ready for new commands
        MOVING      Motion is in progress
        COMPLETED   Motion finished successfully (target reached)
        ERROR       Motion failed due to hardware/software error
        TIMEOUT     Motion did not complete within time limit
        ABORTED     Motion was cancelled by user/system
        COLLISION   Motion stopped due to collision detection

    Example:
        >>> from promoc_core.motion import MotionStatus
        >>> 
        >>> # In your motion callback:
        >>> def handle_motion_result(status: MotionStatus):
        ...     if status == MotionStatus.COMPLETED:
        ...         print("Target reached!")
        ...     elif status == MotionStatus.TIMEOUT:
        ...         print("Motion took too long!")
        ...     elif status == MotionStatus.ERROR:
        ...         print("Motion failed!")
    """
    UNKNOWN = auto()      # Status cannot be determined
    IDLE = auto()         # Controller is idle, ready for commands
    MOVING = auto()       # Motion in progress
    COMPLETED = auto()    # Motion completed successfully
    ERROR = auto()        # Motion failed with error
    TIMEOUT = auto()      # Motion timed out
    ABORTED = auto()      # Motion was aborted by user
    COLLISION = auto()    # Motion stopped due to collision risk


@dataclass
class MotionResult:
    """
    Result of a motion operation.

    Contains all relevant information about a completed motion:
    - Final status (success, timeout, error, etc.)
    - Final position (if available)
    - Error message (if something went wrong)
    - Duration (how long the motion took)

    Attributes:
        status: Final MotionStatus of the operation
        final_position: Position after motion completed (list of floats)
        error_message: Description of what went wrong (if status is ERROR)
        duration_s: Time taken for motion in seconds

    Properties:
        success: Convenience property, True if status == COMPLETED

    Example:
        >>> result = wait_for_position(target, get_pos_fn, timeout_s=10.0)
        >>> 
        >>> if result.success:
        ...     print(f"Arrived at {result.final_position}")
        ...     print(f"Motion took {result.duration_s:.2f}s")
        ... else:
        ...     print(f"Motion failed: {result.status.name}")
        ...     if result.error_message:
        ...         print(f"Error: {result.error_message}")
    """
    status: MotionStatus
    final_position: Optional[List[float]] = None
    error_message: Optional[str] = None
    duration_s: float = 0.0

    @property
    def success(self) -> bool:
        """True if motion completed successfully."""
        return self.status == MotionStatus.COMPLETED


def check_position_reached(
    target: List[float],
    current: List[float],
    tolerance: float = 0.001
) -> bool:
    """
    Check if current position has reached target within tolerance.

    This is the core function for determining if a motion is complete.
    Each axis is checked independently - ALL axes must be within
    tolerance for the function to return True.

    How it works:
        1. Compare length of target and current (must match)
        2. For each axis: calculate |target - current|
        3. If ALL differences <= tolerance → return True
        4. If ANY difference > tolerance → return False

    Args:
        target: Target position as list of floats [x, y, z, ...]
        current: Current position as list of floats [x, y, z, ...]
        tolerance: Maximum allowed deviation per axis (default: 0.001 = 1mm or 1um depending on units)

    Returns:
        True if all axes are within tolerance of target

    Example:
        >>> # 3-axis example (XYZ in meters)
        >>> target = [0.1, 0.2, 0.003]
        >>> current = [0.1001, 0.1999, 0.00305]  # All within 1mm
        >>> check_position_reached(target, current, tolerance=0.001)
        True
        >>> 
        >>> # One axis too far
        >>> current = [0.1, 0.2, 0.010]  # Z is 7mm off
        >>> check_position_reached(target, current, tolerance=0.001)
        False
    """
    # Step 1: Verify dimensions match
    if len(target) != len(current):
        return False

    # Step 2: Check each axis
    return all(
        abs(t - c) <= tolerance
        for t, c in zip(target, current)
    )


def compute_position_error(
    target: List[float],
    current: List[float]
) -> Tuple[float, List[float]]:
    """
    Compute position error between target and current position.

    Useful for diagnostics, logging, or deciding if motion should continue.
    Returns both the total Euclidean distance and per-axis errors.

    How it works:
        1. Calculate absolute difference for each axis
        2. Calculate Euclidean distance (sqrt of sum of squares)
        3. Return both values

    Args:
        target: Target position [x, y, z, ...]
        current: Current position [x, y, z, ...]

    Returns:
        Tuple of (total_error, per_axis_errors)
        - total_error: Euclidean distance (float)
        - per_axis_errors: List of absolute differences per axis

    Raises:
        ValueError: If position dimensions don't match

    Example:
        >>> target = [0.1, 0.2, 0.0]
        >>> current = [0.11, 0.21, 0.01]
        >>> total, per_axis = compute_position_error(target, current)
        >>> per_axis
        [0.01, 0.01, 0.01]  # 10mm error on each axis
        >>> total
        0.01732...  # sqrt(0.01² + 0.01² + 0.01²)
    """
    if len(target) != len(current):
        raise ValueError(
            f"Position dimensions don't match: {len(target)} vs {len(current)}")

    per_axis = [abs(t - c) for t, c in zip(target, current)]
    total = math.sqrt(sum(e**2 for e in per_axis))

    return total, per_axis


def wait_for_position(
    target: List[float],
    get_position_fn: Callable[[], Optional[List[float]]],
    tolerance: float = 0.001,
    timeout_s: float = 10.0,
    poll_interval_s: float = 0.05
) -> MotionResult:
    """
    Wait for position to reach target with polling.

    This is a generic, ROS-independent implementation that works with
    any callback function that returns the current position. Perfect
    for implementing motion completion logic in different contexts.

    How it works:
        1. Start a timer
        2. Loop: get current position via callback
        3. Check if position matches target (within tolerance)
        4. If yes → return COMPLETED
        5. If timeout exceeded → return TIMEOUT
        6. Otherwise → sleep and repeat

    Args:
        target: Target position to reach [x, y, z, ...]
        get_position_fn: Callback that returns current position (or None if unavailable)
        tolerance: Position tolerance per axis (default: 0.001)
        timeout_s: Maximum wait time in seconds (default: 10.0)
        poll_interval_s: How often to check position (default: 0.05 = 50ms)

    Returns:
        MotionResult containing:
        - status: COMPLETED or TIMEOUT
        - final_position: Last known position
        - duration_s: How long the wait took

    Example:
        >>> def get_current_pos():
        ...     # Read position from your hardware interface
        ...     return [0.1, 0.2, 0.003]
        >>> 
        >>> result = wait_for_position(
        ...     target=[0.1, 0.2, 0.003],
        ...     get_position_fn=get_current_pos,
        ...     tolerance=0.001,
        ...     timeout_s=10.0
        ... )
        >>> 
        >>> if result.success:
        ...     print(f"Motion completed in {result.duration_s:.2f}s")
        ... else:
        ...     print(f"Motion failed: {result.error_message}")
    """
    # Step 1: Initialize timing
    start_time = time.time()
    last_position = None

    # Step 2: Polling loop
    while True:
        elapsed = time.time() - start_time

        # Step 3: Check timeout
        if elapsed >= timeout_s:
            return MotionResult(
                status=MotionStatus.TIMEOUT,
                final_position=last_position,
                error_message=f"Timeout after {timeout_s:.1f}s",
                duration_s=elapsed
            )

        # Step 4: Get current position
        current = get_position_fn()
        if current is None:
            # Position not available yet, wait and retry
            time.sleep(poll_interval_s)
            continue

        last_position = current

        # Step 5: Check if target reached
        if check_position_reached(target, current, tolerance):
            return MotionResult(
                status=MotionStatus.COMPLETED,
                final_position=current,
                duration_s=elapsed
            )

        # Step 6: Wait before next check
        time.sleep(poll_interval_s)


def wait_for_idle(
    get_status_fn: Callable[[], str],
    idle_states: List[str] = None,
    error_states: List[str] = None,
    timeout_s: float = 10.0,
    poll_interval_s: float = 0.1
) -> MotionResult:
    """
    Wait for motion controller to reach idle state.

    Similar to wait_for_position, but checks status strings instead
    of positions. Useful when you just need to know "is it done?"
    without tracking the exact position.

    How it works:
        1. Loop: get current status via callback
        2. If status is in idle_states → return COMPLETED
        3. If status is in error_states → return ERROR
        4. If timeout exceeded → return TIMEOUT
        5. Otherwise → sleep and repeat

    Args:
        get_status_fn: Callback that returns current status as string
        idle_states: Status strings meaning "motion done" 
                     (default: ["IDLE", "XBOT_IDLE", "idle"])
        error_states: Status strings meaning "error occurred"
                      (default: ["ERROR", "XBOT_ERROR", "STOPPED", ...])
        timeout_s: Maximum wait time (default: 10.0s)
        poll_interval_s: How often to check (default: 0.1s)

    Returns:
        MotionResult with final status

    Example:
        >>> def get_controller_status():
        ...     return "XBOT_IDLE"  # or "XBOT_MOVING", "XBOT_ERROR", etc.
        >>> 
        >>> result = wait_for_idle(get_controller_status, timeout_s=30.0)
        >>> if result.success:
        ...     print("Controller is idle!")
    """
    # Default state lists for common controllers
    if idle_states is None:
        idle_states = ["IDLE", "XBOT_IDLE", "idle"]
    if error_states is None:
        error_states = ["ERROR", "XBOT_ERROR",
                        "STOPPED", "XBOT_STOPPED", "error"]

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed >= timeout_s:
            return MotionResult(
                status=MotionStatus.TIMEOUT,
                error_message=f"Timeout waiting for idle after {timeout_s:.1f}s",
                duration_s=elapsed
            )

        try:
            current_status = get_status_fn()
        except Exception as e:
            return MotionResult(
                status=MotionStatus.ERROR,
                error_message=f"Error getting status: {e}",
                duration_s=elapsed
            )

        if current_status in idle_states:
            return MotionResult(
                status=MotionStatus.COMPLETED,
                duration_s=elapsed
            )

        if current_status in error_states:
            return MotionResult(
                status=MotionStatus.ERROR,
                error_message=f"Controller in error state: {current_status}",
                duration_s=elapsed
            )

        time.sleep(poll_interval_s)


@dataclass
class VelocityParams:
    """
    Velocity and acceleration parameters for motion.

    Provides a standardized way to pass motion parameters
    across different motion controllers.
    """
    max_velocity: float = 0.1       # m/s or mm/s depending on context
    max_acceleration: float = 0.5   # m/s² or mm/s²

    # Optional per-axis or per-DOF parameters
    xy_velocity: Optional[float] = None
    z_velocity: Optional[float] = None
    rotation_velocity: Optional[float] = None

    def get_xy_velocity(self) -> float:
        """Get XY velocity, falling back to max_velocity."""
        return self.xy_velocity if self.xy_velocity is not None else self.max_velocity

    def get_z_velocity(self) -> float:
        """Get Z velocity, falling back to max_velocity."""
        return self.z_velocity if self.z_velocity is not None else self.max_velocity


def interpolate_position(
    start: List[float],
    end: List[float],
    t: float
) -> List[float]:
    """
    Linear interpolation between two positions.

    Args:
        start: Start position
        end: End position
        t: Interpolation factor (0.0 = start, 1.0 = end)

    Returns:
        Interpolated position

    Example:
        >>> start = [0.0, 0.0, 0.0]
        >>> end = [1.0, 2.0, 3.0]
        >>> interpolate_position(start, end, 0.5)
        [0.5, 1.0, 1.5]
    """
    t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
    return [s + t * (e - s) for s, e in zip(start, end)]
