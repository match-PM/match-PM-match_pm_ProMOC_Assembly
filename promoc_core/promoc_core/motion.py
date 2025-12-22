"""\
Motion Utilities for ProMOC Assembly
===================================

This module contains central, reusable helper functions related to motion.
It is intentionally **ROS-independent** so that it can be used identically
across multiple nodes and components (linear axis, planar motor, simulators, tests).

It includes, among others:

- `MotionStatus`: An enum for tracking the status of a movement.
- Position/tolerance checking ("target reached?").
- Polling logic for waiting for motion completion.

Quickstart
----------
1) **Evaluate motion status:**

    >>> from promoc_core.motion import MotionStatus
    >>> status = MotionStatus.IDLE
    >>> if status == MotionStatus.COMPLETED:
    ...     print("Movement finished!")

2) **Check if a target position has been reached:**

    >>> from promoc_core.motion import check_position_reached
    >>> target = [0.1, 0.2, 0.003]
    >>> current = [0.1001, 0.2002, 0.00305]
    >>> check_position_reached(target, current, tolerance=0.001)
    True

3) **Wait for motion completion (with a callback):**

    >>> from promoc_core.motion import wait_for_position
    >>> result = wait_for_position(
    ...     target=[0.1, 0.2, 0.003],
    ...     get_position_fn=my_get_position_callback,
    ...     timeout_s=10.0
    ... )
    >>> if result.success:
    ...     print("Arrived!")

Available Classes
------------------
- `MotionStatus`: Enum (IDLE, MOVING, COMPLETED, ERROR, ...).
- `MotionResult`: Dataclass with the result/diagnostics of a motion.

Available Functions
---------------------
- `check_position_reached()`: Checks target achievement axis by axis.
- `compute_position_error()`: Calculates total distance + per-axis errors.
- `wait_for_position()`: Polling wait for a target (ROS-independent).
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple
import time
import math


class MotionStatus(Enum):
    """
    Status of a motion operation.

    This serves to represent the state of motion commands uniformly across
    different motion controllers (linear axis, planar motor, simulator, ...).

    States:
        UNKNOWN     The status cannot be determined (e.g., communication loss).
        IDLE        The controller is ready and waiting for new commands.
        MOVING      Motion is in progress.
        COMPLETED   Motion has completed successfully (target reached).
        ERROR       An error occurred (hardware/software).
        TIMEOUT     The motion did not complete in time.
        ABORTED     The motion was aborted by the user or system.
        COLLISION   Motion was stopped due to a collision risk.

    Example:
        >>> from promoc_core.motion import MotionStatus
        >>>
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

    Contains the most important information after a movement is complete:

    - Final status (success/timeout/error/...).
    - Final position (if available).
    - Error message (if something went wrong).
    - Duration of the movement.

    Attributes:
        status: The final `MotionStatus`.
        final_position: The position after completion (list of floats).
        error_message: An error description (typically when `status == ERROR`).
        duration_s: The duration in seconds.

    Properties:
        success: A convenience property: True if `status == COMPLETED`.

    Example:
        >>> result = wait_for_position(target, get_pos_fn, timeout_s=10.0)
        >>>
        >>> if result.success:
        ...     print(f"Arrived at {result.final_position}")
        ...     print(f"Duration: {result.duration_s:.2f}s")
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
        """True if the movement completed successfully."""
        return self.status == MotionStatus.COMPLETED


def check_position_reached(
    target: List[float],
    current: List[float],
    tolerance: float = 0.001
) -> bool:
    """
    Checks if the current position has reached the target within a tolerance.

    This is the core function for deciding "is the movement finished?".
    It checks on an **axis-by-axis** basis—only when *all* axes are within
    tolerance does the function return True.

    Procedure:
        1) Compares the lengths of `target` and `current` (must be identical).
        2) Calculates the absolute difference |target - current| for each axis.
        3) If *all* deviations are <= tolerance → True.
        4) If *any* deviation is > tolerance → False.

    Args:
        target: The target position as a list [x, y, z, ...].
        current: The current position as a list [x, y, z, ...].
        tolerance: The maximum deviation per axis (default: 0.001).

    Returns:
        True if all axes are within tolerance.

    Example:
        >>> target = [0.1, 0.2, 0.003]
        >>> current = [0.1001, 0.1999, 0.00305]
        >>> check_position_reached(target, current, tolerance=0.001)
        True
        >>>
        >>> current = [0.1, 0.2, 0.010]  # Z is too far
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
    Calculates the position error between a target and current position.

    Useful for diagnostics/logging or for deciding whether a movement should
    continue. Returns both the total error (Euclidean distance) and the
    per-axis deviations.

    Procedure:
        1) Calculate the absolute difference for each axis.
        2) Calculate the Euclidean distance (sqrt of the sum of squares).
        3) Return both values.

    Args:
        target: The target position [x, y, z, ...].
        current: The current position [x, y, z, ...].

    Returns:
        A tuple (total_error, per_axis_errors).
        - total_error: The Euclidean distance (float).
        - per_axis_errors: A list of the per-axis deviations.

    Raises:
        ValueError: If the dimensions do not match.

    Example:
        >>> target = [0.1, 0.2, 0.0]
        >>> current = [0.11, 0.21, 0.01]
        >>> total, per_axis = compute_position_error(target, current)
        >>> per_axis
        [0.01, 0.01, 0.01]
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
    Waits via polling for a target position to be reached.

    This is a generic, **ROS-independent** implementation: you provide a
    callback function `get_position_fn` that returns the current position as
    a list (or `None` if the position is not currently available).

    Procedure:
        1) Start a timer.
        2) Loop: get the current position via the callback.
        3) Check for target achievement (`check_position_reached`).
        4) If reached → return `COMPLETED`.
        5) If timeout → return `TIMEOUT`.
        6) Otherwise, wait briefly and repeat.

    Args:
        target: The target position [x, y, z, ...].
        get_position_fn: A callback that provides the current position (or None).
        tolerance: Tolerance per axis (default: 0.001).
        timeout_s: Maximum wait time in seconds (default: 10.0).
        poll_interval_s: Polling interval (default: 0.05s).

    Returns:
        A `MotionResult` with:
        - status: `COMPLETED` or `TIMEOUT`.
        - final_position: The last known position.
        - duration_s: The wait time until completion/timeout.

    Example:
        >>> def get_current_pos():
        ...     # Read the position from your interface
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
    Waits for a motion controller to enter an idle state.

    Similar to `wait_for_position`, but checks status strings
    (e.g., "IDLE"/"XBOT_IDLE") instead of exact positions.
    This is useful when you only need to know: "Is it finished?".

    Procedure:
        1) Loop: get the status via the callback.
        2) If status is in `idle_states` → `COMPLETED`.
        3) If status is in `error_states` → `ERROR`.
        4) If timeout → `TIMEOUT`.
        5) Otherwise, wait and repeat.

    Args:
        get_status_fn: A callback that returns the current status as a string.
        idle_states: Status strings indicating "finished"
            (Default: ["IDLE", "XBOT_IDLE", "idle"]).
        error_states: Status strings indicating "error/stopped"
            (Default: ["ERROR", "XBOT_ERROR", "STOPPED", ...]).
        timeout_s: Max wait time (default: 10.0s).
        poll_interval_s: Polling interval (default: 0.1s).

    Returns:
        A `MotionResult` with the final status.

    Example:
        >>> def get_controller_status():
        ...     return "XBOT_IDLE"  # or "XBOT_MOVING", "XBOT_ERROR", ...
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
    Velocity and acceleration parameters for movements.

    Provides a standardized structure for passing motion parameters
    across different controllers.
    """
    max_velocity: float = 0.1       # m/s or mm/s depending on context
    max_acceleration: float = 0.5   # m/s² or mm/s²

    # Optional per-axis or per-DOF parameters
    xy_velocity: Optional[float] = None
    z_velocity: Optional[float] = None
    rotation_velocity: Optional[float] = None

    def get_xy_velocity(self) -> float:
        """Returns the XY velocity (fallback: `max_velocity`)."""
        return self.xy_velocity if self.xy_velocity is not None else self.max_velocity

    def get_z_velocity(self) -> float:
        """Returns the Z velocity (fallback: `max_velocity`)."""
        return self.z_velocity if self.z_velocity is not None else self.max_velocity


def interpolate_position(
    start: List[float],
    end: List[float],
    t: float
) -> List[float]:
    """
    Linear interpolation between two positions.

    Args:
        start: The starting position.
        end: The target position.
        t: The interpolation factor (0.0 = start, 1.0 = end).

    Returns:
        The interpolated position.

    Example:
        >>> start = [0.0, 0.0, 0.0]
        >>> end = [1.0, 2.0, 3.0]
        >>> interpolate_position(start, end, 0.5)
        [0.5, 1.0, 1.5]
    """
    t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
    return [s + t * (e - s) for s, e in zip(start, end)]
