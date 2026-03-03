"""Smoke tests for MTF handler wiring."""

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


def test_mtf_handler_builds_default_config():
    handler = MTFHandler(node=_Node({}), camera_driver=object())
    cfg = handler._build_mtf_config(2.4, 2.0, 10.0, auto_roi=True)

    assert cfg.pixel_size_um == 2.4
    assert cfg.min_edge_angle == 2.0
    assert cfg.max_edge_angle == 10.0
