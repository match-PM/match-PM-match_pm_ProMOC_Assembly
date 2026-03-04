"""\
Unit Conversions for ProMOC Assembly
======================================

This module provides common conversion functions that can be used across all
ProMOC nodes and components. This ensures that units remain consistent and
typical conversion errors are avoided.

Important
---------
Please **always** use these functions instead of inline calculations:

     ✓ position_m = mm_to_m(position_mm)
     ✗ position_m = position_mm / 1000  # avoid!

Quickstart
----------
1) **Length (most common case):**

    >>> from promoc_core.conversions import mm_to_m, m_to_mm, um_to_mm
    >>>
    >>> # ROS typically uses meters (SI), while hardware often uses millimeters.
    >>> position_ros = mm_to_m(150.0)  # 0.15 m
    >>> position_hw = m_to_mm(0.15)    # 150.0 mm
    >>>
    >>> # Pixel sizes are often specified in micrometers.
    >>> pixel_size_mm = um_to_mm(3.45)  # 0.00345 mm

2) **Angles:**

    >>> from promoc_core.conversions import deg_to_rad, rad_to_deg
    >>>
    >>> angle_rad = deg_to_rad(90.0)  # 1.5708... rad
    >>> angle_deg = rad_to_deg(3.14159)  # 180.0 deg

3) **Optics/MTF (e.g., for camera/lens testing):**

    >>> from promoc_core.conversions import lp_mm_to_lp_px, nyquist_frequency_lp_mm
    >>>
    >>> # Conversion of spatial frequencies
    >>> lp_per_pixel = lp_mm_to_lp_px(100, pixel_size_um=3.45)  # 0.345
    >>>
    >>> # Calculate Nyquist limit
    >>> nyquist = nyquist_frequency_lp_mm(3.45)  # 144.93 lp/mm

4) **Velocity:**

    >>> from promoc_core.conversions import mm_s_to_m_s, m_s_to_mm_s
    >>>
    >>> velocity_ros = mm_s_to_m_s(50.0)  # 0.05 m/s
    >>> velocity_hw = m_s_to_mm_s(0.05)   # 50.0 mm/s

Categories
----------
- Length:   m ↔ mm ↔ µm
- Angle:    rad ↔ deg ↔ mrad
- Optics:   lp/mm ↔ lp/px
- Speed:    m/s ↔ mm/s
"""
import math


# =============================================================================
# Length Conversions
# =============================================================================
# These are the most frequently used conversions in ProMOC.
# ROS typically works in meters (SI), while hardware interfaces often use mm.

def m_to_mm(value: float) -> float:
    """
    Converts meters to millimeters.

    Use when sending positions to hardware that expects mm.

    Args:
        value: Length in meters.

    Returns:
        Length in millimeters.

    Example:
        >>> m_to_mm(0.15)  # 150mm
        150.0
    """
    return value * 1000.0


def mm_to_m(value: float) -> float:
    """
    Converts millimeters to meters.

    Use when converting hardware values (mm) to ROS units (m).

    Args:
        value: Length in millimeters.

    Returns:
        Length in meters.

    Example:
        >>> mm_to_m(150.0)  # Hardware reports 150mm
        0.15
    """
    return value / 1000.0


def um_to_mm(value: float) -> float:
    """
    Converts micrometers (µm) to millimeters.

    Use when dealing with pixel sizes or fine positioning.

    Args:
        value: Length in micrometers (µm).

    Returns:
        Length in millimeters.

    Example:
        >>> um_to_mm(3.45)  # typical pixel size
        0.00345
    """
    return value / 1000.0


def mm_to_um(value: float) -> float:
    """
    Converts millimeters to micrometers (µm).

    Use when conversion to finer units is necessary.

    Args:
        value: Length in millimeters.

    Returns:
        Length in micrometers (µm).

    Example:
        >>> mm_to_um(0.001)  # 1µm
        1.0
    """
    return value * 1000.0


def um_to_m(value: float) -> float:
    """
    Converts micrometers (µm) to meters.

    Use when fine measurements are needed directly in ROS units (m).

    Args:
        value: Length in micrometers (µm).

    Returns:
        Length in meters.

    Example:
        >>> um_to_m(3.45)
        3.45e-06
    """
    return value / 1_000_000.0


def m_to_um(value: float) -> float:
    """
    Converts meters to micrometers (µm).

    Args:
        value: Length in meters.

    Returns:
        Length in micrometers (µm).

    Example:
        >>> m_to_um(0.001)  # 1mm
        1000.0
    """
    return value * 1_000_000.0


# =============================================================================
# Angle Conversions
# =============================================================================
# ROS uses radians, while humans and some interfaces use degrees.

def rad_to_deg(value: float) -> float:
    """
    Converts radians to degrees.

    Use when displaying angles for users or in logs.

    Args:
        value: Angle in radians.

    Returns:
        Angle in degrees.

    Example:
        >>> rad_to_deg(3.14159)  # π
        180.0
    """
    return math.degrees(value)


def deg_to_rad(value: float) -> float:
    """
    Converts degrees to radians.

    Use when converting user input (degrees) to ROS angles (radians).

    Args:
        value: Angle in degrees.

    Returns:
        Angle in radians.

    Example:
        >>> deg_to_rad(90.0)
        1.5707963267948966
    """
    return math.radians(value)


def mrad_to_deg(value: float) -> float:
    """
    Converts milliradians (mrad) to degrees.

    Use when dealing with precision optics, tilt stages, etc.

    Args:
        value: Angle in milliradians.

    Returns:
        Angle in degrees.

    Example:
        >>> mrad_to_deg(17.45)  # ~1 degree
        1.0
    """
    return math.degrees(value / 1000.0)


def deg_to_mrad(value: float) -> float:
    """
    Converts degrees to milliradians (mrad).

    Args:
        value: Angle in degrees.

    Returns:
        Angle in milliradians.
    """
    return math.radians(value) * 1000.0


# =============================================================================
# Optical / MTF Conversions
# =============================================================================
# These conversions are used for lens testing and MTF analysis.
# Line pairs (lp) describe how well an optic can resolve fine details.

def lp_mm_to_lp_px(lp_mm: float, pixel_size_um: float) -> float:
    """
    Converts line pairs per millimeter (lp/mm) to line pairs per pixel (lp/px).

    Use when converting from a physical spatial frequency (lp/mm) to a digital
    spatial frequency (lp/px) for image analysis.

    Background:
        - lp/mm: How many line pairs fit into 1mm (physical).
        - lp/pixel: How many line pairs fit into 1 pixel (digital).
        - If lp/pixel > 0.5, the frequency is above the Nyquist limit.

    Args:
        lp_mm: Spatial frequency in line pairs per millimeter.
        pixel_size_um: The camera's pixel size in micrometers.

    Returns:
        Spatial frequency in line pairs per pixel.

    Example:
        >>> lp_mm_to_lp_px(100, 3.45)
        0.345
        >>> lp_mm_to_lp_px(200, 3.45)
        0.69
    """
    pixel_size_mm = um_to_mm(pixel_size_um)
    return lp_mm * pixel_size_mm


def lp_px_to_lp_mm(lp_px: float, pixel_size_um: float) -> float:
    """
    Converts line pairs per pixel (lp/px) to line pairs per millimeter (lp/mm).

    Use when converting a digital spatial frequency back into physical units.

    Args:
        lp_px: Spatial frequency in line pairs per pixel.
        pixel_size_um: Pixel size in micrometers.

    Returns:
        Spatial frequency in line pairs per millimeter.

    Example:
        >>> lp_px_to_lp_mm(0.5, 3.45)
        144.93
    """
    pixel_size_mm = um_to_mm(pixel_size_um)
    return lp_px / pixel_size_mm


def nyquist_frequency_lp_mm(pixel_size_um: float) -> float:
    """
    Calculates the Nyquist frequency in lp/mm.

    The Nyquist frequency is the maximum spatial frequency that can be resolved
    without aliasing. It corresponds to 0.5 lp/px (1 line pair = 2 pixels).

    Use when determining the maximum resolvable detail frequency of a camera.

    Args:
        pixel_size_um: Pixel size in micrometers.

    Returns:
        The Nyquist frequency in lp/mm.

    Example:
        >>> nyquist_frequency_lp_mm(3.45)
        144.93
    """
    return lp_px_to_lp_mm(0.5, pixel_size_um)


def cycles_per_pixel_to_lp_mm(cpp: float, pixel_size_um: float) -> float:
    """
    Converts cycles per pixel (cpp) to line pairs per millimeter (lp/mm).

    Note: 1 cycle = 1 line pair. Therefore, this is equivalent to `lp_px_to_lp_mm`.

    Args:
        cpp: Frequency in cycles per pixel.
        pixel_size_um: Pixel size in micrometers.

    Returns:
        Spatial frequency in lp/mm.
    """
    return lp_px_to_lp_mm(cpp, pixel_size_um)


# =============================================================================
# Speed / Velocity Conversions
# =============================================================================
# Conversion between hardware velocity units and ROS units.

def mm_s_to_m_s(value: float) -> float:
    """
    Converts mm/s to m/s.

    Use when converting hardware velocity (mm/s) to ROS velocity (m/s).

    Args:
        value: Velocity in mm/s.

    Returns:
        Velocity in m/s.

    Example:
        >>> mm_s_to_m_s(50.0)
        0.05
    """
    return value / 1000.0


def m_s_to_mm_s(value: float) -> float:
    """
    Converts m/s to mm/s.

    Use when sending velocity commands to hardware that expects mm/s.

    Args:
        value: Velocity in m/s.

    Returns:
        Velocity in mm/s.

    Example:
        >>> m_s_to_mm_s(0.1)
        100.0
    """
    return value * 1000.0
