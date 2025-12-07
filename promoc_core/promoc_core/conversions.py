"""
Unit Conversion Utilities for ProMOC Assembly
==============================================

This module provides common unit conversion functions for use across
all ProMOC nodes and components. Using these functions ensures
consistency and reduces conversion errors.

**Important:** Always use these functions instead of inline calculations!
    ✓ position_m = mm_to_m(position_mm)
    ✗ position_m = position_mm / 1000  # Avoid!

Quick Start
-----------
1. **Length conversions (most common):**
   
   >>> from promoc_core.conversions import mm_to_m, m_to_mm, um_to_mm
   >>> 
   >>> # ROS uses meters, hardware often uses mm
   >>> position_ros = mm_to_m(150.0)  # 0.15 m
   >>> position_hw = m_to_mm(0.15)    # 150.0 mm
   >>> 
   >>> # Pixel sizes are often in micrometers
   >>> pixel_size_mm = um_to_mm(3.45)  # 0.00345 mm

2. **Angle conversions:**
   
   >>> from promoc_core.conversions import deg_to_rad, rad_to_deg
   >>> 
   >>> angle_rad = deg_to_rad(90.0)  # 1.5708... rad
   >>> angle_deg = rad_to_deg(3.14159)  # 180.0 deg

3. **Optical/MTF conversions (for camera/lens testing):**
   
   >>> from promoc_core.conversions import lp_mm_to_lp_px, nyquist_frequency_lp_mm
   >>> 
   >>> # Convert spatial frequency units
   >>> lp_per_pixel = lp_mm_to_lp_px(100, pixel_size_um=3.45)  # 0.345
   >>> 
   >>> # Calculate Nyquist limit
   >>> nyquist = nyquist_frequency_lp_mm(3.45)  # 144.93 lp/mm

4. **Velocity conversions:**
   
   >>> from promoc_core.conversions import mm_s_to_m_s, m_s_to_mm_s
   >>> 
   >>> velocity_ros = mm_s_to_m_s(50.0)  # 0.05 m/s
   >>> velocity_hw = m_s_to_mm_s(0.05)   # 50.0 mm/s

Conversion Categories
---------------------
- Length:   m ↔ mm ↔ µm (meters, millimeters, micrometers)
- Angle:    rad ↔ deg ↔ mrad (radians, degrees, milliradians)
- Optical:  lp/mm ↔ lp/px (line pairs per mm/pixel)
- Velocity: m/s ↔ mm/s
"""
import math
from typing import Union


# =============================================================================
# Length Conversions
# =============================================================================
# These are the most commonly used conversions in ProMOC.
# ROS typically uses meters (SI), but hardware interfaces often use mm.

def m_to_mm(value: float) -> float:
    """
    Convert meters to millimeters.

    Use when: Sending positions to hardware that expects mm.

    Args:
        value: Length in meters

    Returns:
        Length in millimeters

    Example:
        >>> m_to_mm(0.15)  # 150mm in ROS coordinates
        150.0
    """
    return value * 1000.0


def mm_to_m(value: float) -> float:
    """
    Convert millimeters to meters.

    Use when: Converting hardware readings (mm) to ROS (meters).

    Args:
        value: Length in millimeters

    Returns:
        Length in meters

    Example:
        >>> mm_to_m(150.0)  # Hardware reports 150mm
        0.15
    """
    return value / 1000.0


def um_to_mm(value: float) -> float:
    """
    Convert micrometers to millimeters.

    Use when: Working with pixel sizes or fine positioning.

    Args:
        value: Length in micrometers (µm)

    Returns:
        Length in millimeters

    Example:
        >>> um_to_mm(3.45)  # Typical camera pixel size
        0.00345
    """
    return value / 1000.0


def mm_to_um(value: float) -> float:
    """
    Convert millimeters to micrometers.

    Use when: Converting to fine precision units.

    Args:
        value: Length in millimeters

    Returns:
        Length in micrometers (µm)

    Example:
        >>> mm_to_um(0.001)  # 1 micron positioning accuracy
        1.0
    """
    return value * 1000.0


def um_to_m(value: float) -> float:
    """
    Convert micrometers to meters.

    Use when: Converting fine measurements directly to ROS units.

    Args:
        value: Length in micrometers (µm)

    Returns:
        Length in meters

    Example:
        >>> um_to_m(3.45)  # Pixel size to meters
        3.45e-06
    """
    return value / 1_000_000.0


def m_to_um(value: float) -> float:
    """
    Convert meters to micrometers.

    Args:
        value: Length in meters

    Returns:
        Length in micrometers (µm)

    Example:
        >>> m_to_um(0.001)  # 1mm in micrometers
        1000.0
    """
    return value * 1_000_000.0


# =============================================================================
# Angle Conversions
# =============================================================================
# ROS uses radians, but humans and some interfaces use degrees.

def rad_to_deg(value: float) -> float:
    """
    Convert radians to degrees.

    Use when: Displaying angles to users or logging.

    Args:
        value: Angle in radians

    Returns:
        Angle in degrees

    Example:
        >>> rad_to_deg(3.14159)  # π radians
        180.0
    """
    return math.degrees(value)


def deg_to_rad(value: float) -> float:
    """
    Convert degrees to radians.

    Use when: Converting user input to ROS angles.

    Args:
        value: Angle in degrees

    Returns:
        Angle in radians

    Example:
        >>> deg_to_rad(90.0)
        1.5707963267948966
    """
    return math.radians(value)


def mrad_to_deg(value: float) -> float:
    """
    Convert milliradians to degrees.

    Use when: Working with precision optics (tilt stages, etc.)

    Args:
        value: Angle in milliradians

    Returns:
        Angle in degrees

    Example:
        >>> mrad_to_deg(17.45)  # ~1 degree
        1.0
    """
    return math.degrees(value / 1000.0)


def deg_to_mrad(value: float) -> float:
    """
    Convert degrees to milliradians.

    Args:
        value: Angle in degrees

    Returns:
        Angle in milliradians
    """
    return math.radians(value) * 1000.0


# =============================================================================
# Optical / MTF Conversions
# =============================================================================
# These are used for lens testing and MTF analysis.
# Line pairs (lp) measure how well a lens can resolve fine details.

def lp_mm_to_lp_px(lp_mm: float, pixel_size_um: float) -> float:
    """
    Convert line pairs per millimeter to line pairs per pixel.

    Use when: Converting from physical frequency (lp/mm) to digital
    frequency (lp/pixel) for image analysis.

    Background:
        - lp/mm: How many line pairs fit in 1mm (physical units)
        - lp/pixel: How many line pairs fit in 1 pixel (digital units)
        - If lp/pixel > 0.5, the frequency is beyond Nyquist limit!

    Args:
        lp_mm: Spatial frequency in line pairs per millimeter
        pixel_size_um: Camera pixel size in micrometers

    Returns:
        Spatial frequency in line pairs per pixel

    Example:
        >>> # 100 lp/mm with a 3.45µm pixel camera
        >>> lp_mm_to_lp_px(100, 3.45)
        0.345  # Well below Nyquist (0.5), good!
        >>> 
        >>> # 200 lp/mm with same camera
        >>> lp_mm_to_lp_px(200, 3.45)
        0.69  # Above Nyquist, will alias!
    """
    pixel_size_mm = um_to_mm(pixel_size_um)
    return lp_mm * pixel_size_mm


def lp_px_to_lp_mm(lp_px: float, pixel_size_um: float) -> float:
    """
    Convert line pairs per pixel to line pairs per millimeter.

    Use when: Converting from digital frequency back to physical.

    Args:
        lp_px: Spatial frequency in line pairs per pixel
        pixel_size_um: Camera pixel size in micrometers

    Returns:
        Spatial frequency in line pairs per millimeter

    Example:
        >>> # Nyquist frequency (0.5 lp/px) for 3.45µm pixels
        >>> lp_px_to_lp_mm(0.5, 3.45)
        144.93  # Max resolvable frequency
    """
    pixel_size_mm = um_to_mm(pixel_size_um)
    return lp_px / pixel_size_mm


def nyquist_frequency_lp_mm(pixel_size_um: float) -> float:
    """
    Calculate Nyquist frequency in line pairs per millimeter.

    The Nyquist frequency is the maximum spatial frequency that
    can be resolved without aliasing. It equals 0.5 line pairs 
    per pixel (1 line pair = 2 pixels).

    Use when: Determining the maximum resolvable detail for a camera.

    Args:
        pixel_size_um: Camera pixel size in micrometers

    Returns:
        Nyquist frequency in lp/mm

    Example:
        >>> # Camera with 3.45µm pixels
        >>> nyquist_frequency_lp_mm(3.45)
        144.93  # Cannot resolve > 144.93 lp/mm
    """
    return lp_px_to_lp_mm(0.5, pixel_size_um)


def cycles_per_pixel_to_lp_mm(cpp: float, pixel_size_um: float) -> float:
    """
    Convert cycles per pixel to line pairs per millimeter.

    Note: 1 cycle = 1 line pair, so this is equivalent to lp_px_to_lp_mm.

    Args:
        cpp: Frequency in cycles per pixel
        pixel_size_um: Camera pixel size in micrometers

    Returns:
        Spatial frequency in lp/mm
    """
    return lp_px_to_lp_mm(cpp, pixel_size_um)


# =============================================================================
# Speed / Velocity Conversions
# =============================================================================
# Convert between hardware velocity units and ROS velocity units.

def mm_s_to_m_s(value: float) -> float:
    """
    Convert millimeters per second to meters per second.

    Use when: Converting hardware velocity to ROS (which uses m/s).

    Args:
        value: Speed in mm/s

    Returns:
        Speed in m/s

    Example:
        >>> mm_s_to_m_s(50.0)  # Hardware max velocity
        0.05
    """
    return value / 1000.0


def m_s_to_mm_s(value: float) -> float:
    """
    Convert meters per second to millimeters per second.

    Use when: Sending velocity commands to hardware (which expects mm/s).

    Args:
        value: Speed in m/s

    Returns:
        Speed in mm/s

    Example:
        >>> m_s_to_mm_s(0.1)  # ROS velocity command
        100.0
    """
    return value * 1000.0
