"""Adapter conversion helpers for planar-motor requests."""

import math


def deg_to_rad(value_deg: float) -> float:
    return math.radians(float(value_deg))


def mm_to_m(value_mm: float) -> float:
    return float(value_mm) / 1000.0
