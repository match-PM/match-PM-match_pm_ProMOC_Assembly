# ruff: noqa: E402
"""Unit tests for planar motion/control callbacks without adapter indirection."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("planar_motor_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from planar_motor_nodes.services.control import ControlCallbacks
from planar_motor_nodes.services.motion import MotionCallbacks
from promoc_core.motion import MotionStatus


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


class _FakeBot:
    def __init__(self):
        self.stopped_actor = None

    def linear_motion_si(self, xbot_id, x, y, xy_vel, xy_accel):
        _ = xbot_id, x, y, xy_vel, xy_accel
        return 0.01

    def six_d_of_motion_si(
        self,
        xbot_id,
        x,
        y,
        z,
        rx,
        ry,
        rz,
        xy_vel,
        xy_accel,
        z_vel,
        rx_vel,
        ry_vel,
        rz_vel,
    ):
        _ = (
            xbot_id,
            x,
            y,
            z,
            rx,
            ry,
            rz,
            xy_vel,
            xy_accel,
            z_vel,
            rx_vel,
            ry_vel,
            rz_vel,
        )
        return 0.01

    def rotary_motion(self, xbot_id, target_rz, max_speed, max_accel, cmd_lb, rot_mode):
        _ = xbot_id, target_rz, max_speed, max_accel, cmd_lb, rot_mode
        return 0.01

    def arc_motion_si(
        self,
        xbot_id,
        target_x,
        target_y,
        radius_m,
        max_speed,
        max_accel,
        cmd_lb,
        arc_mode,
        arc_type,
        arc_direction,
        pos_mode,
        final_speed,
        angle_rad,
    ):
        _ = (
            xbot_id,
            target_x,
            target_y,
            radius_m,
            max_speed,
            max_accel,
            cmd_lb,
            arc_mode,
            arc_type,
            arc_direction,
            pos_mode,
            final_speed,
            angle_rad,
        )
        return 0.01

    def stop_motion(self, xbot_id):
        self.stopped_actor = xbot_id

    def activate_xbots(self):
        return None

    def deactivate_xbots(self):
        return None

    def levitation_command(self, xbot_id, command):
        _ = xbot_id, command


class _FakePMC:
    def __init__(self):
        self.bot = _FakeBot()
        self.status = {"source": "test", "is_mock": True}


class _FakeMoverUtils:
    def __init__(self):
        self.speed_params = {
            "xy_vel": 0.05,
            "xy_max_accel": 0.2,
            "z_vel": 0.01,
            "z_max_accel": 0.05,
            "rx_vel": 0.1,
            "ry_vel": 0.1,
            "rz_vel": 0.1,
        }

    def get_current_position(self, xbot_id=0):
        _ = xbot_id
        return [0.12, 0.12, 0.001, 0.0, 0.0, 0.0]

    def get_xbot_state_string(self, xbot_id=0):
        _ = xbot_id
        return "XBOT_IDLE"

    def mm_to_m(self, value):
        return float(value) / 1000.0

    def deg_to_rad(self, value):
        import math

        return math.radians(float(value))

    def get_speed_params(self, xbot_id=0):
        _ = xbot_id
        return dict(self.speed_params)

    def set_speed_params(self, xbot_id, params):
        _ = xbot_id
        self.speed_params = dict(params)

    def is_position_in_bounds(self, x, y, z):
        _ = x, y, z
        return True

    def wait_for_motion_completion(
        self,
        xbot_id,
        target_position,
        position_tolerance,
        max_wait_time,
    ):
        _ = xbot_id, target_position, position_tolerance, max_wait_time
        return MotionStatus.COMPLETED


def _config():
    return SimpleNamespace(
        xy_tolerance=0.001,
        six_d_tolerance=0.001,
        x_min=0.055,
        x_max=0.420,
        y_min=0.055,
        y_max=0.180,
        z_min=0.0,
        z_max=0.004,
    )


def test_planar_motion_callbacks_regression_paths():
    logger = _DummyLogger()
    pmc = _FakePMC()
    mover_utils = _FakeMoverUtils()
    config = _config()

    motion = MotionCallbacks(logger, pmc, mover_utils, config)

    linear_req = SimpleNamespace(xbot_id=0, x_pos=100.0, y_pos=120.0)
    linear_res = SimpleNamespace(success=False, status_message="")
    linear_result = motion.callback_linear_motion_si(linear_req, linear_res)
    assert linear_result.success is True

    sixd_req = SimpleNamespace(
        xbot_id=0,
        x_pos=100.0,
        y_pos=120.0,
        z_pos=1.0,
        rx_pos=0.0,
        ry_pos=0.0,
        rz_pos=0.0,
    )
    sixd_res = SimpleNamespace(success=False, status_message="")
    sixd_result = motion.callback_six_d_motion(sixd_req, sixd_res)
    assert sixd_result.success is True

    arc_req = SimpleNamespace(
        xbot_id=0,
        target_x=110.0,
        target_y=130.0,
        radius=20.0,
        max_speed=50.0,
        max_accel=100.0,
        arc_mode=0,
        arc_type=0,
        arc_direction=1,
        pos_mode=0,
        final_speed=0.0,
        angle_degrees=90.0,
    )
    arc_res = SimpleNamespace(success=False, status_message="")
    arc_result = motion.callback_arc_motion_si(arc_req, arc_res)
    assert arc_result.success is True


def test_planar_control_stop_motion_calls_pmc_directly():
    logger = _DummyLogger()
    pmc = _FakePMC()
    mover_utils = _FakeMoverUtils()
    config = _config()

    control = ControlCallbacks(logger, pmc, mover_utils, config)
    stop_req = SimpleNamespace(xbot_id=2)
    stop_res = SimpleNamespace(success=False, status_message="")

    stop_result = control.callback_stop_motion(stop_req, stop_res)

    assert stop_result.success is True
    assert pmc.bot.stopped_actor == 2
