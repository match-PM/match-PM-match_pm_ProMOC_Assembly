# ruff: noqa: E402
"""Controller tests for the unified linear-axis runtime."""

from __future__ import annotations

from pathlib import Path
import sys
import threading
import time
import types

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("linear_axis_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

if "promoc_assembly_interfaces" not in sys.modules:
    pkg = types.ModuleType("promoc_assembly_interfaces")
    msg_mod = types.ModuleType("promoc_assembly_interfaces.msg")
    srv_mod = types.ModuleType("promoc_assembly_interfaces.srv")

    class _DeviceStatus:
        pass

    msg_mod.DeviceStatus = _DeviceStatus
    for name in (
        "EmergencyStop",
        "GetOperationStatus",
        "GetPosition",
        "GetVelocityParameters",
        "Home",
        "JogAxis",
        "MoveAbsolute",
        "MoveRelative",
        "SetVelocityParameters",
        "ShutdownLinearAxis",
        "Stop",
    ):
        setattr(srv_mod, name, type(name, (), {}))

    pkg.msg = msg_mod
    pkg.srv = srv_mod
    sys.modules["promoc_assembly_interfaces"] = pkg
    sys.modules["promoc_assembly_interfaces.msg"] = msg_mod
    sys.modules["promoc_assembly_interfaces.srv"] = srv_mod

from linear_axis_nodes.config import LinearAxisConfig
from linear_axis_nodes.drivers.hardware import ThorlabsLTS300Driver
from linear_axis_nodes.node import AxisController, AxisOperationError
from promoc_core import error_codes
from promoc_core.promoc_exceptions import MovementTimeoutError
from promoc_core.status import AxisState


class _DummyLogger:
    def debug(self, *args, **kwargs):
        _ = args, kwargs

    def info(self, *args, **kwargs):
        _ = args, kwargs

    def warn(self, *args, **kwargs):
        _ = args, kwargs

    def warning(self, *args, **kwargs):
        _ = args, kwargs

    def error(self, *args, **kwargs):
        _ = args, kwargs


class _FakeDriver:
    def __init__(self, axis_id: str = "x", move_delay_s: float = 0.2):
        self.axis_id = axis_id
        self.connected = False
        self.position = 0.0
        self.move_delay_s = move_delay_s
        self.stop_requested = False
        self.velocity = (0.0, 1.0, 5.0)
        self.moving = False
        self.jog_calls = []
        self.move_relative_calls = []

    def connect(self, port: str = None) -> bool:
        _ = port
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False
        self.moving = False

    def move_absolute(self, position: float, timeout: float | None = None) -> None:
        self._run_move(position, timeout)

    def move_relative(self, distance: float, timeout: float | None = None) -> None:
        self.move_relative_calls.append(distance)
        self._run_move(self.position + distance, timeout)

    def jog(self, step_size: float, timeout: float | None = None) -> None:
        self.jog_calls.append(step_size)
        self._run_move(self.position + step_size, timeout)

    def home(self, timeout: float = 180.0) -> None:
        self._run_move(0.0, timeout)

    def stop(self) -> None:
        self.stop_requested = True
        self.moving = False

    def get_position(self) -> float:
        return self.position

    def is_moving(self) -> bool:
        return self.moving

    def get_serial_number(self) -> str:
        return f"SIM-{self.axis_id.upper()}"

    def get_velocity_parameters(self):
        return self.velocity

    def set_velocity_parameters(self, min_velocity=None, acceleration=None, max_velocity=None):
        current = list(self.velocity)
        if min_velocity is not None:
            current[0] = min_velocity
        if acceleration is not None:
            current[1] = acceleration
        if max_velocity is not None:
            current[2] = max_velocity
        self.velocity = tuple(current)
        return self.velocity

    def _run_move(self, target: float, timeout: float | None) -> None:
        self.moving = True
        self.stop_requested = False
        start = time.monotonic()
        while time.monotonic() - start < self.move_delay_s:
            if self.stop_requested:
                self.moving = False
                return
            if timeout is not None and time.monotonic() - start > timeout:
                self.moving = False
                raise MovementTimeoutError("timed out")
            time.sleep(0.01)
        self.position = target
        self.moving = False


class _FakeThorlabsDevice:
    def __init__(self):
        self.setup_jog_calls = []
        self.jog_calls = []
        self.position = 0

    def setup_jog(self, **kwargs):
        self.setup_jog_calls.append(kwargs)

    def jog(self, direction, kind):
        self.jog_calls.append((direction, kind))

    def is_moving(self):
        return False

    def get_position(self):
        return self.position


def _config(**overrides) -> LinearAxisConfig:
    values = {
        "axis_id": "x",
        "driver_mode": "mock",
        "serial_number": "SIM-X",
        "serial_port": "",
        "min_position": 0.0,
        "max_position": 300.0,
        "default_velocity": 5.0,
        "default_acceleration": 1.0,
        "movement_timeout": 1.0,
        "homing_timeout": 1.0,
        "state_publish_rate_hz": 10.0,
    }
    values.update(overrides)
    return LinearAxisConfig(**values)


class _Param:
    def __init__(self, value):
        self.value = value


class _FakeNode:
    def __init__(self, overrides=None):
        self.values = dict(overrides or {})

    def has_parameter(self, name):
        return name in self.values

    def declare_parameter(self, name, default):
        self.values.setdefault(name, default)

    def get_parameter(self, name):
        return _Param(self.values[name])


def _controller(monkeypatch, *, axis_id: str = "x", move_delay_s: float = 0.2, **cfg):
    driver = _FakeDriver(axis_id=axis_id, move_delay_s=move_delay_s)
    monkeypatch.setattr(
        AxisController,
        "_create_driver",
        lambda self: driver,
    )
    return AxisController(_DummyLogger(), _config(axis_id=axis_id, **cfg)), driver


def test_config_from_node_normalizes_axis_and_driver_mode():
    config = LinearAxisConfig.from_node(
        _FakeNode({"axis_id": " X ", "driver_mode": " MOCK "})
    )

    assert config.axis_id == "x"
    assert config.driver_mode == "mock"


def test_movement_before_homing_is_rejected(monkeypatch):
    controller, _ = _controller(monkeypatch)

    with pytest.raises(AxisOperationError) as exc_info:
        controller.move_absolute(10.0)

    assert exc_info.value.error_code == error_codes.DEVICE_UNHOMED


def test_absolute_and_relative_soft_limits_are_rejected(monkeypatch):
    controller, _ = _controller(monkeypatch)
    controller.home()

    with pytest.raises(AxisOperationError) as abs_exc:
        controller.move_absolute(301.0)
    assert abs_exc.value.error_code == error_codes.TARGET_OUT_OF_RANGE

    with pytest.raises(AxisOperationError) as rel_exc:
        controller.move_relative(-1.0)
    assert rel_exc.value.error_code == error_codes.TARGET_OUT_OF_RANGE


def test_invalid_velocity_and_acceleration_are_rejected(monkeypatch):
    controller, _ = _controller(monkeypatch)

    with pytest.raises(AxisOperationError) as vel_exc:
        controller.set_velocity_parameters(0.0, 1.0, 0.0)
    assert vel_exc.value.error_code == error_codes.INVALID_PARAMETER

    with pytest.raises(AxisOperationError) as accel_exc:
        controller.set_velocity_parameters(0.0, 0.0, 1.0)
    assert accel_exc.value.error_code == error_codes.INVALID_PARAMETER


def test_second_movement_while_busy_is_rejected(monkeypatch):
    controller, _ = _controller(monkeypatch, move_delay_s=0.3)
    controller.home()

    worker = threading.Thread(target=controller.move_absolute, args=(20.0,))
    worker.start()
    time.sleep(0.05)

    with pytest.raises(AxisOperationError) as exc_info:
        controller.move_relative(5.0)

    worker.join()
    assert exc_info.value.error_code == error_codes.DEVICE_BUSY


def test_stop_remains_callable_during_movement(monkeypatch):
    controller, _ = _controller(monkeypatch, move_delay_s=0.3)
    controller.home()
    outcome = {}

    def _run_move():
        try:
            controller.move_absolute(25.0)
            outcome["result"] = "completed"
        except AxisOperationError as exc:
            outcome["error_code"] = exc.error_code

    worker = threading.Thread(target=_run_move)
    worker.start()
    time.sleep(0.05)

    was_moving = controller.stop()
    worker.join()

    assert was_moving is True
    assert outcome["error_code"] == error_codes.STOP_REQUESTED


def test_mock_movement_reaches_requested_target(monkeypatch):
    controller, _ = _controller(monkeypatch)
    controller.home()

    final_position = controller.move_absolute(42.5)

    assert final_position == pytest.approx(42.5)
    assert controller.snapshot().axis_state == AxisState.HOMED


def test_jog_uses_driver_jog_not_relative_move(monkeypatch):
    controller, driver = _controller(monkeypatch)
    controller.home()

    final_position = controller.jog(2.5)

    assert final_position == pytest.approx(2.5)
    assert driver.jog_calls == [2.5]
    assert driver.move_relative_calls == []


def test_hardware_jog_uses_builtin_kinesis_jog():
    device = _FakeThorlabsDevice()
    driver = ThorlabsLTS300Driver(_DummyLogger())
    driver.connected = True
    driver.device = device

    driver.jog(-2.5, timeout=0.1)

    assert device.setup_jog_calls == [
        {
            "mode": "step",
            "step_size": 1024000,
            "stop_mode": "profiled",
            "scale": False,
        }
    ]
    assert device.jog_calls == [("-", "builtin")]


def test_movement_timeout_returns_correct_error(monkeypatch):
    controller, _ = _controller(monkeypatch, move_delay_s=0.3, movement_timeout=0.05)
    controller.home()

    with pytest.raises(AxisOperationError) as exc_info:
        controller.move_absolute(50.0)

    assert exc_info.value.error_code == error_codes.MOVEMENT_TIMEOUT
