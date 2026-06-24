"""ROS-independent helpers for motion status, tolerances, and polling."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple
import time
import math


class MotionStatus(Enum):
    """Common motion states used by controllers and tests."""

    UNKNOWN = auto()
    IDLE = auto()
    MOVING = auto()
    COMPLETED = auto()
    ERROR = auto()
    TIMEOUT = auto()
    ABORTED = auto()
    COLLISION = auto()


@dataclass
class MotionResult:
    """Result object returned by polling helpers."""

    status: MotionStatus
    final_position: Optional[List[float]] = None
    error_message: Optional[str] = None
    duration_s: float = 0.0

    @property
    def success(self) -> bool:
        """True if the movement completed successfully."""
        return self.status == MotionStatus.COMPLETED


def compute_motion_timeout(
    travel_time_s: float | None,
    *,
    multiplier: float = 1.5,
    buffer_s: float = 3.0,
    min_s: float = 5.0,
    fallback_s: float | None = None,
) -> float:
    """Compute a safe polling timeout from a driver-provided travel time."""
    if multiplier <= 0:
        raise ValueError("multiplier must be > 0")
    if min_s <= 0:
        raise ValueError("min_s must be > 0")

    if travel_time_s is not None and travel_time_s > 0:
        timeout = (travel_time_s * multiplier) + buffer_s
        return max(float(timeout), float(min_s))

    fallback = min_s if fallback_s is None else fallback_s
    return max(float(fallback), float(min_s))


def check_position_reached(
    target: List[float], current: List[float], tolerance: float = 0.001
) -> bool:
    """Return True when every axis is within tolerance of the target."""
    if len(target) != len(current):
        return False

    return all(abs(t - c) <= tolerance for t, c in zip(target, current))


def compute_position_error(
    target: List[float], current: List[float]
) -> Tuple[float, List[float]]:
    """Return Euclidean error and per-axis absolute errors."""
    if len(target) != len(current):
        raise ValueError(
            f"Position dimensions don't match: {len(target)} vs {len(current)}"
        )

    per_axis = [abs(t - c) for t, c in zip(target, current)]
    total = math.sqrt(sum(e**2 for e in per_axis))

    return total, per_axis


def wait_for_position(
    target: List[float],
    get_position_fn: Callable[[], Optional[List[float]]],
    tolerance: float = 0.001,
    timeout_s: float = 10.0,
    poll_interval_s: float = 0.05,
) -> MotionResult:
    """Poll a position callback until the target is reached or timed out."""
    start_time = time.time()
    last_position = None

    while True:
        elapsed = time.time() - start_time

        if elapsed >= timeout_s:
            return MotionResult(
                status=MotionStatus.TIMEOUT,
                final_position=last_position,
                error_message=f"Timeout after {timeout_s:.1f}s",
                duration_s=elapsed,
            )

        current = get_position_fn()
        if current is None:
            time.sleep(poll_interval_s)
            continue

        last_position = current

        if check_position_reached(target, current, tolerance):
            return MotionResult(
                status=MotionStatus.COMPLETED,
                final_position=current,
                duration_s=elapsed,
            )

        time.sleep(poll_interval_s)


def wait_for_idle(
    get_status_fn: Callable[[], str],
    idle_states: List[str] = None,
    error_states: List[str] = None,
    timeout_s: float = 10.0,
    poll_interval_s: float = 0.1,
) -> MotionResult:
    """Poll a status callback until it reports idle, error, or timeout."""
    if idle_states is None:
        idle_states = ["IDLE", "XBOT_IDLE", "idle"]
    if error_states is None:
        error_states = ["ERROR", "XBOT_ERROR", "STOPPED", "XBOT_STOPPED", "error"]

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed >= timeout_s:
            return MotionResult(
                status=MotionStatus.TIMEOUT,
                error_message=f"Timeout waiting for idle after {timeout_s:.1f}s",
                duration_s=elapsed,
            )

        try:
            current_status = get_status_fn()
        except Exception as e:
            return MotionResult(
                status=MotionStatus.ERROR,
                error_message=f"Error getting status: {e}",
                duration_s=elapsed,
            )

        if current_status in idle_states:
            return MotionResult(status=MotionStatus.COMPLETED, duration_s=elapsed)

        if current_status in error_states:
            return MotionResult(
                status=MotionStatus.ERROR,
                error_message=f"Controller in error state: {current_status}",
                duration_s=elapsed,
            )

        time.sleep(poll_interval_s)


@dataclass
class VelocityParams:
    """Common velocity and acceleration settings."""

    max_velocity: float = 0.1
    max_acceleration: float = 0.5

    xy_velocity: Optional[float] = None
    z_velocity: Optional[float] = None
    rotation_velocity: Optional[float] = None

    def get_xy_velocity(self) -> float:
        """Returns the XY velocity (fallback: `max_velocity`)."""
        return self.xy_velocity if self.xy_velocity is not None else self.max_velocity

    def get_z_velocity(self) -> float:
        """Returns the Z velocity (fallback: `max_velocity`)."""
        return self.z_velocity if self.z_velocity is not None else self.max_velocity


def interpolate_position(start: List[float], end: List[float], t: float) -> List[float]:
    """Linearly interpolate between two positions."""
    t = max(0.0, min(1.0, t))
    return [s + t * (e - s) for s, e in zip(start, end)]
