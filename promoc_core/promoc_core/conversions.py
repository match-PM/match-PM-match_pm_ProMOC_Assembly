"""
Unit conversion utilities for ProMOC Assembly.
"""
import math

def m_to_mm(value: float) -> float:
    """Converts meters to millimeters."""
    return value * 1000.0

def mm_to_m(value: float) -> float:
    """Converts millimeters to meters."""
    return value / 1000.0

def rad_to_deg(value: float) -> float:
    """Converts radians to degrees."""
    return math.degrees(value)

def deg_to_rad(value: float) -> float:
    """Converts degrees to radians."""
    return math.radians(value)
