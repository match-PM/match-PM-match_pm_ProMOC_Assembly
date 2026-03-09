"""Adapter mapping helpers for linear-axis message fields."""


def normalize_axis_name(axis_name: str) -> str:
    """Normalize axis name to canonical lower-case identifier."""
    return str(axis_name or "").strip().lower()
