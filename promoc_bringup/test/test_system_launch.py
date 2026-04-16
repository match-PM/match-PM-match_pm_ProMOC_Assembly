"""Smoke checks for main system launch wiring."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_system_launch_file_exists():
    launch_path = ROOT / "promoc_bringup" / "launch" / "system.launch.py"
    assert launch_path.exists()


def test_system_launch_includes_camera_and_axes_only():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "camera.launch.py" in content
    assert "linear_axis_nodes" in content
    assert "lts300_x_axis" in content
    assert "lts300_z_axis" not in content
    assert "planar_motor_nodes" not in content
    assert "mover_node" not in content
    assert "runtime_mode" in content
