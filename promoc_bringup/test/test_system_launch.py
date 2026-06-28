"""Smoke checks for main system launch wiring."""

from __future__ import annotations

from pathlib import Path
import re


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


def test_system_launch_uses_driver_mode_and_component_flags():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert re.search(r'DeclareLaunchArgument\(\s*"driver_mode"', content)
    for argument in ("camera", "x_axis", "z_axis", "planar_motor", "system_controller"):
        assert re.search(rf'DeclareLaunchArgument\(\s*"{argument}"', content)
    assert "runtime_mode" not in content


def test_system_controller_is_optional_by_default():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    match = re.search(
        r'DeclareLaunchArgument\(\s*"system_controller".*?\)',
        content,
        flags=re.DOTALL,
    )
    assert match is not None
    system_controller_block = match.group(0)
    assert 'default_value="false"' in system_controller_block
