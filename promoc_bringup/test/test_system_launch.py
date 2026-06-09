"""Smoke checks for main system launch wiring."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_system_launch_file_exists():
    launch_path = ROOT / "promoc_bringup" / "launch" / "system.launch.py"
    assert launch_path.exists()


def test_system_launch_includes_camera_mover_and_axis_namespaces():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "camera.launch.py" in content
    assert "planar_motor_nodes" in content
    assert 'name="mover"' in content
    assert 'namespace="promoc"' in content
    assert 'namespace="promoc/linear_axis"' in content
    assert "runtime_mode" in content
