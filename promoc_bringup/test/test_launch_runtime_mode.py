"""Static checks for canonical runtime_mode launch API."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_system_launch_supports_runtime_mode_and_legacy_alias():
    content = (
        ROOT / "promoc_bringup" / "launch" / "system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "runtime_mode" in content
    assert "sim_mode" in content
    assert "Deprecated" in content


def test_camera_launch_supports_runtime_mode_and_legacy_aliases():
    content = (
        ROOT / "promoc_bringup" / "launch" / "camera.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "runtime_mode" in content
    assert "sim_mode" in content
    assert "use_simulator" in content


def test_optical_launch_supports_runtime_mode_and_legacy_aliases():
    content = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "runtime_mode" in content
    assert "sim_mode" in content
    assert "use_simulator" in content
