import math
import pytest
from promoc_core.conversions import (
    m_to_mm, mm_to_m,
    um_to_mm, mm_to_um,
    um_to_m, m_to_um,
    deg_to_rad, rad_to_deg,
    mrad_to_deg, deg_to_mrad,
    mm_s_to_m_s, m_s_to_mm_s,
    lp_mm_to_lp_px, lp_px_to_lp_mm
)

def test_length_conversions():
    """Test basic length conversions (m <-> mm <-> um)."""
    # m <-> mm
    assert m_to_mm(1.0) == 1000.0
    assert m_to_mm(0.0015) == 1.5
    assert mm_to_m(1000.0) == 1.0
    assert mm_to_m(1.5) == 0.0015

    # mm <-> um
    assert mm_to_um(1.0) == 1000.0
    assert um_to_mm(1000.0) == 1.0
    
    # m <-> um
    assert m_to_um(1.0) == 1_000_000.0
    assert um_to_m(1_000_000.0) == 1.0

def test_angle_conversions():
    """Test angle conversions (deg <-> rad)."""
    # deg <-> rad
    assert rad_to_deg(math.pi) == 180.0
    assert rad_to_deg(math.pi / 2) == 90.0
    assert deg_to_rad(180.0) == pytest.approx(math.pi)
    assert deg_to_rad(90.0) == pytest.approx(math.pi / 2)

    # mrad <-> deg
    # 1 mrad approx 0.0572958 degrees
    assert mrad_to_deg(1000.0) == pytest.approx(math.degrees(1.0))
    assert deg_to_mrad(1.0) == pytest.approx(math.radians(1.0) * 1000.0)

def test_velocity_conversions():
    """Test velocity conversions."""
    assert mm_s_to_m_s(1000.0) == 1.0
    assert m_s_to_mm_s(1.0) == 1000.0

def test_optical_conversions():
    """Test optical/MTF conversions."""
    # Pixel size 3.45um.
    # 100 lp/mm -> ? lp/px
    # 100 lp/mm * (3.45um / 1000) = 100 * 0.00345 = 0.345 lp/px
    lp_px = lp_mm_to_lp_px(100.0, pixel_size_um=3.45)
    assert lp_px == pytest.approx(0.345)

    # Inverse
    assert lp_px_to_lp_mm(0.345, pixel_size_um=3.45) == pytest.approx(100.0)
