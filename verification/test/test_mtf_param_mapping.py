"""Unit tests for verification MTF parameter mapping."""

from __future__ import annotations

from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "verification", ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace()
if "camera_nodes.plotting" not in sys.modules:
    mod = types.ModuleType("camera_nodes.plotting")
    mod.VerificationPlotter = object
    sys.modules["camera_nodes.plotting"] = mod
srv_mod = types.ModuleType("promoc_assembly_interfaces.srv")


class _SrvType:
    class Request:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


srv_mod.GetPosition = _SrvType
sys.modules["promoc_assembly_interfaces.srv"] = srv_mod
if "promoc_assembly_interfaces" not in sys.modules:
    pkg_mod = types.ModuleType("promoc_assembly_interfaces")
    pkg_mod.srv = srv_mod
    sys.modules["promoc_assembly_interfaces"] = pkg_mod

from camera_nodes.algorithms.mtf_analysis import MTFConfig  # noqa: E402
from verification.callbacks.base import ScientificVerificationBase  # noqa: E402
from verification.callbacks.mtf import MTFVerificationCallbacks  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


class _Logger:
    def info(self, *_args, **_kwargs):
        return None

    def warn(self, *_args, **_kwargs):
        return None


class _Harness(ScientificVerificationBase, MTFVerificationCallbacks):
    def __init__(self, params: dict):
        self._params = dict(params)
        self._logger = _Logger()

    def has_parameter(self, name: str) -> bool:
        return name in self._params

    def get_parameter(self, name: str):
        return _Param(self._params[name])

    def get_logger(self):
        return self._logger


def test_apply_mtf_param_overrides_maps_valid_values_and_ignores_invalid():
    cfg_default = MTFConfig(pixel_size_um=2.4, min_edge_angle=2.0)
    callbacks = _Harness(
        {
            "mtf.lsf_window_mode": "peak",
            "mtf.lsf_peak_window_size": "bad-int",
            "mtf.derivative_mode": "iso",
            "mtf.derivative_correction_max": "bad-float",
            "mtf.esf_sg_window": 7,
            "mtf.edge_validation_percentile": 88.0,
            "mtf.debug_export_dir": "",
        }
    )
    cfg = MTFConfig(pixel_size_um=2.4, min_edge_angle=2.0)
    callbacks._apply_mtf_param_overrides(cfg, debug_dir=None, force_debug=False)

    assert cfg.lsf_window_mode == "peak"
    assert cfg.lsf_peak_window_size == cfg_default.lsf_peak_window_size
    assert cfg.derivative_mode == "iso"
    assert cfg.derivative_correction_max == cfg_default.derivative_correction_max
    assert cfg.esf_sg_window == 7
    assert cfg.edge_validation_percentile == 88.0


def test_apply_mtf_param_overrides_force_debug_takes_precedence():
    callbacks = _Harness(
        {
            "mtf.debug_export_prefix": "abc",
            "mtf.debug_export_csv": False,
            "mtf.debug_export_png": False,
        }
    )
    cfg = MTFConfig(pixel_size_um=2.4, min_edge_angle=2.0)
    callbacks._apply_mtf_param_overrides(cfg, debug_dir="tmp_debug", force_debug=True)

    assert cfg.debug_export_dir == "tmp_debug"
    assert cfg.debug_export_prefix == "abc"
    assert cfg.debug_export_csv is True
    assert cfg.debug_export_png is True
