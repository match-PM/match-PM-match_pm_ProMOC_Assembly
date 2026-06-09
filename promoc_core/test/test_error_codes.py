"""Tests for shared ProMOC error code definitions."""

from promoc_core import error_codes


def test_error_code_ranges_are_grouped() -> None:
    assert 1000 <= error_codes.CONNECTION_FAILED < 1100
    assert 1100 <= error_codes.INVALID_CONFIGURATION < 1200
    assert 1200 <= error_codes.DEVICE_NOT_READY < 1300
    assert 1300 <= error_codes.MOVEMENT_FAILED < 1400
    assert 1400 <= error_codes.SOFT_LIMIT_REACHED < 1500
    assert 1500 <= error_codes.SYSTEM_STOP_ACTIVE < 1600
    assert 1600 <= error_codes.STOP_REQUESTED < 1700


def test_success_and_unknown_error_codes_are_reserved() -> None:
    assert error_codes.SUCCESS == 0
    assert error_codes.UNKNOWN_ERROR == 9999
