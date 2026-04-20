"""Static smoke checks for the minimal messstand launch path."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

def test_optical_launch_has_no_verification_node():
    content = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "scientific_verification" not in content
    assert "package='verification'" not in content
    assert "runtime_mode" in content
    assert "/promoc/camera/autofocus" in content
    assert "/promoc/camera/measure_mtf" in content
    assert "/promoc/camera/set_exposure" in content
