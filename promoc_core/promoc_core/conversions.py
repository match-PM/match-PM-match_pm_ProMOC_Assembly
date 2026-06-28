"""Einheitenumrechnungen fuer alle ROS-Knoten.

Unterstuetzte Einheiten: Meter (m), Millimeter (mm), Mikrometer (um),
Grad (deg), Radiant (rad), Milliradiant (mrad), Linienpaare/mm, Pixel.
"""

import math


def m_to_mm(value: float) -> float:
    """Meter nach Millimeter (x1000)."""
    return value * 1000.0


def mm_to_m(value: float) -> float:
    """Millimeter nach Meter (/1000)."""
    return value / 1000.0


def um_to_mm(value: float) -> float:
    """Mikrometer nach Millimeter (/1000)."""
    return value / 1000.0


def mm_to_um(value: float) -> float:
    """Millimeter nach Mikrometer (x1000)."""
    return value * 1000.0


def um_to_m(value: float) -> float:
    """Mikrometer nach Meter (/1.000.000)."""
    return value / 1_000_000.0


def m_to_um(value: float) -> float:
    """Meter nach Mikrometer (x1.000.000)."""
    return value * 1_000_000.0


def rad_to_deg(value: float) -> float:
    """Radiant nach Grad (x180/pi)."""
    return math.degrees(value)


def deg_to_rad(value: float) -> float:
    """Grad nach Radiant (xpi/180)."""
    return math.radians(value)


def mrad_to_deg(value: float) -> float:
    """Milliradiant nach Grad."""
    return math.degrees(value / 1000.0)


def deg_to_mrad(value: float) -> float:
    """Grad nach Milliradiant."""
    return math.radians(value) * 1000.0


def lp_mm_to_lp_px(lp_mm: float, pixel_size_um: float) -> float:
    """Linienpaare pro mm nach Linienpaare pro Pixel (Kamera-MTF)."""
    return lp_mm * um_to_mm(pixel_size_um)


def lp_px_to_lp_mm(lp_px: float, pixel_size_um: float) -> float:
    """Linienpaare pro Pixel nach Linienpaare pro mm."""
    return lp_px / um_to_mm(pixel_size_um)


def nyquist_frequency_lp_mm(pixel_size_um: float) -> float:
    """Kamera-Nyquist-Frequenz in Linienpaaren pro mm (0.5 lp/px)."""
    return lp_px_to_lp_mm(0.5, pixel_size_um)


def mm_s_to_m_s(value: float) -> float:
    """mm/s nach m/s."""
    return value / 1000.0


def m_s_to_mm_s(value: float) -> float:
    """m/s nach mm/s."""
    return value * 1000.0
