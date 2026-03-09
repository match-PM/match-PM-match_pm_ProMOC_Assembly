"""Adapter-level validation helpers for planar-motor mappings."""


def require_positive(value: float, name: str) -> float:
    numeric = float(value)
    if numeric <= 0:
        raise ValueError(f"{name} must be positive, got {numeric}")
    return numeric
