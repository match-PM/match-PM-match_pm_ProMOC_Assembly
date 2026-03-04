# ruff: noqa: E402
"""Regression tests for linear-axis service callback facade."""

from __future__ import annotations

from pathlib import Path
import sys
import time
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("linear_axis_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from linear_axis_nodes.config import LTS300NodeConfig
from linear_axis_nodes.services import ServiceHandlers
from linear_axis_nodes.services.status import OperationStatus


class _DummyLogger:
    def debug(self, *args, **kwargs):
        _ = args, kwargs

    def info(self, *args, **kwargs):
        _ = args, kwargs

    def warning(self, *args, **kwargs):
        _ = args, kwargs

    def warn(self, *args, **kwargs):
        _ = args, kwargs

    def error(self, *args, **kwargs):
        _ = args, kwargs


class _FakeDriver:
    def __init__(self):
        self._position = 0.0
        self._moving = False
        self._velocity = (0.0, 1.0, 5.0)

    def move_absolute(self, position):
        self._moving = True
        self._position = float(position)
        self._moving = False

    def move_relative(self, distance):
        self._moving = True
        self._position += float(distance)
        self._moving = False

    def home(self, timeout=180.0):
        _ = timeout
        self._moving = True
        self._position = 0.0
        self._moving = False

    def stop(self):
        self._moving = False

    def jog_positive(self, step_size=1.0):
        self._position += float(step_size)

    def jog_negative(self, step_size=1.0):
        self._position -= float(step_size)

    def get_position(self):
        return self._position

    def is_moving(self):
        return self._moving

    def get_velocity_parameters(self):
        return self._velocity

    def set_velocity_parameters(
        self, min_velocity=None, acceleration=None, max_velocity=None
    ):
        current = list(self._velocity)
        if min_velocity is not None:
            current[0] = min_velocity
        if acceleration is not None:
            current[1] = acceleration
        if max_velocity is not None:
            current[2] = max_velocity
        self._velocity = tuple(current)
        return self._velocity


class _FakeInterface:
    def __init__(self):
        self.driver = _FakeDriver()
        self.disconnected = False

    def disconnect(self):
        self.disconnected = True


def _config() -> LTS300NodeConfig:
    return LTS300NodeConfig(
        use_sim_time=True,
        serial_port="sim",
        serial_number="SIM",
        collision_threshold=300.0,
        max_position=300.0,
        min_position=0.0,
        max_single_move=300.0,
        homing_timeout=5.0,
        velocity_conversion_factor=1.0,
        position_poll_interval_s=0.1,
    )


def _wait_until_idle(callbacks: ServiceHandlers, timeout_s: float = 1.0):
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        status, _ = callbacks.get_operation_status()
        if status == OperationStatus.IDLE:
            return True
        time.sleep(0.01)
    return False


def test_linear_service_callbacks_motion_and_admin_paths():
    interface = _FakeInterface()
    callbacks = ServiceHandlers(_DummyLogger(), interface, _config())

    abs_req = SimpleNamespace(axis_position=10.0)
    abs_res = SimpleNamespace(success=False, status_message="")
    abs_result = callbacks.callback_move_absolute(
        abs_req, abs_res, other_axis_position=0.0
    )
    assert abs_result.success is True
    assert _wait_until_idle(callbacks)

    rel_req = SimpleNamespace(axis_position=5.0)
    rel_res = SimpleNamespace(success=False, status_message="")
    rel_result = callbacks.callback_move_relative(
        rel_req, rel_res, other_axis_position=0.0
    )
    assert rel_result.success is True
    assert _wait_until_idle(callbacks)

    home_req = SimpleNamespace()
    home_res = SimpleNamespace(success=False, status_message="")
    home_result = callbacks.callback_home(home_req, home_res)
    assert home_result.success is True
    assert _wait_until_idle(callbacks)

    jog_req = SimpleNamespace(step_size=2.0)
    jog_res = SimpleNamespace(success=False, final_position=-1.0, status_message="")
    jog_result = callbacks.callback_jog_axis(jog_req, jog_res)
    assert jog_result.success is True

    stop_req = SimpleNamespace()
    stop_res = SimpleNamespace(success=False, status_message="")
    stop_result = callbacks.callback_stop(stop_req, stop_res)
    assert stop_result.success is True

    emergency_req = SimpleNamespace()
    emergency_res = SimpleNamespace(success=False, was_moving=False, status_message="")
    emergency_result = callbacks.callback_emergency_stop(emergency_req, emergency_res)
    assert emergency_result.success is True

    vel_set_req = SimpleNamespace(min_velocity=0.1, acceleration=0.2, max_velocity=0.3)
    vel_set_res = SimpleNamespace(
        success=False,
        status_message="",
        actual_min_velocity=0.0,
        actual_acceleration=0.0,
        actual_max_velocity=0.0,
    )
    vel_set_result = callbacks.callback_set_velocity_parameters(
        vel_set_req, vel_set_res
    )
    assert vel_set_result.success is True

    vel_get_req = SimpleNamespace()
    vel_get_res = SimpleNamespace(
        success=False,
        status_message="",
        min_velocity=0.0,
        acceleration=0.0,
        max_velocity=0.0,
    )
    vel_get_result = callbacks.callback_get_velocity_parameters(
        vel_get_req, vel_get_res
    )
    assert vel_get_result.success is True

    status_req = SimpleNamespace()
    status_res = SimpleNamespace(success=False, operation_status="", status_message="")
    status_result = callbacks.callback_get_operation_status(status_req, status_res)
    assert status_result.success is True

    position_req = SimpleNamespace()
    position_res = SimpleNamespace(success=False, axis_position=0.0, status_message="")
    position_result = callbacks.callback_get_position(position_req, position_res)
    assert position_result.success is True

    shutdown_req = SimpleNamespace()
    shutdown_res = SimpleNamespace(success=False, status_message="")
    shutdown_result = callbacks.callback_shutdown(shutdown_req, shutdown_res)
    assert shutdown_result.success is True
    assert interface.disconnected is True
