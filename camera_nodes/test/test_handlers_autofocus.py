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

def _fake_resize(image, size, interpolation=None):
    target_width, target_height = size
    if image.ndim == 2:
        shape = (target_height, target_width)
    else:
        shape = (target_height, target_width, image.shape[2])
    return np.zeros(shape, dtype=image.dtype)


def _fake_cvt_color(image, code):
    if image.ndim == 2:
        return np.repeat(image[:, :, None], 3, axis=2)
    return image


if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace()
cv2_stub = sys.modules["cv2"]
if not hasattr(cv2_stub, "INTER_AREA"):
    cv2_stub.INTER_AREA = 3
if not hasattr(cv2_stub, "COLOR_GRAY2BGR"):
    cv2_stub.COLOR_GRAY2BGR = 8
if not hasattr(cv2_stub, "resize"):
    cv2_stub.resize = _fake_resize
if not hasattr(cv2_stub, "cvtColor"):
    cv2_stub.cvtColor = _fake_cvt_color

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
from camera_nodes.algorithms.autofocus import AutofocusConfig, _Measurement  # noqa: E402
from camera_nodes.algorithms.autofocus_strategies.four_step import FourStepAutofocus  # noqa: E402
from camera_nodes.services.autofocus import AutofocusHandler, AutofocusRunner  # noqa: E402
from camera_nodes.services.fly_over import FlyOverDetector  # noqa: E402
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
        self.cb_group = object()
        self.created_clients = []

    def has_parameter(self, name: str) -> bool:
        return name in self._params

    def get_parameter(self, name: str):
        return _Param(self._params[name])

    def get_logger(self):
        return self._logger

    def create_client(self, srv_type, service_name, **kwargs):
        client = types.SimpleNamespace(
            srv_type=srv_type,
            service_name=service_name,
            kwargs=dict(kwargs),
            wait_for_service=lambda timeout_sec=0.0: True,
        )
        self.created_clients.append(client)
        return client


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


class _PositionClient:
    def __init__(self, positions):
        self._positions = list(positions)
        self.calls = 0

    def call(self, _request):
        index = min(self.calls, len(self._positions) - 1)
        value = float(self._positions[index])
        self.calls += 1
        return types.SimpleNamespace(success=True, axis_position=value)


class _StatusClient:
    def __init__(self, statuses):
        self._statuses = list(statuses)
        self.calls = 0

    def call(self, _request):
        index = min(self.calls, len(self._statuses) - 1)
        value = str(self._statuses[index])
        self.calls += 1
        return types.SimpleNamespace(
            success=True,
            operation_status=value,
            status_message=value,
        )


class _RunnerHandler:
    def __init__(self, params: dict | None = None):
        self._node = _Node(params or {})
        self.wait_calls = 0
        self.latest_image = (None, None)
        self.latest_passthrough_image = (None, None, "")

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

    def _get_latest_passthrough_image(self):
        return self.latest_passthrough_image

    def _get_latest_image_timestamp_ns(self):
        return int(self.latest_image[1] or 0)

    def _wait_for_new_image(self, last_timestamp, timeout=1.0):
        image, ts = self.latest_image
        return image, ts if ts is not None else last_timestamp + 1

    def _wait_for_new_passthrough_image(self, last_timestamp, timeout=1.0):
        image, ts, encoding = self.latest_passthrough_image
        resolved_ts = ts if ts is not None else last_timestamp + 1
        return image, resolved_ts, encoding

    def _prepare_autofocus_analysis_image(self, image, roi_rect=None, encoding=""):
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


def test_flyover_detector_rejects_peak_windows_outside_scan_range():
    node = _Node({})
    detector = FlyOverDetector(
        node=node,
        get_latest_cv_image=lambda: (None, None),
        get_center_roi=lambda *_args, **_kwargs: np.zeros((1, 1), dtype=np.uint8),
        wait_for_axis_idle=lambda _clients: None,
        get_position=lambda _clients: -1.0,
    )

    result = detector._analyze_peak(
        scan_data=[(15.0, 16.17), (15.2, 12.0), (15.4, 8.0)],
        start_pos=285.0,
        end_pos=288.0,
        peak_ratio=0.9,
        margin=1.0,
        backtrack=2.0,
        guard=1.5,
        min_window_width=6.0,
        threshold=0.0,
    )

    assert result.peak_start is None
    assert result.peak_end is None
    assert any(
        "outside the requested scan range" in msg
        for msg in node._logger.warnings
    )


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


def test_fourstep_parabolic_peak_does_not_replace_measured_best_position():
    algorithm = FourStepAutofocus(AutofocusConfig(start_mm=0.0, end_mm=1.0))
    measurements = [
        _Measurement(0.00, 90.0),
        _Measurement(0.01, 100.0),
        _Measurement(0.02, 95.0),
    ]
    algorithm._measurements = measurements
    algorithm._best_measurement = measurements[1]
    algorithm.ultra_start_index = 0
    algorithm.scan_points = [0.00, 0.01, 0.02]

    algorithm._apply_parabolic_refinement()

    best_position, best_score = algorithm.get_best_result()
    assert algorithm.parabolic_peak_mm is not None
    assert algorithm.parabolic_peak_mm != 0.01
    assert best_position == 0.01
    assert best_score == 100.0


def test_runner_uses_fourstep_parabolic_peak_as_final_measurement_candidate():
    handler = _RunnerHandler()
    runner = AutofocusRunner(handler)
    algorithm = types.SimpleNamespace(parabolic_peak_mm=5.55)
    request = types.SimpleNamespace(start_position=2.0, end_position=6.0)

    target = runner._resolve_final_measurement_target(
        "fourstep",
        algorithm,
        best_position=5.5,
        request=request,
    )

    assert target == 5.55


def test_runner_returns_to_measured_fourstep_best_when_peak_confirmation_score_drops(monkeypatch):
    handler = _RunnerHandler()
    handler.latest_image = (object(), 5)
    runner = AutofocusRunner(handler)
    move_client = _MoveClient()
    request = types.SimpleNamespace(start_position=2.0, end_position=6.0)

    class _Algorithm:
        def score_image(self, _image):
            return 80.0

    monkeypatch.setattr(autofocus_module.time, "sleep", lambda *_args, **_kwargs: None)

    best_position, best_score, best_image = runner._confirm_measurement_position(
        "fourstep",
        _Algorithm(),
        target_pos=5.55,
        best_position=5.5,
        best_score=100.0,
        best_image=None,
        request=request,
        clients={"move": move_client},
        save_best_image=False,
        settle_s=0.05,
        analysis_roi_rect=None,
    )

    assert best_position == 5.5
    assert best_score == 100.0
    assert best_image is None
    assert move_client.positions == [5.0, 5.5]
    assert handler.wait_calls == 2


def test_runner_accepts_fourstep_peak_when_confirmation_score_improves(monkeypatch):
    handler = _RunnerHandler()
    handler.latest_image = (object(), 5)
    runner = AutofocusRunner(handler)
    move_client = _MoveClient()
    request = types.SimpleNamespace(start_position=2.0, end_position=6.0)

    class _Algorithm:
        def score_image(self, _image):
            return 120.0

    monkeypatch.setattr(autofocus_module.time, "sleep", lambda *_args, **_kwargs: None)

    best_position, best_score, best_image = runner._confirm_measurement_position(
        "fourstep",
        _Algorithm(),
        target_pos=5.55,
        best_position=5.5,
        best_score=100.0,
        best_image=None,
        request=request,
        clients={"move": move_client},
        save_best_image=False,
        settle_s=0.05,
        analysis_roi_rect=None,
    )

    assert best_position == 5.55
    assert best_score == 120.0
    assert best_image is None
    assert move_client.positions == []
    assert handler.wait_calls == 0


def test_axis_client_wait_for_target_bypasses_stale_cached_position(monkeypatch):
    handler = _RunnerHandler()
    handler._node.current_axis_position = 0.0
    axis_clients = autofocus_module.AxisClientManager(handler)
    position_client = _PositionClient([9.7, 10.0, 10.0, 10.0])
    sleep_calls = []

    monkeypatch.setattr(autofocus_module.time, "sleep", lambda *_args, **_kwargs: sleep_calls.append(1))

    reached = axis_clients.wait_for_axis_target(
        {"position": position_client},
        10.0,
        tolerance_mm=0.05,
        timeout_s=1.0,
    )

    assert reached == 10.0
    assert position_client.calls >= 4
    assert sleep_calls


def test_axis_clients_use_camera_node_reentrant_callback_group():
    handler = _RunnerHandler()
    axis_clients = autofocus_module.AxisClientManager(handler)

    clients = axis_clients.get_all_axis_clients()

    assert set(clients) == {
        "move",
        "jog",
        "status",
        "position",
        "stop",
        "get_vel",
        "set_vel",
    }
    assert handler._node.created_clients
    assert all(
        entry.kwargs.get("callback_group") is handler._node.cb_group
        for entry in handler._node.created_clients
    )


def test_axis_client_wait_for_target_requires_idle_before_accepting_exact_position(monkeypatch):
    handler = _RunnerHandler()
    axis_clients = autofocus_module.AxisClientManager(handler)
    position_client = _PositionClient([10.0, 10.0, 10.0, 10.0, 10.0])
    status_client = _StatusClient(["moving", "moving", "idle", "idle", "idle"])
    sleep_calls = []

    monkeypatch.setattr(
        autofocus_module.time,
        "sleep",
        lambda *_args, **_kwargs: sleep_calls.append(1),
    )

    reached = axis_clients.wait_for_axis_target(
        {"position": position_client, "status": status_client},
        10.0,
        tolerance_mm=0.05,
        timeout_s=1.0,
    )

    assert reached == 10.0
    assert status_client.calls >= 5
    assert sleep_calls


def test_axis_client_wait_for_target_falls_back_to_idle_when_position_stalls(monkeypatch):
    handler = _RunnerHandler()
    axis_clients = autofocus_module.AxisClientManager(handler)
    position_client = _PositionClient([9.2, 9.2, 9.2])
    status_client = _StatusClient(["moving", "idle"])

    monkeypatch.setattr(autofocus_module.time, "sleep", lambda *_args, **_kwargs: None)

    reached = axis_clients.wait_for_axis_target(
        {"position": position_client, "status": status_client},
        10.0,
        tolerance_mm=0.05,
        timeout_s=1.0,
    )

    assert reached == 9.2
    assert status_client.calls >= 2
    assert any(
        "idle before exact target confirmation" in msg
        for msg in handler._node._logger.warnings
    )


def test_move_axis_continues_when_move_service_response_times_out():
    handler = _RunnerHandler()
    handler._axis_clients = types.SimpleNamespace(
        _call_service_with_timeout=lambda *_args, **_kwargs: None
    )
    target_waits = []
    handler._wait_for_axis_target = (
        lambda _clients, target_pos: target_waits.append(float(target_pos)) or float(target_pos)
    )
    runner = AutofocusRunner(handler)

    class _MoveClientNeverAck:
        def __init__(self):
            self.calls = 0

        def call(self, _request):
            raise AssertionError("synchronous move.call should not be used here")

    move_client = _MoveClientNeverAck()
    runner._move_axis({"move": move_client}, 5.0)

    assert target_waits == [5.0]
    assert any("AF move: response timeout" in msg for msg in handler._node._logger.warnings)


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

    best_position, best_score, _best_image = runner._confirm_measurement_position(
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

    assert best_position == 5.5
    assert best_score == 120.0
    assert wait_calls == [
        (
            11,
            min(
                autofocus_module.AUTOFOCUS_NEW_IMAGE_TIMEOUT_S,
                max(0.05, autofocus_module.AUTOFOCUS_FRESH_FRAME_WAIT_S),
            ),
        )
    ]


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
    handler._wait_for_new_passthrough_image = lambda *_args, **_kwargs: (None, None, "")
    handler._wait_for_new_image = lambda *_args, **_kwargs: (None, None)
    handler._get_latest_passthrough_image = lambda: (None, None, "")
    handler._get_latest_cv_image = lambda: (None, None)
    runner = AutofocusRunner(handler)

    try:
        runner._wait_for_next_autofocus_frame(0)
    except ImageProcessingError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected ImageProcessingError for stalled camera stream")

    assert "no usable camera frame available" in message.lower()
    assert "rqt_image_view" in message


def test_wait_for_next_autofocus_frame_reuses_latest_cached_frame_when_timestamp_stalls():
    handler = _RunnerHandler()
    handler.latest_passthrough_image = (
        np.zeros((3000, 4000), dtype=np.uint16),
        11,
        "bayer_rggb16",
    )
    handler._wait_for_new_passthrough_image = lambda *_args, **_kwargs: (None, None, "")
    handler._wait_for_new_image = lambda *_args, **_kwargs: (None, None)
    real_handler = AutofocusHandler(handler._node, camera_driver=object())
    handler._prepare_autofocus_analysis_image = real_handler._prepare_autofocus_analysis_image
    runner = AutofocusRunner(handler)

    frame = runner._wait_for_next_autofocus_frame(11)

    assert frame.analysis_image.shape == (2048, 2048, 3)
    assert frame.timestamp_ns == 11


def test_prepare_autofocus_analysis_image_center_crop_and_downsample():
    handler = AutofocusHandler(
        _Node(
            {
                "autofocus.analysis_roi_width_px": 2048,
                "autofocus.analysis_roi_height_px": 2048,
                "autofocus.analysis_downsample_max_dim_px": 2048,
                "autofocus.analysis_use_center_roi": True,
                "autofocus.analysis_log_effective_roi": True,
            }
        ),
        camera_driver=object(),
    )
    handler._reset_analysis_logging()
    image = np.zeros((3000, 4000, 3), dtype=np.uint8)

    processed = handler._prepare_autofocus_analysis_image(image)

    assert processed.shape == (2048, 2048, 3)
    assert any("effective_roi=(976,476,2048,2048)" in msg for msg in handler._node._logger.infos)


def test_prepare_autofocus_analysis_image_uses_configured_roi_origin():
    handler = AutofocusHandler(
        _Node(
            {
                "autofocus.analysis_roi_x_px": 1979,
                "autofocus.analysis_roi_y_px": 1010,
                "autofocus.analysis_roi_width_px": 1689,
                "autofocus.analysis_roi_height_px": 1624,
                "autofocus.analysis_downsample_max_dim_px": 2048,
                "autofocus.analysis_use_center_roi": True,
                "autofocus.analysis_log_effective_roi": True,
            }
        ),
        camera_driver=object(),
    )
    handler._reset_analysis_logging()
    image = np.zeros((3692, 5536, 3), dtype=np.uint8)

    processed = handler._prepare_autofocus_analysis_image(image)

    assert processed.shape == (1624, 1689, 3)
    assert any(
        "requested_roi=(1979,1010,1689,1624)" in msg
        and "effective_roi=(1979,1010,1689,1624)" in msg
        for msg in handler._node._logger.infos
    )


def test_prepare_autofocus_analysis_image_clamps_small_source_image():
    handler = AutofocusHandler(
        _Node(
            {
                "autofocus.analysis_roi_width_px": 2048,
                "autofocus.analysis_roi_height_px": 2048,
                "autofocus.analysis_downsample_max_dim_px": 2048,
                "autofocus.analysis_use_center_roi": True,
                "autofocus.analysis_log_effective_roi": True,
            }
        ),
        camera_driver=object(),
    )
    handler._reset_analysis_logging()
    image = np.zeros((800, 1200, 3), dtype=np.uint8)

    processed = handler._prepare_autofocus_analysis_image(image)

    assert processed.shape == (800, 1200, 3)
    assert any("effective_roi=(0,0,1200,800)" in msg for msg in handler._node._logger.infos)


def test_measure_tenengrad_roi_uses_same_analysis_path_without_axis_motion():
    node = _Node(
        {
            "camera.expected_width": 30,
            "camera.expected_height": 20,
            "autofocus.analysis_downsample_max_dim_px": 2048,
            "autofocus.analysis_log_effective_roi": False,
        }
    )
    handler = AutofocusHandler(node, camera_driver=object())
    image = np.arange(20 * 30, dtype=np.uint16).reshape(20, 30)
    handler._get_latest_passthrough_image = lambda: (image, 123456789, "mono16")
    captured = {}

    def _score(analysis_image):
        captured["analysis_image"] = analysis_image.copy()
        return 42.0

    handler._calculate_sharpness = _score

    request = types.SimpleNamespace(
        roi_x=5,
        roi_y=4,
        roi_width=10,
        roi_height=8,
    )
    response = types.SimpleNamespace(
        success=False,
        status_message="",
        tenengrad_value=0.0,
        roi_x=0,
        roi_y=0,
        roi_width=0,
        roi_height=0,
        analysis_width=0,
        analysis_height=0,
        image_timestamp_ns=0,
        image_encoding="",
    )

    result = handler.measure_tenengrad_roi_callback(request, response)

    assert result.success is True
    assert result.tenengrad_value == 42.0
    assert np.array_equal(captured["analysis_image"], image[4:12, 5:15])
    assert (result.roi_x, result.roi_y, result.roi_width, result.roi_height) == (
        5,
        4,
        10,
        8,
    )
    assert (result.analysis_width, result.analysis_height) == (10, 8)
    assert result.image_timestamp_ns == 123456789
    assert result.image_encoding == "mono16"
    assert not node.created_clients


def test_measure_tenengrad_roi_reports_missing_live_frame():
    handler = AutofocusHandler(
        _Node({"camera.expected_width": 30, "camera.expected_height": 20}),
        camera_driver=object(),
    )
    handler._get_latest_passthrough_image = lambda: (None, None, "")
    handler._get_latest_cv_image = lambda: (None, None)
    request = types.SimpleNamespace(
        roi_x=1,
        roi_y=1,
        roi_width=10,
        roi_height=8,
    )
    response = types.SimpleNamespace(success=False, status_message="")

    result = handler.measure_tenengrad_roi_callback(request, response)

    assert result.success is False
    assert "live camera frame" in result.status_message


def test_run_autofocus_loop_scores_preprocessed_analysis_image():
    handler = _RunnerHandler(
        {
            "autofocus.analysis_roi_width_px": 2048,
            "autofocus.analysis_roi_height_px": 2048,
            "autofocus.analysis_downsample_max_dim_px": 2048,
            "autofocus.analysis_use_center_roi": True,
        }
    )
    real_handler = AutofocusHandler(handler._node, camera_driver=object())
    handler._prepare_autofocus_analysis_image = real_handler._prepare_autofocus_analysis_image
    handler._wait_for_new_passthrough_image = (
        lambda *_args, **_kwargs: (np.zeros((3000, 4000), dtype=np.uint16), 1, "bayer_rggb16")
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

    assert algorithm.seen_shape == (2048, 2048, 3)
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


def test_fly_over_detection_uses_precise_axis_position_reader():
    handler = AutofocusHandler(_Node({}), camera_driver=object())
    captured = {}

    class _FakeAxisClients:
        def get_position(self, clients, *, prefer_cached=True):
            captured["prefer_cached"] = prefer_cached
            return 5.0

    class _FakeFlyOverDetector:
        def __init__(
            self,
            node,
            get_latest_cv_image,
            get_center_roi,
            wait_for_axis_idle,
            get_position,
        ):
            _ = node, get_latest_cv_image, get_center_roi, wait_for_axis_idle
            captured["position"] = get_position({"position": object()})

        def detect(self, **_kwargs):
            return types.SimpleNamespace(peak_start=1.0, peak_end=2.0, max_stddev=3.0)

    handler._axis_clients = _FakeAxisClients()
    original_detector = autofocus_module.FlyOverDetector
    autofocus_module.FlyOverDetector = _FakeFlyOverDetector
    try:
        result = handler._fly_over_detection(1.0, 2.0, {"position": object()})
    finally:
        autofocus_module.FlyOverDetector = original_detector

    assert result == (1.0, 2.0, 3.0)
    assert captured["position"] == 5.0
    assert captured["prefer_cached"] is False


def test_autofocus_roi_callback_uses_interactively_selected_roi_when_request_is_empty():
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
    handler._get_latest_cv_image = lambda: (np.zeros((3000, 4000, 3), dtype=np.uint8), 1)
    handler._select_roi_interactive = lambda _image: ((120, 180, 900, 700), object())
    request = types.SimpleNamespace(
        roi_x=0,
        roi_y=0,
        roi_width=0,
        roi_height=0,
    )

    response = handler.autofocus_roi_callback(request, _Response())

    assert response.success is True
    assert captured["roi"] == (120, 180, 900, 700)


def test_autofocus_roi_callback_reports_cancelled_interactive_selection():
    handler = AutofocusHandler(
        _Node({"camera.expected_width": 4000, "camera.expected_height": 3000}),
        camera_driver=object(),
    )
    handler._get_latest_cv_image = lambda: (np.zeros((3000, 4000, 3), dtype=np.uint8), 1)
    handler._select_roi_interactive = lambda _image: (None, None)
    request = types.SimpleNamespace(
        roi_x=0,
        roi_y=0,
        roi_width=0,
        roi_height=0,
    )

    response = handler.autofocus_roi_callback(request, _Response())

    assert response.success is False
    assert "selection was cancelled" in response.status_message.lower()


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
