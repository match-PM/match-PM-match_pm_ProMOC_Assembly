# ruff: noqa: E402
"""Runtime-focused tests for timeout and status handling."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("planar_motor_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from planar_motor_nodes.config import DEFAULT_MOVER_NODE_PARAMETERS, MoverNodeConfig
from planar_motor_nodes.models import SpeedProfile, XBotPose, XBotSnapshot
from planar_motor_nodes.services.control import ControlCallbacks
from planar_motor_nodes.services.status import MoverUtils
from promoc_core import error_codes
from promoc_core.promoc_exceptions import DriverNotAvailableError, MotionError
from promoc_core.status import DeviceState


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


class _AlwaysBusyDriver:
    def connect(self, controller_address: str) -> None:
        _ = controller_address

    def disconnect(self) -> None:
        return None

    def list_xbot_ids(self) -> list[int]:
        return [0]

    def activate_xbots(self, xbot_ids=None) -> None:
        _ = xbot_ids

    def deactivate_xbots(self, xbot_ids=None) -> None:
        _ = xbot_ids

    def set_levitation(self, xbot_ids=None, enabled: bool = True) -> None:
        _ = xbot_ids, enabled

    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        _ = xbot_id
        return XBotSnapshot(
            xbot_id=0,
            pose=XBotPose(0.12, 0.12, 0.0015, 0.0, 0.0, 0.0),
            raw_state="XBOT_MOTION",
            device_state=DeviceState.BUSY,
            active=True,
            levitated=True,
            busy=True,
        )

    def move_linear_absolute(self, xbot_id: int, target_x: float, target_y: float, speed: SpeedProfile):
        _ = xbot_id, target_x, target_y, speed
        return 5.0

    def move_six_dof_absolute(self, xbot_id: int, target_pose: XBotPose, speed: SpeedProfile):
        _ = xbot_id, target_pose, speed
        return 5.0

    def arc_move(self, xbot_id: int, target_x: float, target_y: float, radius_m: float, max_speed: float, max_accel: float, *, relative: bool, final_speed: float, arc_mode: int, arc_type: int, arc_direction: int, angle_rad: float):
        _ = (
            xbot_id,
            target_x,
            target_y,
            radius_m,
            max_speed,
            max_accel,
            relative,
            final_speed,
            arc_mode,
            arc_type,
            arc_direction,
            angle_rad,
        )
        return 5.0

    def rotate(self, xbot_id: int, target_rz: float, max_speed: float, max_accel: float, mode: int):
        _ = xbot_id, target_rz, max_speed, max_accel, mode
        return 5.0

    def stop(self, xbot_id: int) -> None:
        _ = xbot_id

    def stop_all(self) -> None:
        return None


class _StartupFailureDriver(_AlwaysBusyDriver):
    def connect(self, controller_address: str) -> None:
        _ = controller_address
        raise DriverNotAvailableError(
            "local PMCLib is missing",
            error_code=error_codes.DRIVER_FAILURE,
        )


class _ConnectedDriver(_AlwaysBusyDriver):
    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        _ = xbot_id
        return XBotSnapshot(
            xbot_id=0,
            pose=XBotPose(0.12, 0.12, 0.0015, 0.0, 0.0, 0.0),
            raw_state="XBOT_IDLE",
            device_state=DeviceState.READY,
            active=True,
            levitated=True,
            busy=False,
        )


def _config() -> MoverNodeConfig:
    return MoverNodeConfig(
        driver_mode="mock",
        xbot_id=0,
        publish_rate=10.0,
        pmc_ip="mock://controller",
        auto_activate=False,
        movement_timeout=0.1,
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


def _hardware_config() -> MoverNodeConfig:
    return MoverNodeConfig(
        driver_mode="hardware",
        xbot_id=0,
        publish_rate=10.0,
        pmc_ip="192.0.2.10",
        auto_activate=False,
        movement_timeout=0.1,
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


def test_wait_for_motion_completion_maps_timeout_to_meaningful_error():
    runtime = MoverUtils(_DummyLogger(), _AlwaysBusyDriver(), _config())
    runtime.connect_and_prepare()
    try:
        runtime.wait_for_motion_completion(
            0,
            XBotPose(0.15, 0.13, 0.0015, 0.0, 0.0, 0.0),
            tolerance=0.001,
            travel_time=0.01,
            buffer_s=0.0,
            multiplier=1.0,
            minimum_timeout=0.01,
        )
    except MotionError as exc:
        assert exc.error_code == error_codes.MOVEMENT_TIMEOUT
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected MotionError with MOVEMENT_TIMEOUT")


def test_default_auto_activate_matches_main_startup_behavior():
    assert DEFAULT_MOVER_NODE_PARAMETERS["auto_activate"] is True


def test_startup_failure_publishes_error_status_message():
    runtime = MoverUtils(_DummyLogger(), _StartupFailureDriver(), _hardware_config())

    try:
        runtime.connect_and_prepare()
    except DriverNotAvailableError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected startup failure")

    state, error_code, message = runtime.current_status()
    assert state == DeviceState.ERROR
    assert error_code == error_codes.DRIVER_FAILURE
    assert "Planar motor startup failed" in message
    assert "local PMCLib is missing" in message

    info = runtime.build_info_message(0)
    assert info.device_status.state == int(DeviceState.ERROR)
    assert info.device_status.error_code == error_codes.DRIVER_FAILURE
    assert "local PMCLib is missing" in info.device_status.message


def test_hardware_z_max_accel_change_is_reported_as_compatibility_limit():
    config = _hardware_config()
    driver = _ConnectedDriver()
    runtime = MoverUtils(_DummyLogger(), driver, config)
    runtime.connect_and_prepare()
    callbacks = ControlCallbacks(_DummyLogger(), driver, runtime, config)
    request = SimpleNamespace(
        xbot_id=0,
        xy_vel=0.05,
        xy_max_accel=0.2,
        z_vel=0.01,
        z_max_accel=0.2,
        rx_vel=0.1,
        ry_vel=0.1,
        rz_vel=0.2,
    )
    response = SimpleNamespace()

    result = callbacks.callback_set_velocity_acceleration(request, response)

    assert result.success is True
    assert "z_max_accel is accepted for interface compatibility" in result.status_message
