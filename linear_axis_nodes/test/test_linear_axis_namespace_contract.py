# ruff: noqa: E402
"""Static checks for the unified linear-axis configuration contract."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("linear_axis_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from linear_axis_nodes.config import LinearAxisConfig


EXPECTED_KEYS = {
    "axis_id",
    "driver_mode",
    "serial_number",
    "serial_port",
    "min_position",
    "max_position",
    "default_velocity",
    "default_acceleration",
    "movement_timeout",
    "homing_timeout",
    "state_publish_rate_hz",
}


def _load_axis_yaml(name: str) -> dict:
    path = REPO_ROOT / "linear_axis_nodes" / "config" / name
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    return content["/**"]["ros__parameters"]


def test_axis_yaml_parameter_names_match_python_contract():
    config_fields = set(LinearAxisConfig.__annotations__.keys())
    assert config_fields == EXPECTED_KEYS
    assert set(_load_axis_yaml("x_axis.yaml").keys()) == EXPECTED_KEYS
    assert set(_load_axis_yaml("z_axis.yaml").keys()) == EXPECTED_KEYS


def test_x_and_z_configs_share_one_schema_and_differ_by_axis_values():
    x_cfg = _load_axis_yaml("x_axis.yaml")
    z_cfg = _load_axis_yaml("z_axis.yaml")

    assert x_cfg["axis_id"] == "x"
    assert z_cfg["axis_id"] == "z"
    assert x_cfg["serial_number"] != z_cfg["serial_number"]
    assert x_cfg["driver_mode"] == z_cfg["driver_mode"] == "hardware"


def test_system_launch_uses_package_owned_axis_configs():
    content = (
        REPO_ROOT / "promoc_bringup" / "launch" / "system.launch.py"
    ).read_text(encoding="utf-8")

    assert '("lts300_x_axis", os.path.join(axis_pkg, "config", "x_axis.yaml"))' in content
    assert '("lts300_z_axis", os.path.join(axis_pkg, "config", "z_axis.yaml"))' in content
    assert 'executable="lts300_node"' in content
    assert 'namespace="promoc/linear_axis"' in content
