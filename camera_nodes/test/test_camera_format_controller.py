"""Unit tests for MTF camera format switching helpers."""

from __future__ import annotations

from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if "rcl_interfaces.msg" not in sys.modules:
    rcl_msg = types.ModuleType("rcl_interfaces.msg")

    class Parameter:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ParameterType:
        PARAMETER_NOT_SET = 0
        PARAMETER_BOOL = 1
        PARAMETER_INTEGER = 2
        PARAMETER_DOUBLE = 3
        PARAMETER_STRING = 4

    class ParameterValue:
        def __init__(self, **kwargs):
            self.type = kwargs.get("type", ParameterType.PARAMETER_NOT_SET)
            self.bool_value = kwargs.get("bool_value", False)
            self.integer_value = kwargs.get("integer_value", 0)
            self.double_value = kwargs.get("double_value", 0.0)
            self.string_value = kwargs.get("string_value", "")

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

from camera_nodes.services.camera_format import CameraFormatController  # noqa: E402


ParameterType = sys.modules["rcl_interfaces.msg"].ParameterType
ParameterValue = sys.modules["rcl_interfaces.msg"].ParameterValue


class _Logger:
    def info(self, *_args, **_kwargs):
        return None

    def warn(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


class _Client:
    def wait_for_service(self, timeout_sec=0.0):
        return True


class _Node:
    def __init__(self):
        self._logger = _Logger()

    def create_client(self, *_args, **_kwargs):
        return _Client()

    def get_logger(self):
        return self._logger

    def has_parameter(self, _name: str) -> bool:
        return False

    def get_parameter(self, _name: str):
        raise KeyError(_name)


def _param_value(value):
    if isinstance(value, bool):
        return ParameterValue(type=ParameterType.PARAMETER_BOOL, bool_value=value)
    if isinstance(value, int):
        return ParameterValue(type=ParameterType.PARAMETER_INTEGER, integer_value=value)
    if isinstance(value, float):
        return ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=value)
    return ParameterValue(type=ParameterType.PARAMETER_STRING, string_value=str(value))


def test_read_capture_state_queries_capture_specific_parameters(monkeypatch):
    controller = CameraFormatController(_Node())
    queried_names = []

    monkeypatch.setattr(
        controller,
        "_get_service_clients",
        lambda _service: {
            "set": _Client(),
            "get": _Client(),
            "set_service": "/promoc/assembly_camera/set_parameters",
            "get_service": "/promoc/assembly_camera/get_parameters",
        },
    )

    fake_values = {
        "Width": 5536,
        "Height": 3692,
        "OffsetX": 0,
        "OffsetY": 0,
        "BinningHorizontal": 1,
        "BinningVertical": 1,
        "PixelFormat": "BayerRG12",
        "ExposureTime": 100000.0,
        "Gain": 0.0,
        "ExposureAuto": "Off",
        "GainAuto": "Off",
        "BalanceWhiteAuto": "Off",
        "Gamma": 1.0,
        "GammaEnable": False,
        "ColorTransformationEnable": False,
    }

    def _fake_call_get_parameters(_client, names, timeout_s=2.0):
        queried_names.append(tuple(names))
        return types.SimpleNamespace(values=[_param_value(fake_values[name]) for name in names])

    monkeypatch.setattr(controller, "_call_get_parameters", _fake_call_get_parameters)

    state = controller.read_capture_state()

    assert state is not None
    assert any("PixelFormat" in query for query in queried_names)
    assert state["values"]["pixel_format"] == "BayerRG12"
    assert state["values"]["exposure_time"] == 100000.0
    assert state["values"]["exposure_auto"] == "Off"


def test_collect_mismatches_handles_float_string_and_bool_values():
    mismatches = CameraFormatController._collect_mismatches(
        actual={
            "gain": 0.0,
            "pixel_format": "BayerRG12",
            "gamma_enable": False,
        },
        target={
            "gain": 1.0,
            "pixel_format": "BayerRG12",
            "gamma_enable": False,
        },
        keys=["gain", "pixel_format", "gamma_enable"],
    )

    assert mismatches == ["gain=0.0!=1.0"]
