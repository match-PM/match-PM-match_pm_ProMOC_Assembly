# ruff: noqa: E402
"""Focused behavioral tests for the simplified planar-motor runtime."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("planar_motor_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from planar_motor_nodes.config import MoverNodeConfig
from planar_motor_nodes.drivers.mock import MockPlanarMotorDriver
from planar_motor_nodes.services.control import ControlCallbacks
from planar_motor_nodes.services.motion import MotionCallbacks
from planar_motor_nodes.services.status import MoverUtils
from promoc_core import error_codes


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


def _config() -> MoverNodeConfig:
    return MoverNodeConfig(
        driver_mode="mock",
        xbot_id=0,
        publish_rate=10.0,
        pmc_ip="mock://controller",
        auto_activate=True,
        movement_timeout=1.0,
        mock_xbot_count=1,
        xy_tolerance=0.001,
        six_d_tolerance=0.001,
        x_min=0.055,
        x_max=0.420,
        y_min=0.055,
        y_max=0.180,
        z_min=0.0,
        z_max=0.004,
        default_xy_vel=0.05,
        default_xy_max_accel=0.2,
        default_z_vel=0.01,
        default_z_max_accel=0.05,
        default_rx_vel=0.1,
        default_ry_vel=0.1,
        default_rz_vel=0.2,
    )


def _runtime():
    logger = _DummyLogger()
    driver = MockPlanarMotorDriver(logger, mock_xbot_count=1)
    runtime = MoverUtils(logger, driver, _config())
    runtime.connect_and_prepare()
    return logger, driver, runtime


def test_absolute_relative_and_rotary_motion_update_mock_state():
    logger, driver, runtime = _runtime()
    motion = MotionCallbacks(logger, driver, runtime, _config())

    linear_res = SimpleNamespace(success=False, error_code=0, status_message="")
    linear_req = SimpleNamespace(xbot_id=0, x_pos=150.0, y_pos=130.0)
    linear = motion.callback_linear_motion_si(linear_req, linear_res)
    assert linear.success is True
    pose = runtime.get_current_position(0)
    assert round(pose.x, 3) == 0.150
    assert round(pose.y, 3) == 0.130

    arc_res = SimpleNamespace(success=False, error_code=0, status_message="")
    arc_req = SimpleNamespace(
        xbot_id=0,
        target_x=10.0,
        target_y=-5.0,
        radius=20.0,
        max_speed=50.0,
        max_accel=100.0,
        arc_mode=0,
        arc_type=0,
        arc_direction=1,
        pos_mode=1,
        final_speed=0.0,
        angle_degrees=90.0,
    )
    arc = motion.callback_arc_motion_si(arc_req, arc_res)
    assert arc.success is True
    pose = runtime.get_current_position(0)
    assert round(pose.x, 3) == 0.160
    assert round(pose.y, 3) == 0.125

    rotary_res = SimpleNamespace(success=False, error_code=0, status_message="")
    rotary_req = SimpleNamespace(
        xbot_id=0,
        target_rz=90.0,
        max_rz_speed=90.0,
        max_accel_rz=180.0,
        rot_mode=0,
    )
    rotary = motion.callback_rotary_motion(rotary_req, rotary_res)
    assert rotary.success is True
    pose = runtime.get_current_position(0)
    assert round(pose.rz, 3) == 1.571


def test_unknown_xbot_is_rejected():
    logger, driver, runtime = _runtime()
    motion = MotionCallbacks(logger, driver, runtime, _config())
    response = SimpleNamespace(success=False, error_code=0, status_message="")
    request = SimpleNamespace(xbot_id=9, x_pos=150.0, y_pos=130.0)

    result = motion.callback_linear_motion_si(request, response)

    assert result.success is False
    assert result.error_code == error_codes.XBOT_NOT_FOUND


def test_unavailable_position_is_rejected_instead_of_fabricated():
    logger, driver, runtime = _runtime()
    motion = MotionCallbacks(logger, driver, runtime, _config())
    original_get_snapshot = driver.get_snapshot

    def _without_pose(xbot_id):
        snapshot = original_get_snapshot(xbot_id)
        return snapshot.__class__(
            xbot_id=snapshot.xbot_id,
            pose=None,
            raw_state=snapshot.raw_state,
            device_state=snapshot.device_state,
            active=snapshot.active,
            levitated=snapshot.levitated,
            busy=snapshot.busy,
            error_code=snapshot.error_code,
            message=snapshot.message,
        )

    driver.get_snapshot = _without_pose
    response = SimpleNamespace(success=False, error_code=0, status_message="")
    request = SimpleNamespace(
        xbot_id=0,
        x_pos=150.0,
        y_pos=130.0,
        z_pos=-999999.0,
        rx_pos=-999999.0,
        ry_pos=-999999.0,
        rz_pos=-999999.0,
    )

    result = motion.callback_six_d_motion(request, response)

    assert result.success is False
    assert result.error_code == error_codes.POSITION_UNAVAILABLE


def test_stop_updates_mock_status():
    logger, driver, runtime = _runtime()
    control = ControlCallbacks(logger, driver, runtime, _config())

    stop_request = SimpleNamespace(xbot_id=0)
    stop_response = SimpleNamespace(success=False, error_code=0, status_message="")
    stop = control.callback_stop_motion(stop_request, stop_response)

    assert stop.success is True
    assert stop.error_code == error_codes.STOP_REQUESTED
    assert runtime.get_snapshot(0).device_state.name == "STOPPED"


def test_status_message_populates_shared_device_status():
    logger, _, runtime = _runtime()
    message = runtime.build_info_message(0)
    assert message is not None
    assert message.device_status.state == int(message.device_status.state)
    assert message.device_status.error_code == error_codes.SUCCESS
    assert message.xbot_state == "XBOT_IDLE"
