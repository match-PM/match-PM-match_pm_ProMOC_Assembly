"""Linear-axis adapter layer."""

from .conversions import m_to_mm, mm_to_m
from .mapping import normalize_axis_name
from .validation import require_finite


__all__ = [
    "m_to_mm",
    "mm_to_m",
    "normalize_axis_name",
    "require_finite",
]
