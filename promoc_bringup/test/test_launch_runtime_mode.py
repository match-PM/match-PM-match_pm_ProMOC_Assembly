"""Static checks for canonical runtime_mode launch API."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _declares_launch_argument(content: str, arg_name: str) -> bool:
    pattern = rf"DeclareLaunchArgument\(\s*\"{re.escape(arg_name)}\""
    return re.search(pattern, content) is not None


def test_system_launch_is_runtime_mode_only():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "runtime_mode" in content
    assert not _declares_launch_argument(content, "sim_mode")


def test_camera_launch_is_runtime_mode_only():
    content = (ROOT / "promoc_bringup" / "launch" / "camera.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "runtime_mode" in content
    assert not _declares_launch_argument(content, "sim_mode")
    assert not _declares_launch_argument(content, "use_simulator")
    assert 'runtime_mode == "sim"' not in content
    assert "camera_simulator" not in content


def test_optical_launch_is_runtime_mode_only():
    content = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "runtime_mode" in content
    assert not _declares_launch_argument(content, "sim_mode")
    assert not _declares_launch_argument(content, "use_simulator")
    assert "x_axis_name" not in content
    assert "x_axis_port" not in content


def test_camera_launch_uses_dedicated_parameter_builder():
    content = (ROOT / "promoc_bringup" / "launch" / "camera.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "from promoc_bringup.camera_launch_builder import" in content
    assert "build_camera_node_parameters" in content
    assert "build_driver_node_parameters" in content


def test_runtime_mode_compatibility_is_hardware_only():
    content = (
        ROOT / "promoc_bringup" / "promoc_bringup" / "launch_utils.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "runtime_mode='sim' is no longer supported" in content
