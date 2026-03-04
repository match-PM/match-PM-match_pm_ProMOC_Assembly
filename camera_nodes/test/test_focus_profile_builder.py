"""Unit tests for FocusProfileBuilder."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camera_nodes.helpers.focus_profile import FocusProfileBuilder  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


class _Logger:
    def __init__(self):
        self.warnings = []

    def info(self, *_args, **_kwargs):
        return None

    def warn(self, msg, *_args, **_kwargs):
        self.warnings.append(str(msg))


class _Node:
    def __init__(self, params: dict):
        self._params = dict(params)
        self._logger = _Logger()

    def has_parameter(self, name: str) -> bool:
        return name in self._params

    def get_parameter(self, name: str):
        return _Param(self._params[name])

    def get_logger(self):
        return self._logger


class _Request:
    objective_magnification_x = 0.0
    use_beamsplitter = False


def test_focus_profile_builder_parses_objective_and_high_mag_defaults():
    params = {
        "measurement_conditions.camera_objective": "6x objective",
        "autofocus.fly_over.scan_speed_fast": 10.0,
        "autofocus.fly_over.step_size_coarse": 0.5,
        "autofocus.min_step_mm": 0.01,
        "autofocus.fly_over.settle_fine_s": 0.1,
        "autofocus.fly_over.max_sample_step_mm": 0.1,
        "autofocus.fly_over.axis_speed_scale_default": 1.0,
        "autofocus.fly_over.high_mag_threshold_x": 4.0,
        "autofocus.fly_over.very_high_mag_threshold_x": 6.0,
        "autofocus.fly_over.scan_speed_high_mag": 2.0,
        "autofocus.fly_over.scan_speed_very_high_mag": 1.0,
        "autofocus.fly_over.coarse_step_high_mag_mm": 0.1,
        "autofocus.fly_over.coarse_step_very_high_mag_mm": 0.05,
        "autofocus.fly_over.min_step_high_mag_mm": 0.005,
        "autofocus.fly_over.settle_high_mag_s": 0.2,
        "autofocus.fly_over.settle_very_high_mag_s": 0.25,
        "autofocus.profile_table_json": "",
    }
    profile = FocusProfileBuilder(_Node(params)).build(_Request())

    assert profile.magnification_x == 6.0
    assert profile.scan_speed_mm_s == 1.0
    assert profile.coarse_step_mm == 0.05
    assert profile.min_step_mm == 0.005
    assert profile.settle_s == 0.25


def test_focus_profile_builder_json_override_precedence_combo_wins():
    table = {
        "default": {"scan_speed_mm_s": 8.0},
        "profiles": {
            "6x": {"scan_speed_mm_s": 6.0},
            "bs1": {"scan_speed_mm_s": 4.0},
            "6x_bs1": {"scan_speed_mm_s": 2.5, "coarse_step_mm": 0.02},
        },
    }
    params = {
        "measurement_conditions.camera_objective": "6x",
        "autofocus.fly_over.scan_speed_fast": 10.0,
        "autofocus.fly_over.step_size_coarse": 0.5,
        "autofocus.min_step_mm": 0.01,
        "autofocus.fly_over.settle_fine_s": 0.1,
        "autofocus.fly_over.max_sample_step_mm": 0.1,
        "autofocus.fly_over.axis_speed_scale_default": 1.0,
        "autofocus.fly_over.high_mag_threshold_x": 99.0,
        "autofocus.fly_over.very_high_mag_threshold_x": 999.0,
        "autofocus.fly_over.scan_speed_high_mag": 2.0,
        "autofocus.fly_over.scan_speed_very_high_mag": 1.0,
        "autofocus.fly_over.coarse_step_high_mag_mm": 0.1,
        "autofocus.fly_over.coarse_step_very_high_mag_mm": 0.05,
        "autofocus.fly_over.min_step_high_mag_mm": 0.005,
        "autofocus.fly_over.settle_high_mag_s": 0.2,
        "autofocus.fly_over.settle_very_high_mag_s": 0.25,
        "autofocus.profile_table_json": json.dumps(table),
    }
    request = _Request()
    request.use_beamsplitter = True
    profile = FocusProfileBuilder(_Node(params)).build(request)

    assert profile.profile_source == "6x_bs1"
    assert profile.scan_speed_mm_s == 2.5
    assert profile.coarse_step_mm == 0.02
