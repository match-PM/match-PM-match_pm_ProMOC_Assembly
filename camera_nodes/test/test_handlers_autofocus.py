"""Smoke tests for autofocus handler wiring."""

from __future__ import annotations

from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace()

srv_mod = types.ModuleType("promoc_assembly_interfaces.srv")


class _SrvType:
    class Request:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


for srv_name in (
    "GetOperationStatus",
    "GetPosition",
    "GetVelocityParameters",
    "SetVelocityParameters",
    "JogAxis",
    "MoveAbsolute",
    "Stop",
):
    setattr(srv_mod, srv_name, _SrvType)

sys.modules["promoc_assembly_interfaces.srv"] = srv_mod
if "promoc_assembly_interfaces" not in sys.modules:
    pkg_mod = types.ModuleType("promoc_assembly_interfaces")
    pkg_mod.srv = srv_mod
    sys.modules["promoc_assembly_interfaces"] = pkg_mod

import camera_nodes.services.autofocus as autofocus_module  # noqa: E402
from camera_nodes.services.autofocus import AutofocusHandler, AutofocusRunner  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


class _Logger:
    def info(self, *_args, **_kwargs):
        return None

    def warn(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


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


class _MoveClient:
    def __init__(self):
        self.positions = []

    def call(self, request):
        self.positions.append(float(request.axis_position))
        return None


class _RunnerHandler:
    def __init__(self, params: dict | None = None):
        self._node = _Node(params or {})
        self.wait_calls = 0
        self.latest_image = (None, None)

    def _param_int(self, name: str, default: int) -> int:
        return int(self._node._params.get(name, default))

    def _param_float(self, name: str, default: float) -> float:
        return float(self._node._params.get(name, default))

    def _param_bool(self, name: str, default: bool = False) -> bool:
        return bool(self._node._params.get(name, default))

    def _wait_for_axis_idle(self, _clients) -> None:
        self.wait_calls += 1

    def _get_latest_cv_image(self):
        return self.latest_image


def test_autofocus_handler_builds_focus_profile():
    handler = AutofocusHandler(_Node({}), camera_driver=object())
    profile = handler._build_focus_profile(_Request())

    assert isinstance(profile, dict)
    assert "scan_speed_mm_s" in profile
    assert profile["scan_speed_mm_s"] > 0.0


def test_runner_build_plan_uses_request_range_for_exhaustive_mode():
    handler = _RunnerHandler(
        {
            "autofocus.refinement_samples": 61,
            "autofocus.refinement_shrink_factor": 0.4,
            "autofocus.min_step_mm": 0.02,
            "autofocus.fly_over.use_sift_weighting": True,
        }
    )
    runner = AutofocusRunner(handler)
    request = types.SimpleNamespace(
        start_position=1.0,
        end_position=9.0,
        save_best_image=True,
    )

    plan = runner._build_single_mode_run_plan(
        mode=4,
        peak_start=3.0,
        peak_end=5.0,
        request=request,
        focus_profile={"coarse_step_mm": 0.25, "min_step_mm": 0.03, "settle_s": 0.4},
    )

    assert plan.mode_name == "exhaustive"
    assert plan.algorithm.config.start_mm == 1.0
    assert plan.algorithm.config.end_mm == 9.0
    assert plan.algorithm.config.step_mm == 0.25
    assert plan.algorithm.config.min_step_mm == 0.03
    assert plan.algorithm.config.refinement_samples == 61
    assert plan.algorithm.config.shrink_factor == 0.4
    assert plan.algorithm.config.use_sift_weighting is True
    assert plan.settle_s == 0.4
    assert plan.save_best_image is True


def test_runner_build_plan_uses_peak_window_for_refinement_mode():
    runner = AutofocusRunner(_RunnerHandler())
    request = types.SimpleNamespace(
        start_position=1.0,
        end_position=9.0,
        save_best_image=False,
    )

    plan = runner._build_single_mode_run_plan(
        mode=0,
        peak_start=3.0,
        peak_end=5.0,
        request=request,
        focus_profile={"coarse_step_mm": 0.2, "settle_s": 0.15},
    )

    assert plan.mode_name == "goldensection"
    assert plan.algorithm.config.start_mm == 3.0
    assert plan.algorithm.config.end_mm == 5.0
    assert plan.algorithm.config.step_mm == 0.2
    assert plan.settle_s == 0.15
    assert plan.save_best_image is False


def test_runner_moves_fourstep_via_pre_approach_position():
    handler = _RunnerHandler()
    runner = AutofocusRunner(handler)
    move_client = _MoveClient()
    request = types.SimpleNamespace(start_position=2.0, end_position=6.0)

    target_pos = runner._move_to_measurement_position(
        "fourstep",
        5.5,
        request,
        {"move": move_client},
    )

    assert target_pos == 5.5
    assert move_client.positions == [5.0, 5.5]
    assert handler.wait_calls == 2


def test_runner_retries_fourstep_peak_when_confirmation_score_drops(monkeypatch):
    handler = _RunnerHandler()
    handler.latest_image = (object(), None)
    runner = AutofocusRunner(handler)
    move_client = _MoveClient()
    request = types.SimpleNamespace(start_position=2.0, end_position=6.0)

    class _Algorithm:
        def score_image(self, _image):
            return 80.0

    monkeypatch.setattr(autofocus_module.time, "sleep", lambda *_args, **_kwargs: None)

    best_score, best_image = runner._confirm_measurement_position(
        "fourstep",
        _Algorithm(),
        target_pos=5.5,
        best_position=5.5,
        best_score=100.0,
        best_image=None,
        request=request,
        clients={"move": move_client},
        save_best_image=False,
    )

    assert best_score == 100.0
    assert best_image is None
    assert move_client.positions == [5.0, 5.5]
    assert handler.wait_calls == 2
