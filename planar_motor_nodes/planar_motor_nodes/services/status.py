"""Runtime state and status helpers for the planar-motor node."""

from __future__ import annotations

from contextlib import contextmanager
import math
import threading
import time

from promoc_assembly_interfaces.msg import DeviceStatus, XBotInfo
from promoc_core import error_codes
from promoc_core.logging import LogTags, TaggedLogger
from promoc_core.motion import compute_motion_timeout
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ConnectionError,
    MotionError,
    ProMocError,
)
from promoc_core.status import DeviceState

from ..config import MoverNodeConfig
from ..models import SpeedProfile, XBotPose, XBotSnapshot


class MoverUtils:
    """Node-local runtime state shared by the service handlers."""

    def __init__(self, logger, driver, config: MoverNodeConfig):
        self.logger = TaggedLogger(logger, LogTags.PMC)
        self.driver = driver
        self.config = config
        self._state_lock = threading.Lock()
        self._operation_locks: dict[int, threading.Lock] = {}
        self._connected = False
        self._known_xbot_ids: list[int] = []
        self._device_state = DeviceState.DISCONNECTED
        self._error_code = error_codes.SUCCESS
        self._status_message = "Planar motor disconnected"
        self._speed_profiles: dict[int, SpeedProfile] = {}

    def connect_and_prepare(self) -> None:
        with self._state_lock:
            self._device_state = DeviceState.CONNECTING
            self._error_code = error_codes.SUCCESS
            self._status_message = "Connecting to planar motor controller"
        try:
            self.driver.connect(self.config.pmc_ip)
            self._known_xbot_ids = self.driver.list_xbot_ids()
            self._connected = True
            self._require_known_xbot(self.config.xbot_id)
            if self.config.auto_activate:
                if self.config.driver_mode == "hardware":
                    self.logger.warning(
                        "auto_activate is enabled in hardware mode; activating XBots "
                        "is an active hardware action"
                    )
                self.driver.activate_xbots([self.config.xbot_id])
                self._set_state(
                    DeviceState.READY,
                    error_codes.SUCCESS,
                    f"Connected and activated XBot {self.config.xbot_id}",
                )
            else:
                self._set_state(
                    DeviceState.NOT_READY,
                    error_codes.SUCCESS,
                    f"Connected. XBot {self.config.xbot_id} not activated",
                )
        except Exception as exc:
            self.mark_startup_failed(exc)
            raise

    def shutdown(self) -> None:
        if not self._connected:
            return
        try:
            self.driver.stop_all()
        except Exception as exc:  # pragma: no cover - best effort
            self.logger.warning(f"Stop-all during shutdown failed: {exc}")
        try:
            self.driver.disconnect()
        finally:
            self._connected = False
            self._set_state(
                DeviceState.DISCONNECTED,
                error_codes.SUCCESS,
                "Planar motor disconnected",
            )

    def ensure_connected(self) -> None:
        if not self._connected:
            raise ConnectionError(
                "Planar motor controller is not connected",
                error_code=error_codes.CONTROLLER_NOT_CONNECTED,
            )

    def ensure_selected_xbot(self, xbot_id: int) -> None:
        self.ensure_connected()
        self._require_known_xbot(xbot_id)

    def ensure_xbot_active(self, xbot_id: int) -> None:
        snapshot = self.get_snapshot(xbot_id)
        if not snapshot.active:
            raise MotionError(
                f"XBot {xbot_id} is not active",
                error_code=error_codes.XBOT_NOT_ACTIVE,
                details={"xbot_id": xbot_id},
            )

    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        self.ensure_selected_xbot(xbot_id)
        snapshot = self.driver.get_snapshot(xbot_id)
        if snapshot.device_state == DeviceState.BUSY:
            self._set_state(DeviceState.BUSY, snapshot.error_code, snapshot.message or "Busy")
        elif snapshot.device_state == DeviceState.STOPPED:
            self._set_state(
                DeviceState.STOPPED,
                snapshot.error_code or error_codes.MOVEMENT_STOPPED,
                snapshot.message or "Stopped",
            )
        elif snapshot.device_state == DeviceState.ERROR:
            self._set_state(
                DeviceState.ERROR,
                snapshot.error_code or error_codes.DRIVER_FAILURE,
                snapshot.message or "Driver error",
            )
        return snapshot

    def get_current_position(self, xbot_id: int) -> XBotPose:
        snapshot = self.get_snapshot(xbot_id)
        if snapshot.pose is None:
            raise MotionError(
                f"Current position for XBot {xbot_id} is unavailable",
                error_code=error_codes.POSITION_UNAVAILABLE,
                details={"xbot_id": xbot_id},
            )
        return snapshot.pose

    def get_speed_profile(self, xbot_id: int) -> SpeedProfile:
        profile = self._speed_profiles.get(int(xbot_id))
        if profile is not None:
            return profile
        profile = SpeedProfile(
            xy_vel=self.config.default_xy_vel,
            xy_max_accel=self.config.default_xy_max_accel,
            z_vel=self.config.default_z_vel,
            z_max_accel=self.config.default_z_max_accel,
            rx_vel=self.config.default_rx_vel,
            ry_vel=self.config.default_ry_vel,
            rz_vel=self.config.default_rz_vel,
        )
        self._speed_profiles[int(xbot_id)] = profile
        return profile

    def set_speed_profile(
        self,
        xbot_id: int,
        *,
        xy_vel: float,
        xy_max_accel: float,
        z_vel: float,
        z_max_accel: float,
        rx_vel: float,
        ry_vel: float,
        rz_vel: float,
    ) -> SpeedProfile:
        profile = SpeedProfile(
            xy_vel=xy_vel,
            xy_max_accel=xy_max_accel,
            z_vel=z_vel,
            z_max_accel=z_max_accel,
            rx_vel=rx_vel,
            ry_vel=ry_vel,
            rz_vel=rz_vel,
        )
        self._speed_profiles[int(xbot_id)] = profile
        return profile

    def is_position_in_bounds(self, pose: XBotPose) -> bool:
        return (
            self.config.x_min <= pose.x <= self.config.x_max
            and self.config.y_min <= pose.y <= self.config.y_max
            and self.config.z_min <= pose.z <= self.config.z_max
        )

    @contextmanager
    def claim_operation(self, xbot_id: int):
        lock = self._operation_locks.setdefault(int(xbot_id), threading.Lock())
        if not lock.acquire(blocking=False):
            raise MotionError(
                f"XBot {xbot_id} is already busy",
                error_code=error_codes.DEVICE_BUSY,
                details={"xbot_id": xbot_id},
            )
        try:
            self._set_state(DeviceState.BUSY, error_codes.SUCCESS, f"XBot {xbot_id} busy")
            yield
        finally:
            lock.release()

    def wait_for_motion_completion(
        self,
        xbot_id: int,
        expected_pose: XBotPose,
        tolerance: float,
        travel_time: float | None,
        *,
        buffer_s: float,
        multiplier: float,
        minimum_timeout: float,
    ) -> XBotSnapshot:
        timeout_s = compute_motion_timeout(
            travel_time,
            multiplier=multiplier,
            buffer_s=buffer_s,
            min_s=minimum_timeout,
            fallback_s=self.config.movement_timeout,
        )
        deadline = time.monotonic() + max(timeout_s, self.config.movement_timeout)
        last_snapshot: XBotSnapshot | None = None
        while time.monotonic() < deadline:
            snapshot = self.get_snapshot(xbot_id)
            last_snapshot = snapshot
            if not snapshot.busy:
                if snapshot.device_state == DeviceState.STOPPED:
                    raise MotionError(
                        f"Motion stopped for XBot {xbot_id}",
                        error_code=error_codes.MOVEMENT_STOPPED,
                        details={"xbot_id": xbot_id},
                    )
                if snapshot.device_state == DeviceState.ERROR:
                    raise MotionError(
                        f"Driver reported an error for XBot {xbot_id}",
                        error_code=error_codes.DRIVER_FAILURE,
                        details={"xbot_id": xbot_id},
                    )
                if snapshot.pose is None:
                    raise MotionError(
                        f"Current position for XBot {xbot_id} is unavailable",
                        error_code=error_codes.POSITION_UNAVAILABLE,
                        details={"xbot_id": xbot_id},
                    )
                if self._pose_matches(snapshot.pose, expected_pose, tolerance):
                    self._set_state(
                        DeviceState.READY,
                        error_codes.SUCCESS,
                        f"Motion completed for XBot {xbot_id}",
                    )
                    return snapshot
                raise MotionError(
                    f"XBot {xbot_id} did not reach the requested target",
                    error_code=error_codes.MOVEMENT_FAILED,
                    details={"xbot_id": xbot_id},
                )
            time.sleep(0.05)

        try:
            self.driver.stop(xbot_id)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            self.logger.warning(f"Timeout stop for XBot {xbot_id} failed: {exc}")
        raise MotionError(
            f"Motion timeout for XBot {xbot_id}",
            error_code=error_codes.MOVEMENT_TIMEOUT,
            details={"xbot_id": xbot_id},
        )

    def stop_xbot(self, xbot_id: int) -> None:
        self.ensure_selected_xbot(xbot_id)
        self.driver.stop(xbot_id)
        self._set_state(
            DeviceState.STOPPED,
            error_codes.STOP_REQUESTED,
            f"Stop requested for XBot {xbot_id}",
        )

    def list_xbots(self) -> list[int]:
        self.ensure_connected()
        self._known_xbot_ids = self.driver.list_xbot_ids()
        return list(self._known_xbot_ids)

    def build_info_message(self, xbot_id: int) -> XBotInfo | None:
        if not self._connected:
            return self._status_only_info_message()
        snapshot = self.get_snapshot(xbot_id)
        if snapshot.pose is None:
            return None
        message = XBotInfo()
        message.x_pos = snapshot.pose.x * 1000.0
        message.y_pos = snapshot.pose.y * 1000.0
        message.z_pos = snapshot.pose.z * 1000.0
        message.rx_pos = math.degrees(snapshot.pose.rx)
        message.ry_pos = math.degrees(snapshot.pose.ry)
        message.rz_pos = math.degrees(snapshot.pose.rz)
        message.xbot_state = snapshot.raw_state
        message.device_status = self._device_status_message(snapshot)
        return message

    def current_status(self) -> tuple[DeviceState, int, str]:
        with self._state_lock:
            return self._device_state, self._error_code, self._status_message

    def mark_startup_failed(self, exc: Exception) -> None:
        error_code = error_codes.UNKNOWN_ERROR
        message = str(exc) or exc.__class__.__name__
        if isinstance(exc, ProMocError):
            error_code = int(exc.error_code)
            message = exc.message
        self._connected = False
        self._set_state(
            DeviceState.ERROR,
            error_code,
            f"Planar motor startup failed: {message}",
        )

    def _require_known_xbot(self, xbot_id: int) -> None:
        if int(xbot_id) not in self._known_xbot_ids:
            raise ConfigurationError(
                f"XBot {xbot_id} was not found",
                error_code=error_codes.XBOT_NOT_FOUND,
                details={"xbot_id": xbot_id, "known_xbots": self._known_xbot_ids},
            )

    def _set_state(self, state: DeviceState, error_code: int, message: str) -> None:
        with self._state_lock:
            self._device_state = state
            self._error_code = error_code
            self._status_message = message

    def _device_status_message(self, snapshot: XBotSnapshot) -> DeviceStatus:
        state, error_code, message = self.current_status()
        status = DeviceStatus()
        status.state = int(snapshot.device_state or state)
        status.error_code = snapshot.error_code or error_code
        status.message = snapshot.message or message
        return status

    def _status_only_info_message(self) -> XBotInfo:
        state, error_code, message = self.current_status()
        status = DeviceStatus()
        status.state = int(state)
        status.error_code = error_code
        status.message = message
        info = XBotInfo()
        info.xbot_state = state.name
        info.device_status = status
        return info

    @staticmethod
    def _pose_matches(current: XBotPose, expected: XBotPose, tolerance: float) -> bool:
        return (
            abs(current.x - expected.x) <= tolerance
            and abs(current.y - expected.y) <= tolerance
            and abs(current.z - expected.z) <= tolerance
            and abs(current.rx - expected.rx) <= tolerance
            and abs(current.ry - expected.ry) <= tolerance
            and abs(current.rz - expected.rz) <= tolerance
        )
