"""Adapter-level validation helpers for camera request normalization."""

from __future__ import annotations


def require_positive(name: str, value: float) -> float:
    """Validate that a numeric value is strictly positive."""
    numeric = float(value)
    if numeric <= 0:
        raise ValueError(f"{name} must be > 0, got {numeric}")
    return numeric
