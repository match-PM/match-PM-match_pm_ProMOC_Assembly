"""Unit tests for fly-over peak analysis helpers."""

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
    sys.modules["cv2"] = types.SimpleNamespace()
srv_mod = types.ModuleType("promoc_assembly_interfaces.srv")


class _SrvType:
    class Request:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


srv_mod.GetVelocityParameters = _SrvType
srv_mod.SetVelocityParameters = _SrvType
srv_mod.GetOperationStatus = _SrvType
srv_mod.MoveAbsolute = _SrvType
sys.modules["promoc_assembly_interfaces.srv"] = srv_mod
if "promoc_assembly_interfaces" not in sys.modules:
    pkg_mod = types.ModuleType("promoc_assembly_interfaces")
    pkg_mod.srv = srv_mod
    sys.modules["promoc_assembly_interfaces"] = pkg_mod

from camera_nodes.handlers.fly_over import FlyOverDetector  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


class _Logger:
    def info(self, *_args, **_kwargs):
        return None

    def warn(self, *_args, **_kwargs):
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


def _detector(params: dict) -> FlyOverDetector:
    node = _Node(params)
    return FlyOverDetector(
        node=node,
        get_latest_cv_image=lambda: (None, None),
        get_center_roi=lambda image, _size: image,
        wait_for_axis_idle=lambda _clients: None,
        get_position=lambda _clients: 0.0,
    )


def test_analyze_peak_returns_window_around_synthetic_peak():
    params = {
        "autofocus.fly_over.smooth_window_samples": 5,
        "autofocus.fly_over.baseline_percentile": 20.0,
        "autofocus.fly_over.snr_threshold": 2.5,
    }
    detector = _detector(params)

    positions = np.linspace(0.0, 10.0, 51)
    center = 5.0
    sigma = 0.8
    values = 10.0 + (70.0 * np.exp(-0.5 * ((positions - center) / sigma) ** 2))
    scan_data = list(zip(positions.tolist(), values.tolist()))

    result = detector._analyze_peak(
        scan_data=scan_data,
        start_pos=0.0,
        end_pos=10.0,
        peak_ratio=0.5,
        margin=1.0,
        backtrack=1.0,
        threshold=0.0,
    )

    assert result.peak_start is not None
    assert result.peak_end is not None
    assert result.peak_start < center < result.peak_end
    assert result.max_stddev > 50.0


def test_analyze_peak_handles_empty_scan_data():
    detector = _detector({})
    result = detector._analyze_peak(
        scan_data=[],
        start_pos=0.0,
        end_pos=10.0,
        peak_ratio=0.5,
        margin=1.0,
        backtrack=1.0,
        threshold=0.0,
    )

    assert result.peak_start is None
    assert result.peak_end is None
    assert result.max_stddev == 0.0
