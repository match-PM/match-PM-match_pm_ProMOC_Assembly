"""Unit tests for promoc_core.motion_interface."""

from __future__ import annotations

import time

import pytest

from promoc_core.motion import MotionStatus
from promoc_core.motion_interface import (
    MotionExecutionResult,
    compute_motion_timeout,
    normalize_motion_status,
    wait_for_idle_state,
)


class _SequencePort:
    """Minimal fake port that replays pre-defined statuses."""

    def __init__(self, statuses, *, position=None, raise_on_read=False):
        self._statuses = list(statuses)
        self._position = position if position is not None else [0.0]
        self._raise_on_read = raise_on_read
        self._idx = 0

    def read_position(self, actor_id=None):
        return list(self._position)

    def read_status(self, actor_id=None):
        if self._raise_on_read:
            raise RuntimeError("backend disconnected")

        if self._idx >= len(self._statuses):
            return self._statuses[-1]

        value = self._statuses[self._idx]
        self._idx += 1
        return value

    def command(self, command, actor_id=None):
        return MotionExecutionResult(status=MotionStatus.MOVING)

    def stop(self, actor_id=None):
        return MotionExecutionResult(status=MotionStatus.ABORTED)


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("IDLE", MotionStatus.IDLE),
        ("XBOT_IDLE", MotionStatus.IDLE),
        ("XbotState.XBOT_MOTION", MotionStatus.MOVING),
        ("ERROR", MotionStatus.ERROR),
        ("XBOT_STOPPED", MotionStatus.ABORTED),
        ("XBOT_OBSTACLE_DETECTED", MotionStatus.COLLISION),
        (None, MotionStatus.UNKNOWN),
    ],
)
def test_normalize_motion_status(raw_status, expected):
    """Status normalization maps backend strings into shared MotionStatus."""
    assert normalize_motion_status(raw_status) == expected


def test_compute_motion_timeout_uses_shared_formula_and_fallback():
    """Timeout helper uses shared formula and fallback semantics."""
    assert compute_motion_timeout(2.0, multiplier=1.5, buffer_s=1.0, min_s=2.0) == 4.0
    assert compute_motion_timeout(None, min_s=5.0, fallback_s=7.0) == 7.0
    assert compute_motion_timeout(None, min_s=5.0) == 5.0


def test_wait_for_idle_state_completes_when_backend_reaches_idle():
    """Wait helper returns completed when backend transitions to idle."""
    port = _SequencePort(["XBOT_MOTION", "XBOT_IDLE"], position=[0.12, 0.18, 0.001])

    result = wait_for_idle_state(port, actor_id=0, timeout_s=1.0, poll_interval_s=0.01)

    assert result.status == MotionStatus.COMPLETED
    assert result.final_position == [0.12, 0.18, 0.001]


def test_wait_for_idle_state_times_out_when_motion_never_finishes():
    """Wait helper returns timeout when backend never reaches idle."""
    port = _SequencePort(["XBOT_MOTION"])
    started = time.monotonic()

    result = wait_for_idle_state(port, actor_id=0, timeout_s=0.03, poll_interval_s=0.01)

    elapsed = time.monotonic() - started
    assert result.status == MotionStatus.TIMEOUT
    assert elapsed >= 0.03


def test_wait_for_idle_state_surfaces_status_read_errors():
    """Status read exceptions are normalized into MotionStatus.ERROR."""
    port = _SequencePort(["XBOT_IDLE"], raise_on_read=True)

    result = wait_for_idle_state(port, actor_id=0, timeout_s=0.2, poll_interval_s=0.01)

    assert result.status == MotionStatus.ERROR
    assert "status read failed" in result.message
