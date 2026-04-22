"""Smoke tests for autofocus handler wiring."""

from __future__ import annotations

from pathlib import Path
import sys
import types

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if "cv2" not in sys.modules:
    def _fake_resize(image, size, interpolation=None):
        target_width, target_height = size
        if image.ndim == 2:
            shape = (target_height, target_width)
        else:
            shape = (target_height, target_width, image.shape[2])
        return np.zeros(shape, dtype=image.dtype)

    sys.modules["cv2"] = types.SimpleNamespace(
        INTER_AREA=3,
        resize=_fake_resize,
    )

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
from promoc_core.promoc_exceptions import ImageProcessingError  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


class _Logger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, *_args, **_kwargs):
        if _args:
            self.infos.append(str(_args[0]))
        return None

    def warn(self, *_args, **_kwargs):
        if _args:
            self.warnings.append(str(_args[0]))
        return None

    def error(self, *_args, **_kwargs):
        if _args:
            self.errors.append(str(_args[0]))
        return None


class _Node:
    def __init__(self, params: dict):
        self._params = dict(params)
        self._logger = _Logger()
        self.latest_image_msg = None

    def has_parameter(self, name: str) -> bool:
        return name in self._params

    def get_parameter(self, name: str):
        return _Param(self._params[name])

    def get_logger(self):
        return self._logger


class _Request:
    objective_magnification_x = 0.0
    use_beamsplitter = False


class _Response:
    def __init__(self):
        self.success = False
        self.status_message = ""


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

    def _get_latest_image_timestamp_ns(self):
        return int(self.latest_image[1] or 0)

    def _wait_for_new_image(self, last_timestamp, timeout=1.0):
        image, ts = self.latest_image
        return image, ts if ts is not None else last_timestamp + 1

    def _prepare_autofocus_analysis_image(self, image, roi_rect=None):
        return image

    def _camera_image_topic(self):
        return "/promoc/test_camera/stream0/image_raw"


def test_autofocus_handler_builds_focus_profile():
    class _Driver:
        def get_exposure(self):
            return 45000.0

    handler = AutofocusHandler(
        _Node({"autofocus.exposure_guard_s": 0.02}),
        camera_driver=_Driver(),
    )
    profile = handler._build_focus_profile(_Request())

    assert isinstance(profile, dict)
    assert "scan_speed_mm_s" in profile
    assert profile["scan_speed_mm_s"] > 0.0
    assert profile["exposure_time_us"] == 45000.0
    assert profile["settle_s"] >= 0.065


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

    assert plan.mode_name == "fourstep"
    assert plan.algorithm.config.start_mm == 3.0
    assert plan.algorithm.config.end_mm == 5.0
    assert plan.algorithm.config.step_mm == 0.2
    assert plan.settle_s == 0.15
    assert plan.save_best_image is False


def test_handler_algorithm_lookup_matches_public_focus_mode_ids():
    assert autofocus_module._ALGO_LOOKUP[0][0] == "fourstep"
    assert autofocus_module._ALGO_LOOKUP[5][0] == "goldensection"


def test_runner_unknown_mode_falls_back_to_fourstep():
    runner = AutofocusRunner(_RunnerHandler())
    request = types.SimpleNamespace(
        start_position=1.0,
        end_position=9.0,
        save_best_image=False,
    )

    plan = runner._build_single_mode_run_plan(
        mode=999,
        peak_start=3.0,
        peak_end=5.0,
        request=request,
        focus_profile={"coarse_step_mm": 0.2, "settle_s": 0.15},
    )

    assert plan.mode_name == "fourstep"


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
    handler.latest_image = (object(), 5)
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
        settle_s=0.05,
        analysis_roi_rect=None,
    )

    assert best_score == 100.0
    assert best_image is None
    assert move_client.positions == [5.0, 5.5]
    assert handler.wait_calls == 2


def test_runner_confirmation_waits_for_fresh_frame_after_settle(monkeypatch):
    handler = _RunnerHandler()
    handler.latest_image = (object(), 11)
    wait_calls = []

    def _wait_for_new_image(last_timestamp, timeout=1.0):
        wait_calls.append((last_timestamp, timeout))
        return object(), last_timestamp + 1

    handler._wait_for_new_image = _wait_for_new_image
    runner = AutofocusRunner(handler)
    monkeypatch.setattr(autofocus_module.time, "sleep", lambda *_args, **_kwargs: None)

    class _Algorithm:
        def score_image(self, _image):
            return 120.0

    best_score, _best_image = runner._confirm_measurement_position(
        "fourstep",
        _Algorithm(),
        target_pos=5.5,
        best_position=5.5,
        best_score=100.0,
        best_image=None,
        request=types.SimpleNamespace(start_position=2.0, end_position=6.0),
        clients={"move": _MoveClient()},
        save_best_image=False,
        settle_s=0.04,
        analysis_roi_rect=None,
    )

    assert best_score == 120.0
    assert wait_calls == [(11, autofocus_module.AUTOFOCUS_NEW_IMAGE_TIMEOUT_S)]


def test_fill_single_mode_response_uses_student_friendly_status():
    response = types.SimpleNamespace(
        success=False,
        status_message="",
        best_focus_position=0.0,
        best_focus_value=0.0,
        total_measurements_taken=0,
        duration_seconds=0.0,
        best_image_path="",
        measurement_positions=[],
        measurement_scores=[],
    )

    result = autofocus_module.fill_single_mode_response(
        response,
        mode_name="fourstep",
        best_position=12.345,
        best_score=987.0,
        measurements=7,
        duration_s=1.5,
        measurement_positions=[12.0, 12.3],
        measurement_scores=[500.0, 987.0],
        best_image_path="C:/tmp/best.jpg",
    )

    assert result.success is True
    assert "Autofocus complete" in result.status_message
    assert "best_pos=12.345mm" in result.status_message
    assert "measurements=7" in result.status_message
    assert "image=C:/tmp/best.jpg" in result.status_message


def test_wait_for_next_autofocus_frame_reports_operator_hint():
    handler = _RunnerHandler()
    handler._wait_for_new_image = lambda *_args, **_kwargs: (None, None)
    runner = AutofocusRunner(handler)

    try:
        runner._wait_for_next_autofocus_frame(0)
    except ImageProcessingError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected ImageProcessingError for stalled camera stream")

    assert "camera stream stalled" in message.lower()
    assert "rqt_image_view" in message


def test_prepare_autofocus_analysis_image_center_crop_and_downsample():
    handler = AutofocusHandler(
        _Node(
            {
                "autofocus.analysis_roi_width_px": 2000,
                "autofocus.analysis_roi_height_px": 2000,
                "autofocus.analysis_downsample_max_dim_px": 1024,
                "autofocus.analysis_use_center_roi": True,
                "autofocus.analysis_log_effective_roi": True,
            }
        ),
        camera_driver=object(),
    )
    handler._reset_analysis_logging()
    image = np.zeros((3000, 4000, 3), dtype=np.uint8)

    processed = handler._prepare_autofocus_analysis_image(image)

    assert processed.shape == (1024, 1024, 3)
    assert any("effective_roi=(1000,500,2000,2000)" in msg for msg in handler._node._logger.infos)


def test_prepare_autofocus_analysis_image_clamps_small_source_image():
    handler = AutofocusHandler(
        _Node(
            {
                "autofocus.analysis_roi_width_px": 2000,
                "autofocus.analysis_roi_height_px": 2000,
                "autofocus.analysis_downsample_max_dim_px": 1024,
                "autofocus.analysis_use_center_roi": True,
                "autofocus.analysis_log_effective_roi": True,
            }
        ),
        camera_driver=object(),
    )
    handler._reset_analysis_logging()
    image = np.zeros((800, 1200, 3), dtype=np.uint8)

    processed = handler._prepare_autofocus_analysis_image(image)

    assert processed.shape == (683, 1024, 3)
    assert any("effective_roi=(0,0,1200,800)" in msg for msg in handler._node._logger.infos)


def test_run_autofocus_loop_scores_preprocessed_analysis_image():
    handler = _RunnerHandler(
        {
            "autofocus.analysis_roi_width_px": 2000,
            "autofocus.analysis_roi_height_px": 2000,
            "autofocus.analysis_downsample_max_dim_px": 1024,
            "autofocus.analysis_use_center_roi": True,
        }
    )
    real_handler = AutofocusHandler(handler._node, camera_driver=object())
    handler._prepare_autofocus_analysis_image = real_handler._prepare_autofocus_analysis_image
    handler._wait_for_new_image = (
        lambda *_args, **_kwargs: (np.zeros((3000, 4000, 3), dtype=np.uint8), 1)
    )
    runner = AutofocusRunner(handler)

    class _Algorithm:
        def __init__(self):
            self.config = types.SimpleNamespace(start_mm=0.0, end_mm=1.0)
            self.seen_shape = None

        def start(self):
            return 0.0

        def get_scan_step_mm(self):
            return 1.0

        def process_image(self, _position_mm, image):
            self.seen_shape = image.shape
            return types.SimpleNamespace(
                finished=True,
                best_position_mm=0.0,
                best_score=123.0,
                current_score=123.0,
                phase=types.SimpleNamespace(name="FINISHED"),
                next_position_mm=None,
            )

        def get_best_result(self):
            return 0.0, 123.0

    algorithm = _Algorithm()
    best_position, best_score, measurements = runner.run_autofocus_loop(
        algorithm,
        clients={"move": _MoveClient()},
        settle_s=0.0,
    )

    assert algorithm.seen_shape == (1024, 1024, 3)
    assert best_position == 0.0
    assert best_score == 123.0
    assert measurements == 1


def test_autofocus_roi_callback_uses_requested_roi_rect():
    handler = AutofocusHandler(
        _Node({"camera.expected_width": 4000, "camera.expected_height": 3000}),
        camera_driver=object(),
    )
    captured = {}

    def _fake_run(request, response, analysis_roi_rect):
        captured["roi"] = analysis_roi_rect
        response.success = True
        return response

    handler._run_autofocus_request = _fake_run
    request = types.SimpleNamespace(
        roi_x=100,
        roi_y=150,
        roi_width=800,
        roi_height=600,
    )

    response = handler.autofocus_roi_callback(request, _Response())

    assert response.success is True
    assert captured["roi"] == (100, 150, 800, 600)


def test_autofocus_roi_callback_rejects_fully_outside_roi():
    handler = AutofocusHandler(
        _Node({"camera.expected_width": 4000, "camera.expected_height": 3000}),
        camera_driver=object(),
    )
    request = types.SimpleNamespace(
        roi_x=5000,
        roi_y=3500,
        roi_width=200,
        roi_height=200,
    )

    response = handler.autofocus_roi_callback(request, _Response())

    assert response.success is False
    assert "outside the current image" in response.status_message
