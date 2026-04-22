# ruff: noqa: E402
"""Unit tests for linear-axis motion callbacks without adapter indirection."""

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
from linear_axis_nodes.models import OperationStateStore, OperationStatus
from linear_axis_nodes.services.motion import LinearMotionCallbacks
from linear_axis_nodes.services.validation import LinearAxisValidator


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
        self.position = 0.0

    def move_absolute(self, position: float):
        self.position = float(position)

    def move_relative(self, distance: float):
        self.position += float(distance)

    def home(self, timeout: float = 180.0):
        _ = timeout
        self.position = 0.0

    def stop(self):
        return None

    def jog_positive(self, step_size: float = 1.0):
        self.position += float(step_size)

    def jog_negative(self, step_size: float = 1.0):
        self.position -= float(step_size)

    def get_position(self):
        return self.position

    def is_moving(self):
        return False


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


def _wait_until_idle(store: OperationStateStore, timeout_s: float = 1.0) -> bool:
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        status, _ = store.get()
        if status == OperationStatus.IDLE:
            return True
        time.sleep(0.01)
    return False


def test_linear_motion_callbacks_absolute_relative_and_stop():
    logger = _DummyLogger()
    driver = _FakeDriver()
    config = _config()
    store = OperationStateStore()
    validator = LinearAxisValidator(config, logger)
    callbacks = LinearMotionCallbacks(
        logger,
        driver=driver,
        validator=validator,
        state_store=store,
        config=config,
    )

    abs_req = SimpleNamespace(axis_position=10.0)
    abs_res = SimpleNamespace(success=False, status_message="")
    abs_result = callbacks.callback_move_absolute(
        abs_req, abs_res, other_axis_position=0.0
    )
    assert abs_result.success is True
    assert _wait_until_idle(store)

    rel_req = SimpleNamespace(axis_position=2.0)
    rel_res = SimpleNamespace(success=False, status_message="")
    rel_result = callbacks.callback_move_relative(
        rel_req, rel_res, other_axis_position=0.0
    )
    assert rel_result.success is True
    assert _wait_until_idle(store)

    stop_req = SimpleNamespace()
    stop_res = SimpleNamespace(success=False, status_message="")
    stop_result = callbacks.callback_stop(stop_req, stop_res)
    assert stop_result.success is True


def test_linear_motion_callbacks_home_and_jog():
    logger = _DummyLogger()
    driver = _FakeDriver()
    config = _config()
    store = OperationStateStore()
    validator = LinearAxisValidator(config, logger)
    callbacks = LinearMotionCallbacks(
        logger,
        driver=driver,
        validator=validator,
        state_store=store,
        config=config,
    )

    store.set(OperationStatus.ERROR, "previous failure")

    home_req = SimpleNamespace()
    home_res = SimpleNamespace(success=False, status_message="")
    home_result = callbacks.callback_home(home_req, home_res)
    assert home_result.success is True
    assert _wait_until_idle(store)

    jog_req = SimpleNamespace(step_size=1.5)
    jog_res = SimpleNamespace(success=False, final_position=-1.0, status_message="")
    jog_result = callbacks.callback_jog_axis(jog_req, jog_res)
    assert jog_result.success is True
    assert jog_result.final_position >= 0.0
