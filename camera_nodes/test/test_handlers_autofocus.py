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

from camera_nodes.services.handlers.autofocus import AutofocusHandler  # noqa: E402


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


def test_autofocus_handler_builds_focus_profile():
    handler = AutofocusHandler(_Node({}), camera_driver=object())
    profile = handler._build_focus_profile(_Request())

    assert isinstance(profile, dict)
    assert "scan_speed_mm_s" in profile
    assert profile["scan_speed_mm_s"] > 0.0
