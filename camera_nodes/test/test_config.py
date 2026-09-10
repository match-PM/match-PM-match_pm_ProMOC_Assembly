"""Unit tests for camera config."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
path_str = str(ROOT / "camera_nodes")
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from camera_nodes.config import (  # noqa: E402
    declare_camera_parameters,
    load_camera_runtime_config,
)


class _Param:
    def __init__(self, value):
        self.value = value


class _Node:
    def __init__(self):
        self._params = {}
        self.warnings = []

    def declare_parameter(self, name, default):
        self._params.setdefault(name, default)

    def has_parameter(self, name):
        return name in self._params

    def get_parameter(self, name):
        return _Param(self._params[name])

    def get_logger(self):
        return self

    def warning(self, message):
        self.warnings.append(message)


def test_declare_and_load_runtime_config():
    node = _Node()
    declare_camera_parameters(node)

    # Override a couple of values to verify typed parsing.
    node._params["pixel_size_um"] = 3.45
    node._params["mtf.profile"] = "debug"
    node._params["camera.image_topic"] = "/promoc/promoc_camera/stream0/image_raw"
    node._params["autofocus.analysis_roi_width_px"] = 2000

    cfg = load_camera_runtime_config(node)
    assert cfg.core.pixel_size_um == 3.45
    assert cfg.core.image_topic == "/promoc/promoc_camera/stream0/image_raw"
    assert not hasattr(cfg.core, "use_simulator")
    assert not hasattr(cfg.core, "x_axis_node_name")
    assert cfg.autofocus.analysis_roi_width_px == 2000
    assert cfg.mtf.profile == "debug"
    assert cfg.mtf.capture_required_raw is True
    assert cfg.mtf.roi_detection_min_square_side_px == 40


def test_declare_runtime_config_uses_promoc_camera_defaults():
    node = _Node()
    declare_camera_parameters(node)

    cfg = load_camera_runtime_config(node)

    assert cfg.core.image_topic == "/promoc/promoc_camera/stream0/image_raw"
    assert cfg.core.camera_info_topic == "/promoc/promoc_camera/stream0/camera_info"
    assert cfg.core.param_set_service_primary == "/promoc/promoc_camera/set_parameters"
    assert cfg.core.param_set_service_secondary == "/promoc/promoc_camera_controller/set_parameters"
    assert cfg.core.default_pixel_format == "RGB8"
    assert cfg.autofocus.exposure_guard_s == 0.02
    assert cfg.exposure.readback_tolerance_us == 20.0
    assert cfg.auto_exposure.target_level_fraction == 0.70
    assert cfg.auto_exposure.percentile == 95.0
    assert cfg.auto_exposure.clipping_level_fraction == 0.95
    assert cfg.auto_exposure.frames_per_iteration == 3
    assert cfg.mtf.profile == "default"
    assert cfg.mtf.debug_export_dir == ""


def test_declare_runtime_config_uses_conservative_mtf_defaults():
    node = _Node()
    declare_camera_parameters(node)

    assert node._params["mtf.lsf_window_mode"] == "peak"
    assert node._params["mtf.derivative_correction_max"] == 1.15
    assert node._params["mtf.esf_smooth_mode"] == "sg"
    assert node._params["mtf.roi_detection.min_contour_area_px"] == 500
    assert node._params["mtf.roi_detection.min_square_area_px"] == 2500
    assert node._params["mtf.roi_detection.min_square_side_px"] == 40
    assert node._params["mtf.roi_detection.min_edge_roi_width_px"] == 20
    assert node._params["mtf.roi_detection.edge_roi_width_px"] == 60


def test_deprecated_parameter_removed():
    node = _Node()
    declare_camera_parameters(node)
    assert "mtf_csv_path" not in node._params
