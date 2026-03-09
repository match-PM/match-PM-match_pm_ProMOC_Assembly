"""Adapter-level unit conversions for linear-axis services."""


def mm_to_m(value_mm: float) -> float:
    return float(value_mm) / 1000.0


def m_to_mm(value_m: float) -> float:
    return float(value_m) * 1000.0
