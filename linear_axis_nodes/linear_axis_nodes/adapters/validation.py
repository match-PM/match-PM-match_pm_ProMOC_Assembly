"""Adapter-level validation helpers for linear-axis requests."""


def require_finite(value: float, name: str) -> float:
    numeric = float(value)
    if numeric != numeric:  # NaN guard without extra dependency
        raise ValueError(f"{name} must be finite")
    return numeric
