"""Static smoke checks for hardware-first launch configuration."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_system_launch_defaults_to_hardware_mode():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "DeclareLaunchArgument(" in content
    assert '"runtime_mode"' in content
    assert "hardware" in content
    assert '"sim_mode"' not in content


def test_optical_launch_has_no_verification_node():
    content = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "scientific_verification" not in content
    assert "package='verification'" not in content
    assert "runtime_mode" in content
