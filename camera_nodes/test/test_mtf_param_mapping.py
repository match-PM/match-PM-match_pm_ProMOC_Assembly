"""Unit tests for camera MTF config mapping behavior."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import types


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
    rcl_srv.SetParameters = _SrvType
    sys.modules["rcl_interfaces.srv"] = rcl_srv
if "rcl_interfaces" not in sys.modules:
    rcl_pkg = types.ModuleType("rcl_interfaces")
    rcl_pkg.msg = sys.modules["rcl_interfaces.msg"]
    rcl_pkg.srv = sys.modules["rcl_interfaces.srv"]
    sys.modules["rcl_interfaces"] = rcl_pkg

from camera_nodes.algorithms.mtf_analysis import MTFConfig  # noqa: E402
from camera_nodes.handlers.mtf_handler import MTFHandler  # noqa: E402


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


def _callbacks(params: dict) -> MTFHandler:
    return MTFHandler(node=_Node(params), camera_driver=object())


def test_build_mtf_config_mapping_applies_and_respects_auto_roi_override():
    with tempfile.TemporaryDirectory() as tmp_dir:
        callbacks = _callbacks(
            {
                "mtf.debug_export_dir": tmp_dir,
                "mtf.debug_export_prefix": "run",
                "mtf.debug_export_csv": True,
                "mtf.debug_export_png": False,
                "mtf.lsf_window_mode": "peak",
                "mtf.lsf_peak_window_size": 13,
                "mtf.derivative_mode": "iso",
                "mtf.apply_derivative_correction": True,
                "mtf.derivative_correction_max": 0.5,
                "mtf.apply_angle_correction": True,
                "mtf.esf_smooth_mode": "sg",
                "mtf.esf_sg_window": 9,
                "mtf.esf_sg_poly": 2,
                "mtf.edge_validation_mode": "warn",
                "mtf.edge_validation_percentile": 85.0,
                "mtf.edge_validation_min_points": 25,
                "mtf.edge_validation_only_auto": True,
                "mtf.clip_to_nyquist": True,
                "mtf.export_dual_curves": False,
                "mtf.clip_max": 0.9,
                "mtf.warn_threshold": 1.15,
                "mtf.profile": "default",
            }
        )
        config = callbacks._build_mtf_config(2.4, 2.0, 10.0, auto_roi=False)

    assert config.debug_export_dir == tmp_dir
    assert config.debug_export_prefix == "run"
    assert config.lsf_window_mode == "peak"
    assert config.lsf_peak_window_size == 13
    assert config.derivative_mode == "iso"
    assert config.derivative_correction_max == 0.5
    assert config.esf_sg_window == 9
    assert config.edge_validation_percentile == 85.0
    assert config.edge_validation_min_points == 25
    # mtf.edge_validation_only_auto forces off for non-auto mode.
    assert config.edge_validation_mode == "off"
    assert config.mtf_clip_max == 0.9
    assert config.mtf_warn_threshold == 1.15


def test_build_mtf_config_mapping_ignores_invalid_casts_and_applies_profile():
    default_cfg = MTFConfig(pixel_size_um=2.4, min_edge_angle=2.0, max_edge_angle=10.0)
    callbacks = _callbacks(
        {
            "mtf.lsf_peak_window_size": "not-an-int",
            "mtf.derivative_correction_max": "bad",
            "mtf.esf_sg_window": "bad",
            "mtf.edge_validation_percentile": "bad",
            "mtf.profile": "scientific",
        }
    )
    config = callbacks._build_mtf_config(2.4, 2.0, 10.0, auto_roi=True)

    assert config.lsf_peak_window_size == default_cfg.lsf_peak_window_size
    assert config.derivative_correction_max == default_cfg.derivative_correction_max
    assert config.esf_sg_window == default_cfg.esf_sg_window
    assert config.edge_validation_percentile == default_cfg.edge_validation_percentile
    # Profile applied after parameter mapping.
    assert config.derivative_mode == "iso"
    assert config.apply_derivative_correction is True

