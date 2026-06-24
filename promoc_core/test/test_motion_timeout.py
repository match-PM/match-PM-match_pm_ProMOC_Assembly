"""Unit tests for shared motion timeout calculation."""

from __future__ import annotations

import pytest

from promoc_core.motion import compute_motion_timeout


def test_compute_motion_timeout_uses_travel_time_formula() -> None:
    assert (
        compute_motion_timeout(
            2.0,
            multiplier=1.5,
            buffer_s=1.0,
            min_s=2.0,
        )
        == 4.0
    )


def test_compute_motion_timeout_uses_fallback_when_travel_time_is_missing() -> None:
    assert compute_motion_timeout(None, min_s=5.0, fallback_s=7.0) == 7.0
    assert compute_motion_timeout(None, min_s=5.0) == 5.0


@pytest.mark.parametrize(
    ("multiplier", "min_s"),
    [
        (0.0, 5.0),
        (1.0, 0.0),
    ],
)
def test_compute_motion_timeout_rejects_invalid_limits(
    multiplier: float,
    min_s: float,
) -> None:
    with pytest.raises(ValueError):
        compute_motion_timeout(1.0, multiplier=multiplier, min_s=min_s)
