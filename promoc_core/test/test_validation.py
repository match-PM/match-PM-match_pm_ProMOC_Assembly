from promoc_core.validation import (
    is_in_range, clamp,
    validate_position_3d, validate_position_6d,
    validate_positive, validate_non_negative,
    validate_id_range, check_collision_risk,
    Bounds1D, Bounds3D
)

def test_basic_validation():
    """Test is_in_range and clamp."""
    # is_in_range
    assert is_in_range(5.0, 0.0, 10.0) is True
    assert is_in_range(-1.0, 0.0, 10.0) is False
    assert is_in_range(11.0, 0.0, 10.0) is False
    # Inclusive check
    assert is_in_range(0.0, 0.0, 10.0) is True
    assert is_in_range(10.0, 0.0, 10.0) is True

    # clamp
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-5.0, 0.0, 10.0) == 0.0
    assert clamp(15.0, 0.0, 10.0) == 10.0

def test_validate_position_3d():
    """Test 3D position validation."""
    # Valid
    valid, err = validate_position_3d(1, 1, 1, 0, 2, 0, 2, 0, 2)
    assert valid is True
    assert err is None

    # Invalid X
    valid, err = validate_position_3d(3, 1, 1, 0, 2, 0, 2, 0, 2)
    assert valid is False
    assert "X=" in err

    # Multiple invalid (X and Z)
    valid, err = validate_position_3d(3, 1, -1, 0, 2, 0, 2, 0, 2)
    assert valid is False
    assert "X=" in err
    assert "Z=" in err

def test_validate_position_6d():
    """Test 6D position validation."""
    pos = [0.1, 0.1, 0.1, 0, 0, 0]
    # Simple bounds: all [0, 1]
    bounds = [(0, 1)] * 6
    
    valid, err = validate_position_6d(pos, bounds)
    assert valid is True

    # Invalid length
    valid, err = validate_position_6d([0.1], bounds)
    assert valid is False
    assert "must have 6 elements" in err

    # Invalid value
    pos_bad = [2.0, 0.1, 0.1, 0, 0, 0]
    valid, err = validate_position_6d(pos_bad, bounds)
    assert valid is False
    assert "X=" in err

def test_validate_numeric():
    """Test numeric validations (positive, non-negative)."""
    assert validate_positive(1.0)[0] is True
    assert validate_positive(0.0)[0] is False
    assert validate_positive(-1.0)[0] is False

    assert validate_non_negative(0.0)[0] is True
    assert validate_non_negative(-0.1)[0] is False

def test_validate_id():
    """Test ID range validation."""
    assert validate_id_range(5)[0] is True
    assert validate_id_range(0)[0] is True
    assert validate_id_range(15)[0] is True
    
    # Out of range
    assert validate_id_range(-1)[0] is False
    assert validate_id_range(16)[0] is False

    # Wrong type
    assert validate_id_range(5.5)[0] is False

def test_collision_risk():
    """Test collision risk logic."""
    threshold = 100.0
    
    # Safe: other axis below threshold
    is_safe, msg = check_collision_risk(10.0, 50.0, threshold)
    assert is_safe is True
    assert msg is None

    # Unsafe: other axis above threshold
    is_safe, msg = check_collision_risk(10.0, 150.0, threshold)
    assert is_safe is False
    assert "Collision risk" in msg

    # Unknown: other axis is None
    is_safe, msg = check_collision_risk(10.0, None, threshold)
    assert is_safe is True
    assert "caution" in msg

def test_bounds_classes():
    """Test Bounds1D and Bounds3D helper classes."""
    b1 = Bounds1D(0, 10)
    assert b1.contains(5)
    assert not b1.contains(11)
    assert b1.clamp(12) == 10

    b3 = Bounds3D(0,1, 0,1, 0,1)
    assert b3.contains(0.5, 0.5, 0.5)
    assert not b3.contains(1.5, 0.5, 0.5)
    assert b3.clamp_position(1.5, -0.5, 0.5) == (1.0, 0.0, 0.5)
