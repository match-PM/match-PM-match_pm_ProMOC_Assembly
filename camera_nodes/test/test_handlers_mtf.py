"""Smoke tests for MTF handler wiring."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import types

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace()

if "rcl_interfaces.msg" not in sys.modules:
    rcl_msg = types.ModuleType("rcl_interfaces.msg")

    class Parameter:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ParameterType:
        PARAMETER_NOT_SET = 0
        PARAMETER_INTEGER = 2
        PARAMETER_DOUBLE = 3
        PARAMETER_STRING = 4
        PARAMETER_BOOL = 5

    class ParameterValue:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    rcl_msg.Parameter = Parameter
    rcl_msg.ParameterType = ParameterType
    rcl_msg.ParameterValue = ParameterValue
    sys.modules["rcl_interfaces.msg"] = rcl_msg

if "rcl_interfaces.srv" not in sys.modules:
    rcl_srv = types.ModuleType("rcl_interfaces.srv")

    class _SrvType:
        class Request:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

    rcl_srv.GetParameters = _SrvType
    rcl_srv.ListParameters = _SrvType
    rcl_srv.SetParameters = _SrvType
    sys.modules["rcl_interfaces.srv"] = rcl_srv

if "rcl_interfaces" not in sys.modules:
    rcl_pkg = types.ModuleType("rcl_interfaces")
    rcl_pkg.msg = sys.modules["rcl_interfaces.msg"]
    rcl_pkg.srv = sys.modules["rcl_interfaces.srv"]
    sys.modules["rcl_interfaces"] = rcl_pkg

from camera_nodes.services import mtf as mtf_module  # noqa: E402
from camera_nodes import mtf_capture as mtf_capture_module  # noqa: E402
from camera_nodes.algorithms.mtf import MTFConfig  # noqa: E402
from camera_nodes.algorithms.mtf import MTFResult  # noqa: E402
from camera_nodes.services.mtf import MTFHandler  # noqa: E402
from promoc_core.promoc_exceptions import ImageProcessingError  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


@pytest.fixture(autouse=True)
def _isolate_mtf_output_directories(tmp_path, monkeypatch):
    """Tests must not reuse/overwrite checked-in acquisition fixtures."""
    (tmp_path / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf").mkdir(parents=True)
    monkeypatch.setitem(globals(), "ROOT", tmp_path)


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
        self.latest_camera_info = None
        self.latest_image_msg = None

    def has_parameter(self, name: str) -> bool:
        return name in self._params

    def get_parameter(self, name: str):
        return _Param(self._params[name])

    def get_logger(self):
        return self._logger

    def create_client(self, *_args, **_kwargs):
        return types.SimpleNamespace(wait_for_service=lambda timeout_sec=0.0: True)


def _make_measure_response():
    return types.SimpleNamespace(
        success=False,
        status_message="",
        mtf50=0.0,
        mtf20=0.0,
        mtf10=0.0,
        edge_angle=0.0,
        nyquist_frequency=0.0,
    )


def test_mtf_handler_builds_default_config():
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    cfg = handler._build_mtf_config(2.4, 2.0, 10.0, auto_roi=True)

    assert cfg.pixel_size_um == 2.4
    assert cfg.min_edge_angle == 2.0
    assert cfg.max_edge_angle == 10.0
    assert cfg.input_mode == "raw_bayer_rggb"
    assert cfg.capture_pixel_format == "BayerRG12"
    assert cfg.capture_binning_h == 1
    assert cfg.capture_binning_v == 1
    assert cfg.raw_bayer_pattern == "RGGB"


def test_camera_calibration_rejects_zero_placeholder():
    node = _Node({})
    node.latest_camera_info = types.SimpleNamespace(k=[0.0] * 9, d=[0.0] * 5)
    handler = MTFHandler(node=node, camera_driver=object())

    camera_matrix, dist_coeffs = handler._get_camera_calibration((100, 200))

    assert camera_matrix is None
    assert dist_coeffs is None


def test_camera_calibration_shifts_principal_point_for_edge_crop():
    node = _Node({})
    node.latest_camera_info = types.SimpleNamespace(
        k=[1000.0, 0.0, 500.0, 0.0, 1000.0, 400.0, 0.0, 0.0, 1.0],
        d=[0.1, -0.01, 0.0, 0.0, 0.0],
    )
    handler = MTFHandler(node=node, camera_driver=object())

    camera_matrix, dist_coeffs = handler._get_camera_calibration((120, 80))

    assert camera_matrix is not None
    assert camera_matrix[0, 2] == pytest.approx(380.0)
    assert camera_matrix[1, 2] == pytest.approx(320.0)
    assert dist_coeffs is not None


def test_measure_mtf_center_callback_forces_auto_roi():
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    captured = {}

    def _fake_measure_callback(request, response):
        captured["measurement_mode"] = getattr(request, "measurement_mode", "")
        captured["roi_input_source"] = getattr(request, "_mtf_roi_input_source", "")
        return response

    handler.measure_mtf_callback = _fake_measure_callback
    request = types.SimpleNamespace()

    handler.measure_mtf_center_callback(request, _make_measure_response())

    assert captured["measurement_mode"] == "auto"
    assert captured["roi_input_source"] == "alias_center"


def test_measure_mtf_roi_callback_forces_roi_mode_and_defaults_to_square_search():
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    captured = {}

    def _fake_measure_callback(request, response):
        captured["measurement_mode"] = getattr(request, "measurement_mode", "")
        captured["roi_input_source"] = getattr(request, "_mtf_roi_input_source", "")
        return response

    handler.measure_mtf_callback = _fake_measure_callback
    request = types.SimpleNamespace()

    handler.measure_mtf_roi_callback(request, _make_measure_response())

    assert captured["measurement_mode"] == "roi_search"
    assert captured["roi_input_source"] == "alias_roi"


def test_action_frame_core_uses_roi_service_square_search_and_all_four_edges(monkeypatch):
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    image = np.zeros((120, 140), dtype=np.uint16)
    captured = {}
    edge_rois = [
        mtf_module.EdgeROI(
            image=np.zeros((20, 40), dtype=np.uint16),
            bbox=(10 + index, 20 + index, 40, 20),
            edge_direction="horizontal" if name in {"top", "bottom"} else "vertical",
            edge_name=name,
            contrast=0.8,
            parent_center=(70, 60),
        )
        for index, name in enumerate(("top", "right", "bottom", "left"))
    ]

    def resolve(_image, request):
        captured["mode"] = request.measurement_mode
        captured["target"] = request.target_edge
        captured["roi"] = (request.roi_x, request.roi_y, request.roi_width, request.roi_height)
        return edge_rois

    monkeypatch.setattr(handler, "_resolve_edge_rois", resolve)
    monkeypatch.setattr(
        handler,
        "_analyze_edge_once",
        lambda edge, _config, _label: (
            None,
            MTFResult(valid=True, mtf50=80.0, edge_angle=5.0, edge_line=(0, 0, 10, 1)),
        ),
    )

    analysis = handler.analyze_mtf_roi_frame(
        image,
        (5, 6, 100, 90),
        vars(MTFConfig(input_mode="dense_gray", capture_pixel_format="Mono12")),
    )

    assert captured == {
        "mode": "roi_search",
        "target": "any",
        "roi": (5, 6, 100, 90),
    }
    assert analysis["mode"] == "roi_search_square4"
    assert [edge["edge_name"] for edge in analysis["edges"]] == [
        "top", "right", "bottom", "left"
    ]

    geometry = [
        {key: edge[key] for key in ("bbox", "edge_name", "edge_direction", "parent_center")}
        for edge in analysis["edges"]
    ]
    monkeypatch.setattr(
        handler,
        "_resolve_edge_rois",
        lambda *_args: pytest.fail("subsequent frames must reuse the detected edge boxes"),
    )
    reused = handler.analyze_mtf_roi_frame(
        image,
        (5, 6, 100, 90),
        vars(MTFConfig(input_mode="dense_gray", capture_pixel_format="Mono12")),
        geometry,
    )
    assert len(reused["edges"]) == 4


def test_capture_only_defaults_to_roi_square_search():
    handler = MTFHandler(node=_Node({}), camera_driver=object())

    request = types.SimpleNamespace(
        measurement_mode="capture_only",
    )

    normalized = handler._normalize_measurement_request(request)

    assert normalized.measurement_mode == "capture_only"
    assert handler._normalize_roi_detection_mode(normalized) == "search_square_in_roi"


def test_capture_only_direct_uses_direct_roi_mode():
    handler = MTFHandler(node=_Node({}), camera_driver=object())

    request = types.SimpleNamespace(
        measurement_mode="capture_direct",
    )

    normalized = handler._normalize_measurement_request(request)

    assert normalized.measurement_mode == "capture_only_direct"
    assert handler._normalize_roi_detection_mode(normalized) == "direct_manual"


def test_get_roi_coordinates_callback_returns_interactive_roi():
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    handler._get_mtf_capture_image = lambda: (
        np.zeros((80, 100), dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._select_roi_interactive_with_title = lambda _image, title: (
        (10, 20, 30, 40),
        np.zeros((40, 30), dtype=np.uint16),
    )
    response = types.SimpleNamespace(
        success=False,
        status_message="",
        roi_x=0,
        roi_y=0,
        roi_width=0,
        roi_height=0,
    )

    result = handler.get_roi_coordinates_callback(
        types.SimpleNamespace(window_name="Pick ROI"),
        response,
    )

    assert result.success is True
    assert (result.roi_x, result.roi_y, result.roi_width, result.roi_height) == (
        10,
        20,
        30,
        40,
    )
    assert "ROI selected" in result.status_message


def test_detect_square_edge_rois_in_search_roi_translates_back_to_global_coordinates(
    monkeypatch: pytest.MonkeyPatch,
):
    image = np.zeros((400, 500), dtype=np.uint16)
    search_roi = (100, 200, 50, 50)
    local_edge = mtf_module.EdgeROI(
        image=np.full((12, 10), 1024, dtype=np.uint16),
        bbox=(2, 3, 10, 12),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.8,
        parent_center=(8, 9),
    )

    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_targets",
        lambda _image, *_args, **_kwargs: ("viz", [], [((20.0, 20.0), (18.0, 18.0), 0.0)]),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "create_edge_rois_from_rect",
        lambda *_args, **_kwargs: [local_edge],
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "_rect_fully_inside_bounds",
        lambda *_args, **_kwargs: True,
    )

    translated = mtf_module.RoiDetector.detect_square_edge_rois_in_search_roi(
        image,
        search_roi,
    )

    assert len(translated) == 1
    assert translated[0].bbox == (102, 203, 10, 12)
    assert translated[0].parent_center == (108, 209)
    assert translated[0].edge_name == "top"


def test_auto_roi_uses_full_frame_square_detection_with_configured_minimums(
    monkeypatch: pytest.MonkeyPatch,
):
    handler = MTFHandler(
        node=_Node(
            {
                "mtf.roi_detection.min_contour_area_px": 700,
                "mtf.roi_detection.min_square_area_px": 3000,
                "mtf.roi_detection.min_square_side_px": 45,
                "mtf.roi_detection.min_edge_roi_width_px": 22,
                "mtf.roi_detection.edge_roi_width_px": 64,
            }
        ),
        camera_driver=object(),
    )
    image = np.zeros((480, 640), dtype=np.uint16)
    square = ((500.0, 80.0), (90.0, 90.0), 0.0)
    captured = {}
    edge_roi = mtf_module.EdgeROI(
        image=np.full((24, 48), 1024, dtype=np.uint16),
        bbox=(476, 56, 48, 24),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.8,
        parent_center=(500, 80),
    )

    def _detect_targets(_image, **kwargs):
        captured["detect_kwargs"] = kwargs
        return "viz", [], [square]

    def _create_edge_rois(_image, rect, **kwargs):
        captured["rect"] = rect
        captured["edge_kwargs"] = kwargs
        return [edge_roi]

    monkeypatch.setattr(mtf_module.RoiDetector, "detect_targets", _detect_targets)
    monkeypatch.setattr(mtf_module.RoiDetector, "_rect_fully_inside_bounds", lambda *_args: True)
    monkeypatch.setattr(mtf_module.RoiDetector, "create_edge_rois_from_rect", _create_edge_rois)

    detected = handler._detect_auto_edge_rois(image)

    assert detected == [edge_roi]
    assert captured["rect"] == square
    assert captured["detect_kwargs"]["min_area"] == 700
    assert captured["detect_kwargs"]["square_min_area"] == 3000
    assert captured["detect_kwargs"]["min_square_side"] == 45
    assert captured["edge_kwargs"]["roi_width"] == 64
    assert captured["edge_kwargs"]["min_edge_roi_width"] == 22


def test_roi_search_with_request_roi_skips_interactive_selection(monkeypatch: pytest.MonkeyPatch):
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    image = np.zeros((120, 160), dtype=np.uint16)
    edge_roi = mtf_module.EdgeROI(
        image=np.full((24, 48), 1024, dtype=np.uint16),
        bbox=(20, 30, 48, 24),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.8,
        parent_center=(44, 42),
    )
    captured = {}

    handler._select_roi_interactive = lambda _image: pytest.fail(
        "request ROI should not open interactive selection"
    )

    def _detect_in_search_roi(_image, search_roi, **kwargs):
        captured["search_roi"] = search_roi
        captured["kwargs"] = kwargs
        return [edge_roi]

    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_square_edge_rois_in_search_roi",
        _detect_in_search_roi,
    )
    request = types.SimpleNamespace(
        measurement_mode="roi_search",
        roi_x=10,
        roi_y=20,
        roi_width=80,
        roi_height=70,
        target_edge="",
    )

    detected = handler._resolve_edge_rois(image, handler._normalize_measurement_request(request))

    assert detected == [edge_roi]
    assert captured["search_roi"] == (10, 20, 80, 70)
    assert captured["kwargs"]["min_square_side"] == 40


def test_roi_search_rejects_too_small_request_roi():
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    image = np.zeros((120, 160), dtype=np.uint16)
    request = handler._normalize_measurement_request(
        types.SimpleNamespace(
            measurement_mode="roi_search",
            roi_x=10,
            roi_y=20,
            roi_width=20,
            roi_height=20,
            target_edge="",
        )
    )

    with pytest.raises(ImageProcessingError, match="ROI square search ROI too small"):
        handler._resolve_edge_rois(image, request)


def test_measure_mtf_uses_config_pixel_size_and_tracks_roi_origin(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_handler_exports"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "pixel_size_um": 3.45,
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
                "measurement_conditions.camera_objective": "Plan Apo 10x",
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((32, 32), 1024, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }

    edge_roi = mtf_module.EdgeROI(
        image=np.full((16, 16), 2048, dtype=np.uint16),
        bbox=(11, 13, 16, 16),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.8,
        parent_center=(20, 20),
    )

    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_targets",
        lambda _image, *_args, **_kwargs: ("viz", [], [((20.0, 20.0), (12.0, 12.0), 0.0)]),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "create_edge_rois_from_rect",
        lambda *_args, **_kwargs: [edge_roi],
    )
    monkeypatch.setattr(mtf_module, "MTF_AVG_SAMPLES", 1)

    class _FakeAnalyzer:
        init_config = None
        compute_calls = []

        def __init__(self, config, camera_matrix=None, dist_coeffs=None):
            type(self).init_config = config
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            type(self).compute_calls.append(
                {
                    "shape": image.shape,
                    "roi": roi,
                    "roi_origin": roi_origin,
                    "debug_label": debug_label,
                }
            )
            return MTFResult(
                mtf50=120.0,
                mtf20=80.0,
                mtf10=60.0,
                edge_angle=5.0,
                valid=True,
                sensor_nyquist=200.0,
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                capture_binning_h=self.config.capture_binning_h,
                capture_binning_v=self.config.capture_binning_v,
                capture_exposure_us=self.config.capture_exposure_us,
                capture_gain=self.config.capture_gain,
                illumination_wavelength_um=self.config.wavelength_um,
                source_encoding=self.config.source_encoding,
                g1_mtf50=118.0,
                g2_mtf50=122.0,
                g1_mtf20=76.0,
                g2_mtf20=78.0,
                g1_mtf10=56.0,
                g2_mtf10=58.0,
                g1_g2_delta_pct=3.3,
            )

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FakeAnalyzer)

    request = types.SimpleNamespace(
        measurement_mode="auto",
        target_edge="",
        notes="scientific regression",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is True
    assert _FakeAnalyzer.init_config.pixel_size_um == 3.45
    assert _FakeAnalyzer.init_config.measurement_metadata["camera_objective"] == "Plan Apo 10x"
    assert _FakeAnalyzer.init_config.measurement_metadata["pixel_size_source"] == "camera_config"
    assert _FakeAnalyzer.compute_calls[0]["roi_origin"] == (11, 13)
    assert "MTF complete:" in result.status_message


def test_measure_mtf_returns_failure_on_scientific_capture_mismatch(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_handler_capture_failure"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "capture_user",
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((32, 32), 1024, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": True,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: ["gamma_enable=True!=False"]
    )
    handler._get_timestamp = lambda: "20260419_100500"

    result = handler.measure_mtf_callback(
        types.SimpleNamespace(measurement_mode="auto", target_edge=""),
        _make_measure_response(),
    )

    assert result.success is False
    assert "Scientific MTF capture readback mismatch" in result.status_message
    assert "gamma_enable=True!=False" in result.status_message
    assert "restore the scientific raw capture settings" in result.status_message

    run_dir = (
        tmp_dir
        / "capture_user"
        / "mtf_messungen"
        / "mtf_auto_20260419_100500"
    )
    context_path = run_dir / "context.csv"
    summary_path = run_dir / "summary.csv"
    assert context_path.exists()
    assert summary_path.exists()

    with open(context_path, newline="", encoding="utf-8") as csv_file:
        context_rows = list(csv.DictReader(csv_file))

    assert len(context_rows) == 1
    assert context_rows[0]["measurement_success"] == "0"
    assert context_rows[0]["capture_readback_ok"] == "0"
    assert "gamma_enable=True!=False" in context_rows[0]["capture_readback_mismatches"]
    assert "Scientific MTF capture readback mismatch" in context_rows[0]["measurement_error"]
    assert context_rows[0]["selected_official_sop_angle_window_ok"] == "0"
    assert context_rows[0]["selected_official_sop_reason"] == "no valid selected edge"
    assert context_rows[0]["selected_measured_edge_angle_deg"] == ""


def test_write_visual_measurement_exports_writes_overview_and_larger_roi(
    monkeypatch: pytest.MonkeyPatch,
):
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    run_dir = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "visual_exports"
    run_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, tuple[int, ...]] = {}

    monkeypatch.setattr(
        mtf_module,
        "cv2",
        types.SimpleNamespace(
            LINE_AA=16,
            FONT_HERSHEY_SIMPLEX=0,
            rectangle=lambda image, *_args, **_kwargs: image,
            putText=lambda image, *_args, **_kwargs: image,
            imwrite=lambda path, image: written.setdefault(Path(path).name, tuple(image.shape)) or True,
        ),
    )

    edge_roi = mtf_module.EdgeROI(
        image=np.zeros((40, 40), dtype=np.uint8),
        bbox=(80, 60, 40, 40),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.9,
        parent_center=(100, 80),
    )
    result = MTFResult(
        valid=True,
        mtf50=42.0,
        edge_angle=4.5,
        analysis_roi_bounds=(88, 68, 112, 92),
    )
    measured_edge = mtf_module._MeasuredEdge(
        edge_label="01_top",
        edge_roi=edge_roi,
        result=result,
        valid_samples=[result],
        avg_mtf50=42.0,
        avg_mtf20=0.0,
        avg_mtf10=0.0,
        avg_angle=4.5,
        avg_g1_mtf50=0.0,
        avg_g2_mtf50=0.0,
        avg_delta_pct=0.0,
    )

    handler._write_visual_measurement_exports(
        run_dir=run_dir,
        source_image=np.zeros((200, 300, 3), dtype=np.uint8),
        image_encoding="bgr8",
        edge_rows=[
            {
                "edge_label": "01_top",
                "roi_bbox_x": 80,
                "roi_bbox_y": 60,
                "roi_bbox_w": 40,
                "roi_bbox_h": 40,
                "valid": 1,
                "selected_for_response": 1,
                "mtf50_lpmm": 42.0,
                "edge_angle_deg": 4.5,
            }
        ],
        measured_edges=[measured_edge],
        selected_edge=measured_edge,
    )

    assert "01_top_roi.png" in written
    assert "edges_overview.png" in written
    assert written["01_top_roi.png"][0] > 40
    assert written["01_top_roi.png"][1] > 40


def test_write_visual_measurement_exports_skips_analysis_box_overlay(
    monkeypatch: pytest.MonkeyPatch,
):
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    run_dir = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "visual_exports_no_analysis_box"
    run_dir.mkdir(parents=True, exist_ok=True)

    rectangle_calls: list[tuple[tuple[int, int], tuple[int, int]]] = []

    monkeypatch.setattr(
        mtf_module,
        "cv2",
        types.SimpleNamespace(
            LINE_AA=16,
            FONT_HERSHEY_SIMPLEX=0,
            rectangle=lambda image, pt1, pt2, *_args, **_kwargs: rectangle_calls.append((pt1, pt2)) or image,
            putText=lambda image, *_args, **_kwargs: image,
            imwrite=lambda _path, _image: True,
        ),
    )

    edge_roi = mtf_module.EdgeROI(
        image=np.zeros((40, 40), dtype=np.uint8),
        bbox=(80, 60, 40, 40),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.9,
        parent_center=(100, 80),
    )
    result = MTFResult(
        valid=True,
        mtf50=42.0,
        edge_angle=4.5,
        analysis_roi_bounds=(88, 68, 112, 92),
    )
    measured_edge = mtf_module._MeasuredEdge(
        edge_label="01_top",
        edge_roi=edge_roi,
        result=result,
        valid_samples=[result],
        avg_mtf50=42.0,
        avg_mtf20=0.0,
        avg_mtf10=0.0,
        avg_angle=4.5,
        avg_g1_mtf50=0.0,
        avg_g2_mtf50=0.0,
        avg_delta_pct=0.0,
    )

    handler._write_visual_measurement_exports(
        run_dir=run_dir,
        source_image=np.zeros((200, 300, 3), dtype=np.uint8),
        image_encoding="bgr8",
        edge_rows=[
            {
                "edge_label": "01_top",
                "roi_bbox_x": 80,
                "roi_bbox_y": 60,
                "roi_bbox_w": 40,
                "roi_bbox_h": 40,
                "valid": 1,
                "selected_for_response": 1,
                "mtf50_lpmm": 42.0,
                "edge_angle_deg": 4.5,
            }
        ],
        measured_edges=[measured_edge],
        selected_edge=measured_edge,
    )

    assert len(rectangle_calls) == 2


def test_measure_mtf_exports_multi_edge_summary_csv(monkeypatch: pytest.MonkeyPatch):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_handler_multi_edge"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "student1",
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
                "mtf.capture_width": 5536,
                "mtf.capture_height": 3692,
                "measurement_conditions.camera_objective": "Plan Apo 10x",
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((64, 64), 2048, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._get_timestamp = lambda: "20260419_101500"

    edge_rois = [
        mtf_module.EdgeROI(
            image=np.full((16, 40), 2048, dtype=np.uint16),
            bbox=(10, 12, 40, 16),
            edge_direction="horizontal",
            edge_name="top",
            contrast=0.8,
            parent_center=(32, 32),
        ),
        mtf_module.EdgeROI(
            image=np.full((40, 16), 2048, dtype=np.uint16),
            bbox=(42, 10, 16, 40),
            edge_direction="vertical",
            edge_name="right",
            contrast=0.7,
            parent_center=(32, 32),
        ),
    ]

    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_targets",
        lambda _image, *_args, **_kwargs: ("viz", [], [((32.0, 32.0), (30.0, 30.0), 0.0)]),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "create_edge_rois_from_rect",
        lambda *_args, **_kwargs: edge_rois,
    )
    monkeypatch.setattr(mtf_module, "MTF_AVG_SAMPLES", 1)

    class _FakeAnalyzer:
        compute_calls = []

        def __init__(self, config, camera_matrix=None, dist_coeffs=None):
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            type(self).compute_calls.append(
                {
                    "roi_origin": roi_origin,
                    "debug_label": debug_label,
                    "edge_name": self.config.measurement_metadata.get("edge_name"),
                }
            )
            mtf50 = 120.0 if debug_label == "01_top" else 95.0
            return MTFResult(
                mtf50=mtf50,
                mtf20=80.0,
                mtf10=60.0,
                edge_angle=5.0,
                valid=True,
                sensor_nyquist=200.0,
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                capture_binning_h=self.config.capture_binning_h,
                capture_binning_v=self.config.capture_binning_v,
                capture_exposure_us=self.config.capture_exposure_us,
                capture_gain=self.config.capture_gain,
                illumination_wavelength_um=self.config.wavelength_um,
                source_encoding=self.config.source_encoding,
                g1_mtf50=mtf50 - 1.0,
                g2_mtf50=mtf50 + 1.0,
                g1_mtf20=76.0,
                g2_mtf20=78.0,
                g1_mtf10=56.0,
                g2_mtf10=58.0,
                g1_g2_delta_pct=1.6,
                edge_angle_method="geometric",
            )

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FakeAnalyzer)

    request = types.SimpleNamespace(
        measurement_mode="auto",
        target_edge="",
        notes="multi-edge export",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is True
    assert result.mtf50 == 120.0
    assert len(_FakeAnalyzer.compute_calls) == 2
    assert [call["debug_label"] for call in _FakeAnalyzer.compute_calls] == ["01_top", "02_right"]
    assert "MTF complete:" in result.status_message
    assert "mode=auto" in result.status_message
    assert "selected=01_top" in result.status_message
    assert "valid_edges=2/2" in result.status_message
    assert "summary=" in result.status_message

    csv_path = Path(result.status_message.split("summary=", 1)[1].split(",", 1)[0])
    assert csv_path.exists()
    assert csv_path.name == "summary.csv"
    assert csv_path.parent.parent.name == "mtf_messungen"
    assert csv_path.parent.parent.parent.name == "student1"
    assert (csv_path.parent / "selected_edge.txt").read_text(encoding="utf-8").strip() == "01_top"
    context_path = csv_path.parent / "context.csv"
    assert context_path.exists()

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    with open(context_path, newline="", encoding="utf-8") as csv_file:
        context_rows = list(csv.DictReader(csv_file))

    assert len(rows) == 2
    assert rows[0]["edge_label"] == "01_top"
    assert rows[0]["selected_for_response"] == "1"
    assert rows[0]["official_sop_angle_window_ok"] == "1"
    assert rows[0]["official_sop_min_angle_deg"] == "3.0"
    assert rows[0]["official_sop_max_angle_deg"] == "10.0"
    assert rows[0]["official_sop_angle_basis"] == "measured_final_edge_angle_deg"
    assert rows[0]["official_sop_reason"] == ""
    assert rows[1]["edge_label"] == "02_right"
    assert rows[1]["selected_for_response"] == "0"
    assert rows[1]["official_sop_angle_window_ok"] == "1"
    assert len(context_rows) == 1
    assert context_rows[0]["operator"] == "student1"
    assert context_rows[0]["roi_mode"] == "auto"
    assert context_rows[0]["camera_objective"] == "Plan Apo 10x"
    assert context_rows[0]["objective_magnification_x"] == "10.0"
    assert context_rows[0]["capture_readback_ok"] == "1"
    assert context_rows[0]["stream_width_px"] == "64"
    assert context_rows[0]["stream_height_px"] == "64"
    assert context_rows[0]["requested_stream_width_px"] == "5536"
    assert context_rows[0]["requested_stream_height_px"] == "3692"
    assert context_rows[0]["stream_geometry_matches_request"] == "0"
    assert context_rows[0]["selected_edge_label"] == "01_top"
    assert context_rows[0]["valid_edge_count"] == "2"
    assert context_rows[0]["selected_measured_edge_angle_deg"] == "5.0"
    assert context_rows[0]["selected_official_sop_angle_window_ok"] == "1"
    assert (
        context_rows[0]["selected_official_sop_angle_basis"]
        == "measured_final_edge_angle_deg"
    )
    assert context_rows[0]["selected_official_sop_reason"] == ""


def test_measure_mtf_capture_only_writes_roi_stacks_without_analyzer(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_capture_only"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "capture_user",
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
                "mtf.capture_width": 64,
                "mtf.capture_height": 64,
                "mtf.capture_only_samples": 3,
                "mtf.capture_only_timeout_s": 0.1,
                "mtf.capture_only_preview_png": False,
            }
        ),
        camera_driver=object(),
    )
    frames = [
        np.full((64, 64), 1000 + index, dtype=np.uint16)
        for index in range(3)
    ]
    handler._get_mtf_capture_image = lambda: (frames[0], 100, "bayer_rggb16")

    wait_calls = {"count": 0}

    def _wait_for_new(_last_ts, timeout=1.0):
        wait_calls["count"] += 1
        index = wait_calls["count"]
        if index >= len(frames):
            return None, None, "bayer_rggb16"
        return frames[index], 100 + index, "bayer_rggb16"

    handler._wait_for_new_mtf_capture_image = _wait_for_new
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._get_timestamp = lambda: "20260430_090000"

    edge_rois = [
        mtf_module.EdgeROI(
            image=frames[0][10:26, 12:52],
            bbox=(12, 10, 40, 16),
            edge_direction="horizontal",
            edge_name="top",
            contrast=0.8,
            parent_center=(32, 32),
        )
    ]
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_square_edge_rois_in_search_roi",
        lambda *_args, **_kwargs: edge_rois,
    )

    class _FailAnalyzer:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("capture_only must not run MTFAnalyzer")

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FailAnalyzer)

    request = types.SimpleNamespace(
        measurement_mode="capture_only",
        roi_x=0,
        roi_y=0,
        roi_width=64,
        roi_height=64,
        target_edge="",
        notes="capture only",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is True
    assert result.mtf50 == 0.0
    assert "capture-only complete" in result.status_message

    run_dir = (
        tmp_dir
        / "capture_user"
        / "mtf_messungen"
        / "mtf_capture_only_20260430_090000"
    )
    manifest_path = run_dir / "capture_manifest.json"
    assert manifest_path.exists()
    assert (run_dir / "capture_index.csv").exists()
    assert (run_dir / "summary.csv").exists()
    assert (run_dir / "context.csv").exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["measurement_mode"] == "capture_only"
    assert manifest["edges"][0]["edge_label"] == "top"
    assert manifest["edges"][0]["bbox"] == [12, 10, 40, 16]
    assert manifest["edges"][0]["stack_bbox"] == [0, 0, 64, 64]
    assert manifest["edges"][0]["stack_origin"] == [0, 0]
    assert manifest["edges"][0]["edge_bbox_in_stack"] == [12, 10, 40, 16]
    stack = np.load(run_dir / manifest["edges"][0]["stack_file"])
    assert stack.shape == (3, 64, 64)
    assert stack.dtype == np.uint16
    assert [int(sample[0, 0]) for sample in stack] == [1000, 1001, 1002]


def test_measure_mtf_capture_only_direct_skips_square_detection(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_capture_only_direct"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "capture_user",
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
                "mtf.capture_width": 64,
                "mtf.capture_height": 64,
                "mtf.capture_only_samples": 2,
                "mtf.capture_only_timeout_s": 0.1,
                "mtf.capture_only_preview_png": False,
            }
        ),
        camera_driver=object(),
    )
    frames = [
        np.full((64, 64), 2000 + index, dtype=np.uint16)
        for index in range(2)
    ]
    handler._get_mtf_capture_image = lambda: (frames[0], 200, "bayer_rggb16")

    wait_calls = {"count": 0}

    def _wait_for_new(_last_ts, timeout=1.0):
        wait_calls["count"] += 1
        index = wait_calls["count"]
        if index >= len(frames):
            return None, None, "bayer_rggb16"
        return frames[index], 200 + index, "bayer_rggb16"

    handler._wait_for_new_mtf_capture_image = _wait_for_new
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._get_timestamp = lambda: "20260430_090500"

    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_square_edge_rois_in_search_roi",
        lambda *_args, **_kwargs: pytest.fail("direct capture must not search square ROIs"),
    )

    class _FailAnalyzer:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("capture_only_direct must not run MTFAnalyzer")

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FailAnalyzer)

    request = types.SimpleNamespace(
        measurement_mode="capture_only_direct",
        roi_x=8,
        roi_y=9,
        roi_width=24,
        roi_height=22,
        target_edge="",
        notes="direct capture",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is True
    run_dir = (
        tmp_dir
        / "capture_user"
        / "mtf_messungen"
        / "mtf_capture_direct_20260430_090500"
    )
    manifest = json.loads((run_dir / "capture_manifest.json").read_text(encoding="utf-8"))
    assert manifest["measurement_mode"] == "capture_only_direct"
    assert manifest["roi_mode"] == "capture_only_direct"
    assert manifest["edges"][0]["bbox"] == [8, 9, 24, 22]
    assert manifest["edges"][0]["stack_bbox"] == [0, 0, 64, 64]
    assert manifest["edges"][0]["edge_bbox_in_stack"] == [8, 9, 24, 22]
    stack = np.load(run_dir / manifest["edges"][0]["stack_file"])
    assert stack.shape == (2, 64, 64)
    assert [int(sample[0, 0]) for sample in stack] == [2000, 2001]


def test_offline_batch_analyzes_capture_manifest(monkeypatch: pytest.MonkeyPatch):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    run_dir = tmp_root / "mtf_batch_capture" / "mtf_capture_only_20260430_091500"
    run_dir.mkdir(parents=True, exist_ok=True)
    stack = np.stack(
        [
            np.full((16, 40), 1200, dtype=np.uint16),
            np.full((16, 40), 1300, dtype=np.uint16),
        ],
        axis=0,
    )
    np.save(run_dir / "top_raw_stack.npy", stack)

    config = MTFConfig(
        pixel_size_um=2.4,
        input_mode="raw_bayer_rggb",
        raw_bayer_pattern="RGGB",
        capture_pixel_format="BayerRG12",
        capture_binning_h=1,
        capture_binning_v=1,
        capture_exposure_us=100000.0,
        capture_gain=0.0,
        source_encoding="bayer_rggb16",
    )
    manifest = {
        "schema_version": 1,
        "run_id": "mtf_capture_only_20260430_091500",
        "timestamp": "20260430_091500",
        "measurement_mode": "capture_only",
        "roi_mode": "capture_only",
        "measurement_metadata": {
            "measurement_operator": "capture_user",
            "measurement_mode": "capture_only",
            "effective_pixel_size_um": 2.4,
            "pixel_size_source": "request",
        },
        "capture_values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
        },
        "capture_available_keys": ["pixel_format"],
        "capture_mismatches": [],
        "image_encoding": "bayer_rggb16",
        "edges": [
            {
                "edge_label": "top",
                "edge_name": "top",
                "edge_direction": "horizontal",
                "bbox": [12, 10, 40, 16],
                "parent_center": [32, 32],
                "contrast": 0.8,
                "sample_count": 2,
                "dtype": "uint16",
                "shape": list(stack.shape),
                "stack_file": "top_raw_stack.npy",
                "mtf_config": mtf_capture_module.config_to_manifest_dict(config),
            }
        ],
    }
    manifest_path = mtf_capture_module.write_capture_manifest(run_dir, manifest)

    class _FakeAnalyzer:
        def __init__(self, config):
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            value = float(np.mean(image))
            return MTFResult(
                mtf50=value / 10.0,
                mtf20=80.0,
                mtf10=60.0,
                edge_angle=5.0,
                valid=True,
                sensor_nyquist=200.0,
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                capture_binning_h=self.config.capture_binning_h,
                capture_binning_v=self.config.capture_binning_v,
                capture_exposure_us=self.config.capture_exposure_us,
                capture_gain=self.config.capture_gain,
                edge_angle_method="geometric",
            )

    monkeypatch.setattr(mtf_capture_module, "MTFAnalyzer", _FakeAnalyzer)

    result = mtf_capture_module.analyze_capture_manifest(
        manifest_path,
        overwrite=True,
    )

    assert result["selected_edge_label"] == "top"
    assert (run_dir / "selected_edge.txt").read_text(encoding="utf-8").strip() == "top"
    with open(run_dir / "summary.csv", newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[0]["valid"] == "1"
    assert rows[0]["sample_count"] == "2"
    assert rows[0]["mtf50_lpmm"] == "125.0"
    with open(run_dir / "context.csv", newline="", encoding="utf-8") as csv_file:
        context_rows = list(csv.DictReader(csv_file))
    assert context_rows[0]["measurement_success"] == "1"
    assert context_rows[0]["selected_edge_label"] == "top"


def test_offline_batch_accepts_partial_edges_and_target_selection(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    run_dir = tmp_root / "mtf_batch_partial" / "mtf_capture_only_20260430_092000"
    run_dir.mkdir(parents=True, exist_ok=True)
    top_stack = np.full((3, 16, 40), 100, dtype=np.uint16)
    bottom_stack = np.stack(
        [
            np.full((16, 40), 1200, dtype=np.uint16),
            np.full((16, 40), 100, dtype=np.uint16),
            np.full((16, 40), 1300, dtype=np.uint16),
        ],
        axis=0,
    )
    np.save(run_dir / "01_top_raw_stack.npy", top_stack)
    np.save(run_dir / "02_bottom_raw_stack.npy", bottom_stack)

    config = MTFConfig(
        pixel_size_um=2.4,
        input_mode="raw_bayer_rggb",
        raw_bayer_pattern="RGGB",
        capture_pixel_format="BayerRG12",
        capture_binning_h=1,
        capture_binning_v=1,
        capture_exposure_us=100000.0,
        capture_gain=0.0,
        source_encoding="bayer_rggb16",
    )
    manifest = {
        "schema_version": 1,
        "run_id": "mtf_capture_only_20260430_092000",
        "timestamp": "20260430_092000",
        "measurement_mode": "capture_only",
        "roi_mode": "capture_only",
        "measurement_metadata": {
            "measurement_operator": "capture_user",
            "measurement_mode": "capture_only",
            "effective_pixel_size_um": 2.4,
            "pixel_size_source": "request",
        },
        "capture_values": {"pixel_format": "BayerRG12", "bin_h": 1, "bin_v": 1},
        "capture_available_keys": ["pixel_format"],
        "capture_mismatches": [],
        "image_encoding": "bayer_rggb16",
        "edges": [
            {
                "edge_label": "01_top",
                "edge_name": "top",
                "edge_direction": "horizontal",
                "bbox": [12, 10, 40, 16],
                "parent_center": [32, 32],
                "contrast": 0.8,
                "sample_count": 3,
                "dtype": "uint16",
                "shape": list(top_stack.shape),
                "stack_file": "01_top_raw_stack.npy",
                "mtf_config": mtf_capture_module.config_to_manifest_dict(config),
            },
            {
                "edge_label": "02_bottom",
                "edge_name": "bottom",
                "edge_direction": "horizontal",
                "bbox": [12, 40, 40, 16],
                "parent_center": [32, 32],
                "contrast": 0.8,
                "sample_count": 3,
                "dtype": "uint16",
                "shape": list(bottom_stack.shape),
                "stack_file": "02_bottom_raw_stack.npy",
                "mtf_config": mtf_capture_module.config_to_manifest_dict(config),
            },
        ],
    }
    manifest_path = mtf_capture_module.write_capture_manifest(run_dir, manifest)

    class _FakeAnalyzer:
        def __init__(self, config):
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            value = float(np.mean(image))
            if value < 1000.0:
                return MTFResult(valid=False, error_msg="low contrast sample")
            return MTFResult(
                mtf50=value / 10.0,
                mtf20=80.0,
                mtf10=60.0,
                edge_angle=5.0,
                valid=True,
                sensor_nyquist=200.0,
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                edge_angle_method="geometric",
            )

    monkeypatch.setattr(mtf_capture_module, "MTFAnalyzer", _FakeAnalyzer)

    result = mtf_capture_module.analyze_capture_manifest(
        manifest_path,
        overwrite=True,
        target_edge="bottom",
        min_valid_edges=1,
    )

    assert result["measurement_success"] is True
    assert result["valid_edge_count"] == 1
    assert result["selected_edge_label"] == "02_bottom"
    assert result["selected_sample_count"] == 2
    assert (run_dir / "selected_edge.txt").read_text(encoding="utf-8").strip() == "02_bottom"
    with open(run_dir / "summary.csv", newline="", encoding="utf-8") as csv_file:
        rows = {row["edge_label"]: row for row in csv.DictReader(csv_file)}
    assert rows["01_top"]["valid"] == "0"
    assert rows["02_bottom"]["valid"] == "1"
    assert rows["02_bottom"]["stored_sample_count"] == "3"
    assert rows["02_bottom"]["valid_sample_count"] == "2"
    assert rows["02_bottom"]["rejected_sample_count"] == "1"
    assert rows["02_bottom"]["mtf50_lpmm"] == "125.0"
    if hasattr(mtf_capture_module.cv2, "imread"):
        review_png = mtf_capture_module.cv2.imread(str(run_dir / "02_bottom_roi.png"))
        assert review_png is not None
        assert review_png.shape[1] >= 720
        assert review_png.shape[0] >= 420


def test_measure_mtf_manual_roi_exports_summary_and_keeps_manual_label(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_handler_manual"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "manual_user",
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((80, 80), 2048, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._get_timestamp = lambda: "20260419_102000"
    handler._select_roi_interactive = lambda _image: (
        (12, 14, 24, 30),
        np.full((30, 24), 2048, dtype=np.uint16),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_all_targets",
        lambda _roi_img: [],
    )

    class _FakeAnalyzer:
        compute_calls = []

        def __init__(self, config, camera_matrix=None, dist_coeffs=None):
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            type(self).compute_calls.append(
                {
                    "roi_origin": roi_origin,
                    "debug_label": debug_label,
                    "edge_name": self.config.measurement_metadata.get("edge_name"),
                }
            )
            return MTFResult(
                mtf50=88.0,
                mtf20=60.0,
                mtf10=40.0,
                edge_angle=4.8,
                valid=True,
                sensor_nyquist=200.0,
                mtf_peak=1.08,
                mtf_peak_raw=1.12,
                mtf_clipped=False,
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                capture_binning_h=self.config.capture_binning_h,
                capture_binning_v=self.config.capture_binning_v,
                capture_exposure_us=self.config.capture_exposure_us,
                capture_gain=self.config.capture_gain,
                illumination_wavelength_um=self.config.wavelength_um,
                source_encoding=self.config.source_encoding,
                g1_mtf50=87.5,
                g2_mtf50=88.5,
                g1_mtf20=59.0,
                g2_mtf20=61.0,
                g1_mtf10=39.0,
                g2_mtf10=41.0,
                g1_g2_delta_pct=1.1,
                edge_angle_method="geometric",
            )

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FakeAnalyzer)
    monkeypatch.setattr(mtf_module, "MTF_AVG_SAMPLES", 1)

    request = types.SimpleNamespace(
        measurement_mode="direct_manual",
        target_edge="",
        notes="manual export",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is True
    assert result.mtf50 == 88.0
    assert len(_FakeAnalyzer.compute_calls) == 1
    assert _FakeAnalyzer.compute_calls[0]["roi_origin"] == (12, 14)
    assert _FakeAnalyzer.compute_calls[0]["debug_label"] == "manual"
    assert "mode=manual" in result.status_message
    assert "selected=manual" in result.status_message
    assert "valid_edges=1/1" in result.status_message

    csv_path = Path(result.status_message.split("summary=", 1)[1].split(",", 1)[0])
    assert csv_path.exists()
    assert csv_path.name == "summary.csv"
    assert csv_path.parent.parent.parent.name == "manual_user"
    assert (csv_path.parent / "selected_edge.txt").read_text(encoding="utf-8").strip() == "manual"
    context_path = csv_path.parent / "context.csv"
    assert context_path.exists()

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    with open(context_path, newline="", encoding="utf-8") as csv_file:
        context_rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["edge_label"] == "manual"
    assert rows[0]["edge_name"] == "manual"
    assert rows[0]["selected_for_response"] == "1"
    assert rows[0]["mtf_peak_raw"] == "1.12"
    assert rows[0]["mtf_peak_used"] == "1.08"
    assert rows[0]["mtf_clipped"] == "0"
    assert len(context_rows) == 1
    assert context_rows[0]["operator"] == "manual_user"
    assert context_rows[0]["roi_mode"] == "manual"
    assert context_rows[0]["selected_edge_label"] == "manual"
    assert context_rows[0]["valid_edge_count"] == "1"
    assert context_rows[0]["selected_mtf_peak_raw"] == "1.12"
    assert context_rows[0]["selected_mtf_peak_used"] == "1.08"
    assert context_rows[0]["selected_mtf_clipped"] == "0"
    assert context_rows[0]["selected_measured_edge_angle_deg"] == "4.8"
    assert context_rows[0]["selected_official_sop_angle_window_ok"] == "1"
    assert context_rows[0]["selected_official_sop_reason"] == ""


def test_validate_scientific_capture_state_reports_raw_switch_error():
    handler = MTFHandler(
        node=_Node(
            {
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._camera_format_controller._last_operation_error = (
        "Failed to set PixelFormat=BayerRG12: parameter was not declared"
    )

    try:
        handler._validate_scientific_capture_state({}, "rgb8")
    except ImageProcessingError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected ImageProcessingError for rgb8 scientific capture")

    assert "raw Bayer or Mono input" in message
    assert "Raw-switch status" in message
    assert "PixelFormat=BayerRG12" in message


@pytest.mark.parametrize(
    ("measured_angle_deg", "expected_ok", "expected_reason_fragment"),
    [
        (2.99, "0", "below official SOP minimum 3.0deg"),
        (3.0, "1", ""),
        (10.0, "1", ""),
    ],
)
def test_measure_mtf_marks_selected_edge_with_official_sop_window(
    monkeypatch: pytest.MonkeyPatch,
    measured_angle_deg: float,
    expected_ok: str,
    expected_reason_fragment: str,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_handler_sop_boundary"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "boundary_user",
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((64, 64), 2048, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._get_timestamp = lambda: "20260420_120000"

    edge_roi = mtf_module.EdgeROI(
        image=np.full((16, 40), 2048, dtype=np.uint16),
        bbox=(10, 12, 40, 16),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.8,
        parent_center=(32, 32),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_targets",
        lambda _image, *_args, **_kwargs: ("viz", [], [((32.0, 32.0), (30.0, 30.0), 0.0)]),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "create_edge_rois_from_rect",
        lambda *_args, **_kwargs: [edge_roi],
    )
    monkeypatch.setattr(mtf_module, "MTF_AVG_SAMPLES", 1)

    class _FakeAnalyzer:
        def __init__(self, config, camera_matrix=None, dist_coeffs=None):
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            return MTFResult(
                mtf50=100.0,
                mtf20=70.0,
                mtf10=50.0,
                edge_angle=measured_angle_deg,
                valid=True,
                sensor_nyquist=200.0,
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                capture_binning_h=self.config.capture_binning_h,
                capture_binning_v=self.config.capture_binning_v,
                capture_exposure_us=self.config.capture_exposure_us,
                capture_gain=self.config.capture_gain,
                illumination_wavelength_um=self.config.wavelength_um,
                source_encoding=self.config.source_encoding,
                edge_angle_method="geometric",
            )

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FakeAnalyzer)

    request = types.SimpleNamespace(
        measurement_mode="auto",
        target_edge="",
        notes="boundary export",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is True
    csv_path = Path(result.status_message.split("summary=", 1)[1].split(",", 1)[0])
    context_path = csv_path.parent / "context.csv"

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    with open(context_path, newline="", encoding="utf-8") as csv_file:
        context_rows = list(csv.DictReader(csv_file))

    assert rows[0]["official_sop_angle_window_ok"] == expected_ok
    assert rows[0]["selected_for_response"] == "1"
    assert context_rows[0]["selected_official_sop_angle_window_ok"] == expected_ok
    assert context_rows[0]["selected_measured_edge_angle_deg"] == str(measured_angle_deg)
    if expected_reason_fragment:
        assert expected_reason_fragment in rows[0]["official_sop_reason"]
        assert expected_reason_fragment in context_rows[0]["selected_official_sop_reason"]
    else:
        assert rows[0]["official_sop_reason"] == ""
        assert context_rows[0]["selected_official_sop_reason"] == ""


def test_measure_mtf_marks_invalid_edge_as_not_officially_accepted(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_handler_invalid_edge"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "invalid_user",
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((64, 64), 2048, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._get_timestamp = lambda: "20260420_121500"

    edge_roi = mtf_module.EdgeROI(
        image=np.full((16, 40), 2048, dtype=np.uint16),
        bbox=(10, 12, 40, 16),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.8,
        parent_center=(32, 32),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_targets",
        lambda _image, *_args, **_kwargs: ("viz", [], [((32.0, 32.0), (30.0, 30.0), 0.0)]),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "create_edge_rois_from_rect",
        lambda *_args, **_kwargs: [edge_roi],
    )
    monkeypatch.setattr(mtf_module, "MTF_AVG_SAMPLES", 1)

    class _FakeAnalyzer:
        def __init__(self, config, camera_matrix=None, dist_coeffs=None):
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            return MTFResult(
                mtf50=0.0,
                mtf20=0.0,
                mtf10=0.0,
                edge_angle=10.5,
                valid=False,
                error_msg="Angle outside node validation range",
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                capture_binning_h=self.config.capture_binning_h,
                capture_binning_v=self.config.capture_binning_v,
                capture_exposure_us=self.config.capture_exposure_us,
                capture_gain=self.config.capture_gain,
                illumination_wavelength_um=self.config.wavelength_um,
                source_encoding=self.config.source_encoding,
                edge_angle_method="geometric",
            )

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FakeAnalyzer)

    request = types.SimpleNamespace(
        measurement_mode="auto",
        target_edge="",
        notes="invalid export",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is False
    run_dir = tmp_dir / "invalid_user" / "mtf_messungen" / "mtf_auto_20260420_121500"
    summary_path = run_dir / "summary.csv"
    context_path = run_dir / "context.csv"
    assert summary_path.exists()
    assert context_path.exists()

    with open(summary_path, newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    with open(context_path, newline="", encoding="utf-8") as csv_file:
        context_rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["valid"] == "0"
    assert rows[0]["official_sop_angle_window_ok"] == "0"
    assert rows[0]["official_sop_reason"] == "edge technically invalid; no official SOP acceptance"
    assert context_rows[0]["measurement_success"] == "0"
    assert context_rows[0]["selected_official_sop_angle_window_ok"] == "0"
    assert context_rows[0]["selected_official_sop_reason"] == "no valid selected edge"
    assert context_rows[0]["selected_measured_edge_angle_deg"] == ""
    assert "MTF failed on all candidate edges" in result.status_message
    assert "switch between auto and manual ROI" in result.status_message


def test_measure_mtf_reports_missing_camera_image_with_next_step():
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"),
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (None, None, "bayer_rggb16")
    handler._camera_format_controller.restore_after_mtf = lambda _state: None

    result = handler.measure_mtf_callback(
        types.SimpleNamespace(measurement_mode="auto", target_edge=""),
        _make_measure_response(),
    )

    assert result.success is False
    assert "No camera image available for MTF." in result.status_message
    assert "rqt_image_view" in result.status_message
    assert "/promoc/promoc_camera/stream0/image_raw" in result.status_message


def test_measure_mtf_reports_auto_roi_failure_with_manual_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"),
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((32, 32), 1024, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_targets",
        lambda _image, *_args, **_kwargs: ("viz", [], []),
    )

    result = handler.measure_mtf_callback(
        types.SimpleNamespace(measurement_mode="auto", target_edge=""),
        _make_measure_response(),
    )

    assert result.success is False
    assert "Auto-ROI found no square or bar target." in result.status_message
    assert "measurement_mode='roi_search'" in result.status_message
    assert "direct_manual" in result.status_message


def test_measure_mtf_reports_search_roi_failure_with_retry_hint(
    monkeypatch: pytest.MonkeyPatch,
):
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"),
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((32, 32), 1024, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._select_roi_interactive = lambda _image: (
        (5, 5, 20, 20),
        np.full((20, 20), 1024, dtype=np.uint16),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_square_edge_rois_in_search_roi",
        lambda *_args, **_kwargs: [],
    )

    result = handler.measure_mtf_callback(
        types.SimpleNamespace(
            measurement_mode="roi_search",
            target_edge="",
        ),
        _make_measure_response(),
    )

    assert result.success is False
    assert "Search ROI contained no complete square target." in result.status_message
    assert "direct_manual" in result.status_message


def test_measure_mtf_exports_roi_square_search_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_dir = tmp_root / "mtf_handler_roi_square_search"
    tmp_dir.mkdir(exist_ok=True)
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(tmp_dir),
                "measurement.username": "roi_search_user",
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((64, 64), 2048, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._get_timestamp = lambda: "20260426_120000"
    handler._select_roi_interactive = lambda _image: (
        (8, 10, 32, 32),
        np.full((32, 32), 1024, dtype=np.uint16),
    )

    edge_roi = mtf_module.EdgeROI(
        image=np.full((16, 16), 2048, dtype=np.uint16),
        bbox=(11, 13, 16, 16),
        edge_direction="horizontal",
        edge_name="top",
        contrast=0.8,
        parent_center=(20, 20),
    )
    monkeypatch.setattr(
        mtf_module.RoiDetector,
        "detect_square_edge_rois_in_search_roi",
        lambda *_args, **_kwargs: [edge_roi],
    )
    monkeypatch.setattr(mtf_module, "MTF_AVG_SAMPLES", 1)

    class _FakeAnalyzer:
        compute_calls = []

        def __init__(self, config, camera_matrix=None, dist_coeffs=None):
            self.config = config

        def compute_mtf(self, image, roi=None, roi_origin=None, debug_label=None):
            type(self).compute_calls.append(
                {
                    "shape": image.shape,
                    "roi": roi,
                    "roi_origin": roi_origin,
                    "debug_label": debug_label,
                }
            )
            return MTFResult(
                mtf50=88.0,
                mtf20=60.0,
                mtf10=40.0,
                edge_angle=4.8,
                valid=True,
                sensor_nyquist=200.0,
                capture_mode="raw_green",
                capture_pixel_format=self.config.capture_pixel_format,
                capture_binning_h=self.config.capture_binning_h,
                capture_binning_v=self.config.capture_binning_v,
                capture_exposure_us=self.config.capture_exposure_us,
                capture_gain=self.config.capture_gain,
                illumination_wavelength_um=self.config.wavelength_um,
                source_encoding=self.config.source_encoding,
                g1_mtf50=87.5,
                g2_mtf50=88.5,
                g1_mtf20=59.0,
                g2_mtf20=61.0,
                g1_mtf10=39.0,
                g2_mtf10=41.0,
                g1_g2_delta_pct=1.1,
                edge_angle_method="geometric",
            )

    monkeypatch.setattr(mtf_module, "MTFAnalyzer", _FakeAnalyzer)

    request = types.SimpleNamespace(
        measurement_mode="roi_search",
        target_edge="",
        notes="roi search export",
    )

    result = handler.measure_mtf_callback(request, _make_measure_response())

    assert result.success is True
    assert result.mtf50 == 88.0
    assert len(_FakeAnalyzer.compute_calls) == 1
    assert _FakeAnalyzer.compute_calls[0]["roi_origin"] == (11, 13)
    assert _FakeAnalyzer.compute_calls[0]["debug_label"] == "top"
    assert "mode=roi_search" in result.status_message
    assert "selected=top" in result.status_message
    assert "valid_edges=1/1" in result.status_message

    csv_path = Path(result.status_message.split("summary=", 1)[1].split(",", 1)[0])
    assert csv_path.exists()
    assert csv_path.name == "summary.csv"
    assert csv_path.parent.parent.parent.name == "roi_search_user"
    assert (csv_path.parent / "selected_edge.txt").read_text(encoding="utf-8").strip() == "top"
    context_path = csv_path.parent / "context.csv"
    assert context_path.exists()

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    with open(context_path, newline="", encoding="utf-8") as csv_file:
        context_rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["edge_label"] == "top"
    assert rows[0]["edge_name"] == "top"
    assert rows[0]["selected_for_response"] == "1"
    assert len(context_rows) == 1
    assert context_rows[0]["operator"] == "roi_search_user"
    assert context_rows[0]["roi_mode"] == "roi_square_search"
    assert context_rows[0]["selected_edge_label"] == "top"
    assert context_rows[0]["valid_edge_count"] == "1"
    assert context_rows[0]["selected_measured_edge_angle_deg"] == "4.8"
    assert context_rows[0]["selected_official_sop_angle_window_ok"] == "1"
    assert context_rows[0]["selected_official_sop_reason"] == ""


def test_measure_mtf_reports_manual_roi_cancel_with_retry_hint(
    monkeypatch: pytest.MonkeyPatch,
):
    handler = MTFHandler(
        node=_Node(
            {
                "measurement.base_path": str(ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"),
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": True,
                "mtf.capture_required_raw": True,
            }
        ),
        camera_driver=object(),
    )
    handler._get_mtf_capture_image = lambda: (
        np.full((32, 32), 1024, dtype=np.uint16),
        123,
        "bayer_rggb16",
    )
    handler._camera_format_controller.switch_to_full_frame_for_mtf = (
        lambda *_args, **_kwargs: (None, None)
    )
    handler._camera_format_controller.restore_after_mtf = lambda _state: None
    handler._camera_format_controller.get_last_capture_state = lambda: {
        "values": {
            "pixel_format": "BayerRG12",
            "bin_h": 1,
            "bin_v": 1,
            "exposure_time": 100000.0,
            "gain": 0.0,
            "exposure_auto": "Off",
            "gain_auto": "Off",
            "white_balance_auto": "Off",
            "gamma_enable": False,
            "color_transform_enable": False,
        },
        "available_keys": [
            "pixel_format",
            "bin_h",
            "bin_v",
            "exposure_time",
            "gain",
            "exposure_auto",
            "gain_auto",
            "white_balance_auto",
            "gamma_enable",
            "color_transform_enable",
        ],
    }
    handler._camera_format_controller.collect_scientific_capture_mismatches = (
        lambda _state, _target=None: []
    )
    handler._select_roi_interactive = lambda _image: (None, None)

    result = handler.measure_mtf_callback(
        types.SimpleNamespace(measurement_mode="direct_manual", target_edge=""),
        _make_measure_response(),
    )

    assert result.success is False
    assert "Manual ROI selection was cancelled." in result.status_message
    assert "draw one ROI around a clean slanted edge" in result.status_message
