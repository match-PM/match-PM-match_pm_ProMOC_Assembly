"""Plain unit conversions used across the ROS nodes."""

import math


def m_to_mm(value: float) -> float:
    """Meters to millimeters."""
    return value * 1000.0


def mm_to_m(value: float) -> float:
    """Millimeters to meters."""
    return value / 1000.0


def um_to_mm(value: float) -> float:
    """Micrometers to millimeters."""
    return value / 1000.0


def mm_to_um(value: float) -> float:
    """Millimeters to micrometers."""
    return value * 1000.0


def um_to_m(value: float) -> float:
    """Micrometers to meters."""
    return value / 1_000_000.0


def m_to_um(value: float) -> float:
    """Meters to micrometers."""
    return value * 1_000_000.0


def rad_to_deg(value: float) -> float:
    """Radians to degrees."""
    return math.degrees(value)


def deg_to_rad(value: float) -> float:
    """Degrees to radians."""
    return math.radians(value)


def mrad_to_deg(value: float) -> float:
    """Milliradians to degrees."""
    return math.degrees(value / 1000.0)


def deg_to_mrad(value: float) -> float:
    """Degrees to milliradians."""
    return math.radians(value) * 1000.0


def lp_mm_to_lp_px(lp_mm: float, pixel_size_um: float) -> float:
    """Line pairs per millimeter to line pairs per pixel."""
    return lp_mm * um_to_mm(pixel_size_um)


def lp_px_to_lp_mm(lp_px: float, pixel_size_um: float) -> float:
    """Line pairs per pixel to line pairs per millimeter."""
    return lp_px / um_to_mm(pixel_size_um)


def nyquist_frequency_lp_mm(pixel_size_um: float) -> float:
    """Camera Nyquist frequency in line pairs per millimeter."""
    return lp_px_to_lp_mm(0.5, pixel_size_um)


def mm_s_to_m_s(value: float) -> float:
    """Millimeters per second to meters per second."""
    return value / 1000.0


def m_s_to_mm_s(value: float) -> float:
    """Meters per second to millimeters per second."""
    return value * 1000.0
