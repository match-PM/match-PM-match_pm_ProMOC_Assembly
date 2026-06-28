"""Small motion helpers shared by device nodes."""

from __future__ import annotations


def compute_motion_timeout(
    travel_time_s: float | None,
    *,
    multiplier: float = 1.5,
    buffer_s: float = 3.0,
    min_s: float = 5.0,
    fallback_s: float | None = None,
) -> float:
    """Compute a polling timeout from a driver-provided travel time."""
    if multiplier <= 0:
        raise ValueError("multiplier must be > 0")
    if min_s <= 0:
        raise ValueError("min_s must be > 0")

    if travel_time_s is not None and travel_time_s > 0:
        timeout = (travel_time_s * multiplier) + buffer_s
        return max(float(timeout), float(min_s))

    fallback = min_s if fallback_s is None else fallback_s
    return max(float(fallback), float(min_s))
