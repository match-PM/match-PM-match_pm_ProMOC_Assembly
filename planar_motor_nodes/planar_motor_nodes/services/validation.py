"""Service-level validation helpers for planar motor requests."""


def require_non_negative(value: float, name: str) -> float:
    numeric = float(value)
    if numeric < 0:
        raise ValueError(f"{name} must be non-negative, got {numeric}")
    return numeric
