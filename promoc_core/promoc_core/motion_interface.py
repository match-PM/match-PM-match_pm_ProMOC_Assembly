"""Shared motion interface primitives for ProMOC nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .motion import MotionStatus


class MotionCommandName(str, Enum):
    """Canonical internal motion command names across adapters."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    HOME = "home"
    JOG = "jog"
    LINEAR_XY = "linear_motion_si"
    SIX_DOF = "six_d_of_motion_si"
    ROTARY = "rotary_motion"
    ARC = "arc_motion_si"


MotionActorId = int | str


@dataclass(frozen=True)
class MotionCommand:
    """Typed motion command model passed into :class:`MotionPort`."""

    name: MotionCommandName | str
    target_position: Sequence[float] | None = None
    params: Mapping[str, float | int | str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class MotionExecutionResult:
    """Typed command execution result returned by motion adapters."""

    status: MotionStatus
    message: str = ""
    final_position: list[float] | None = None
    travel_time_s: float | None = None
    raw_status: str | None = None

    @property
    def success(self) -> bool:
        """Whether the motion result indicates a successful completion."""
        return self.status in (MotionStatus.COMPLETED, MotionStatus.IDLE)


@runtime_checkable
class MotionPort(Protocol):
    """Minimal motion adapter contract implemented by axis/motor backends."""

    def read_position(
        self, actor_id: MotionActorId | None = None
    ) -> list[float] | None:
        """Return current position for an actor in SI units."""

    def read_status(self, actor_id: MotionActorId | None = None) -> MotionStatus | str:
        """Return backend motion status as enum or backend status string."""

    def command(
        self,
        command: MotionCommand,
        actor_id: MotionActorId | None = None,
    ) -> MotionExecutionResult:
        """Send a command to the backend and return immediate execution metadata."""

    def stop(self, actor_id: MotionActorId | None = None) -> MotionExecutionResult:
        """Stop the actor as quickly as possible."""


_IDLE_STATUS_TOKENS = {
    "IDLE",
    "READY",
    "DONE",
    "COMPLETED",
    "SUCCESS",
    "XBOT_IDLE",
}

_MOVING_STATUS_TOKENS = {
    "MOVING",
    "MOTION",
    "RUNNING",
    "BUSY",
    "WAIT",
    "HOMING",
    "JOGGING",
    "XBOT_MOTION",
    "XBOT_WAIT",
}

_ERROR_STATUS_TOKENS = {
    "ERROR",
    "FAILED",
    "FAULT",
    "XBOT_ERROR",
}

_ABORTED_STATUS_TOKENS = {
    "ABORTED",
    "STOPPED",
    "EMERGENCY_STOP",
    "XBOT_STOPPED",
    "XBOT_STOPPING",
}

_COLLISION_STATUS_TOKENS = {
    "COLLISION",
    "OBSTACLE",
    "XBOT_OBSTACLE_DETECTED",
}


def _status_candidates(raw_status: object) -> tuple[str, ...]:
    token = str(raw_status).strip().upper()
    if not token:
        return ()
    if "." in token:
        return (token, token.split(".")[-1])
    return (token,)


def normalize_motion_status(status: MotionStatus | str | Enum | None) -> MotionStatus:
    """Map backend status values into the shared :class:`MotionStatus` enum."""
    if isinstance(status, MotionStatus):
        return status

    if status is None:
        return MotionStatus.UNKNOWN

    status_to_map: object = status.name if isinstance(status, Enum) else status

    for candidate in _status_candidates(status_to_map):
        if candidate in _IDLE_STATUS_TOKENS:
            return MotionStatus.IDLE
        if candidate in _MOVING_STATUS_TOKENS:
            return MotionStatus.MOVING
        if candidate in _ERROR_STATUS_TOKENS:
            return MotionStatus.ERROR
        if candidate in _ABORTED_STATUS_TOKENS:
            return MotionStatus.ABORTED
        if candidate in _COLLISION_STATUS_TOKENS:
            return MotionStatus.COLLISION

    return MotionStatus.UNKNOWN


def compute_motion_timeout(
    travel_time_s: float | None,
    *,
    multiplier: float = 1.5,
    buffer_s: float = 3.0,
    min_s: float = 5.0,
    fallback_s: float | None = None,
) -> float:
    """Compute a motion timeout using one shared formula for all motion stacks."""
    if multiplier <= 0:
        raise ValueError("multiplier must be > 0")
    if min_s <= 0:
        raise ValueError("min_s must be > 0")

    if travel_time_s is not None and travel_time_s > 0:
        timeout = (travel_time_s * multiplier) + buffer_s
        return max(float(timeout), float(min_s))

    fallback = min_s if fallback_s is None else fallback_s
    return max(float(fallback), float(min_s))


def _safe_read_position(
    port: MotionPort,
    actor_id: MotionActorId | None,
) -> list[float] | None:
    try:
        return port.read_position(actor_id)
    except Exception:
        return None


def wait_for_idle_state(
    port: MotionPort,
    actor_id: MotionActorId | None = None,
    *,
    timeout_s: float = 10.0,
    poll_interval_s: float = 0.1,
) -> MotionExecutionResult:
    """Poll a motion backend until idle/completed, timeout, or terminal error."""
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")
    if poll_interval_s <= 0:
        raise ValueError("poll_interval_s must be > 0")

    start = time.monotonic()

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout_s:
            return MotionExecutionResult(
                status=MotionStatus.TIMEOUT,
                message=f"timeout waiting for idle after {timeout_s:.1f}s",
                final_position=_safe_read_position(port, actor_id),
                travel_time_s=elapsed,
            )

        try:
            status = normalize_motion_status(port.read_status(actor_id))
        except Exception as exc:
            return MotionExecutionResult(
                status=MotionStatus.ERROR,
                message=f"status read failed: {exc}",
                final_position=_safe_read_position(port, actor_id),
                travel_time_s=elapsed,
            )

        if status in (MotionStatus.IDLE, MotionStatus.COMPLETED):
            return MotionExecutionResult(
                status=MotionStatus.COMPLETED,
                message="controller idle",
                final_position=_safe_read_position(port, actor_id),
                travel_time_s=elapsed,
                raw_status=status.value if hasattr(status, "value") else None,
            )

        if status in (MotionStatus.ERROR, MotionStatus.COLLISION):
            return MotionExecutionResult(
                status=status,
                message=f"terminal backend status: {status.name.lower()}",
                final_position=_safe_read_position(port, actor_id),
                travel_time_s=elapsed,
            )

        if status == MotionStatus.ABORTED:
            return MotionExecutionResult(
                status=MotionStatus.ABORTED,
                message="motion aborted by backend",
                final_position=_safe_read_position(port, actor_id),
                travel_time_s=elapsed,
            )

        time.sleep(poll_interval_s)


__all__ = [
    "MotionActorId",
    "MotionCommand",
    "MotionCommandName",
    "MotionExecutionResult",
    "MotionPort",
    "compute_motion_timeout",
    "normalize_motion_status",
    "wait_for_idle_state",
]
