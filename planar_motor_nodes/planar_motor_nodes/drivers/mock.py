"""Vendor-free mock planar-motor driver."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import threading
import time
from typing import Sequence

from promoc_core import error_codes
from promoc_core.promoc_exceptions import ConfigurationError, MotionError
from promoc_core.status import DeviceState

from .base import PlanarMotorDriver
from ..models import SpeedProfile, XBotPose, XBotSnapshot

LINEAR_MIN_TRAVEL_TIME_S = 0.2
ARC_MIN_TRAVEL_TIME_S = 0.3
ROTARY_MIN_TRAVEL_TIME_S = 0.2
SIX_D_MIN_TRAVEL_TIME_S = 0.4
STOP_POLL_S = 0.05


@dataclass
class _MockXBot:
    xbot_id: int
    pose: XBotPose
    active: bool = False
    levitated: bool = False
    raw_state: str = "XBOT_LANDED"
    busy: bool = False
    error_code: int = error_codes.SUCCESS
    message: str = ""
    stop_event: threading.Event = field(default_factory=threading.Event)


class MockPlanarMotorDriver(PlanarMotorDriver):
    """Small in-process mock implementation used for development and tests."""

    def __init__(self, logger, mock_xbot_count: int = 1):
        self._logger = logger
        self._connected = False
        self._lock = threading.Lock()
        self._xbots = {
            xbot_id: _MockXBot(
                xbot_id=xbot_id,
                pose=XBotPose(0.120, 0.120, 0.0015, 0.0, 0.0, 0.0),
            )
            for xbot_id in range(max(1, int(mock_xbot_count)))
        }

    def connect(self, controller_address: str) -> None:
        self._logger.info(f"Mock planar motor connected to {controller_address}")
        self._connected = True

    def disconnect(self) -> None:
        self.stop_all()
        self._connected = False

    def list_xbot_ids(self) -> list[int]:
        self._require_connected()
        return sorted(self._xbots.keys())

    def activate_xbots(self, xbot_ids: Sequence[int] | None = None) -> None:
        for xbot in self._iter_targets(xbot_ids):
            with self._lock:
                xbot.active = True
                xbot.levitated = True
                xbot.raw_state = "XBOT_IDLE"
                xbot.error_code = error_codes.SUCCESS
                xbot.message = "XBot active"

    def deactivate_xbots(self, xbot_ids: Sequence[int] | None = None) -> None:
        for xbot in self._iter_targets(xbot_ids):
            with self._lock:
                xbot.active = False
                xbot.levitated = False
                xbot.busy = False
                xbot.stop_event.set()
                xbot.raw_state = "XBOT_DISABLED"
                xbot.message = "XBot inactive"

    def set_levitation(
        self, xbot_ids: Sequence[int] | None = None, enabled: bool = True
    ) -> None:
        for xbot in self._iter_targets(xbot_ids):
            with self._lock:
                if not xbot.active and enabled:
                    raise MotionError(
                        f"XBot {xbot.xbot_id} is not active",
                        error_code=error_codes.XBOT_NOT_ACTIVE,
                    )
                xbot.levitated = enabled
                xbot.raw_state = "XBOT_IDLE" if enabled else "XBOT_LANDED"
                xbot.message = "Levitation enabled" if enabled else "Levitation disabled"

    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        xbot = self._require_xbot(xbot_id)
        with self._lock:
            return XBotSnapshot(
                xbot_id=xbot.xbot_id,
                pose=xbot.pose,
                raw_state=xbot.raw_state,
                device_state=self._device_state_for(xbot),
                active=xbot.active,
                levitated=xbot.levitated,
                busy=xbot.busy,
                error_code=xbot.error_code,
                message=xbot.message,
            )

    def move_linear_absolute(
        self,
        xbot_id: int,
        target_x: float,
        target_y: float,
        speed: SpeedProfile,
    ) -> float | None:
        xbot = self._prepare_motion(xbot_id)
        distance = math.dist((xbot.pose.x, xbot.pose.y), (target_x, target_y))
        travel_time = max(distance / max(speed.xy_vel, 1e-6), LINEAR_MIN_TRAVEL_TIME_S)
        target = XBotPose(
            target_x,
            target_y,
            xbot.pose.z,
            xbot.pose.rx,
            xbot.pose.ry,
            xbot.pose.rz,
        )
        self._start_motion(xbot_id, target, travel_time)
        return travel_time

    def move_six_dof_absolute(
        self,
        xbot_id: int,
        target_pose: XBotPose,
        speed: SpeedProfile,
    ) -> float | None:
        _ = speed
        self._prepare_motion(xbot_id)
        self._start_motion(xbot_id, target_pose, SIX_D_MIN_TRAVEL_TIME_S)
        return SIX_D_MIN_TRAVEL_TIME_S

    def move_relative(
        self,
        xbot_id: int,
        delta_pose: XBotPose,
        speed: SpeedProfile,
    ) -> float | None:
        snapshot = self.get_snapshot(xbot_id)
        if snapshot.pose is None:
            raise MotionError(
                "Current position unavailable for relative motion",
                error_code=error_codes.POSITION_UNAVAILABLE,
                details={"xbot_id": xbot_id},
            )
        return self.move_six_dof_absolute(
            xbot_id,
            snapshot.pose.with_delta(delta_pose),
            speed,
        )

    def arc_move(
        self,
        xbot_id: int,
        target_x: float,
        target_y: float,
        radius_m: float,
        max_speed: float,
        max_accel: float,
        *,
        relative: bool,
        final_speed: float,
        arc_mode: int,
        arc_type: int,
        arc_direction: int,
        angle_rad: float,
    ) -> float | None:
        _ = radius_m, max_accel, final_speed, arc_mode, arc_type, arc_direction, angle_rad
        snapshot = self.get_snapshot(xbot_id)
        if snapshot.pose is None:
            raise MotionError(
                "Current position unavailable for arc motion",
                error_code=error_codes.POSITION_UNAVAILABLE,
                details={"xbot_id": xbot_id},
            )
        if relative:
            target_x += snapshot.pose.x
            target_y += snapshot.pose.y
        self._prepare_motion(xbot_id)
        distance = math.dist((snapshot.pose.x, snapshot.pose.y), (target_x, target_y))
        travel_time = max(distance / max(max_speed, 1e-6), ARC_MIN_TRAVEL_TIME_S)
        target = XBotPose(
            target_x,
            target_y,
            snapshot.pose.z,
            snapshot.pose.rx,
            snapshot.pose.ry,
            snapshot.pose.rz,
        )
        self._start_motion(xbot_id, target, travel_time)
        return travel_time

    def rotate(
        self,
        xbot_id: int,
        target_rz: float,
        max_speed: float,
        max_accel: float,
        mode: int,
    ) -> float | None:
        _ = max_accel, mode
        snapshot = self.get_snapshot(xbot_id)
        if snapshot.pose is None:
            raise MotionError(
                "Current position unavailable for rotation",
                error_code=error_codes.POSITION_UNAVAILABLE,
                details={"xbot_id": xbot_id},
            )
        self._prepare_motion(xbot_id)
        distance = abs(snapshot.pose.rz - target_rz)
        travel_time = max(distance / max(max_speed, 1e-6), ROTARY_MIN_TRAVEL_TIME_S)
        target = XBotPose(
            snapshot.pose.x,
            snapshot.pose.y,
            snapshot.pose.z,
            snapshot.pose.rx,
            snapshot.pose.ry,
            target_rz,
        )
        self._start_motion(xbot_id, target, travel_time)
        return travel_time

    def stop(self, xbot_id: int) -> None:
        xbot = self._require_xbot(xbot_id)
        with self._lock:
            xbot.stop_event.set()
            if not xbot.busy:
                xbot.raw_state = "XBOT_STOPPED"
                xbot.message = "Stop requested"

    def stop_all(self) -> None:
        for xbot_id in list(self._xbots):
            self.stop(xbot_id)

    def _prepare_motion(self, xbot_id: int) -> _MockXBot:
        xbot = self._require_xbot(xbot_id)
        with self._lock:
            if not xbot.active or not xbot.levitated:
                raise MotionError(
                    f"XBot {xbot_id} is not active",
                    error_code=error_codes.XBOT_NOT_ACTIVE,
                    details={"xbot_id": xbot_id},
                )
            if xbot.busy:
                raise MotionError(
                    f"XBot {xbot_id} is already busy",
                    error_code=error_codes.DEVICE_BUSY,
                    details={"xbot_id": xbot_id},
                )
            xbot.busy = True
            xbot.raw_state = "XBOT_MOTION"
            xbot.message = "Motion in progress"
            xbot.stop_event = threading.Event()
        return xbot

    def _start_motion(self, xbot_id: int, target_pose: XBotPose, travel_time: float) -> None:
        worker = threading.Thread(
            target=self._complete_motion,
            args=(xbot_id, target_pose, travel_time),
            daemon=True,
        )
        worker.start()

    def _complete_motion(
        self, xbot_id: int, target_pose: XBotPose, travel_time: float
    ) -> None:
        xbot = self._require_xbot(xbot_id)
        deadline = time.monotonic() + travel_time
        while time.monotonic() < deadline:
            if xbot.stop_event.wait(STOP_POLL_S):
                with self._lock:
                    xbot.busy = False
                    xbot.raw_state = "XBOT_STOPPED"
                    xbot.message = "Motion stopped"
                    xbot.error_code = error_codes.MOVEMENT_STOPPED
                return

        with self._lock:
            xbot.pose = target_pose
            xbot.busy = False
            xbot.raw_state = "XBOT_IDLE"
            xbot.message = "Motion complete"
            xbot.error_code = error_codes.SUCCESS

    def _iter_targets(self, xbot_ids: Sequence[int] | None) -> list[_MockXBot]:
        self._require_connected()
        if xbot_ids is None:
            return [self._xbots[xbot_id] for xbot_id in sorted(self._xbots)]
        return [self._require_xbot(int(xbot_id)) for xbot_id in xbot_ids]

    def _require_connected(self) -> None:
        if not self._connected:
            raise MotionError(
                "Planar motor controller is not connected",
                error_code=error_codes.CONTROLLER_NOT_CONNECTED,
            )

    def _require_xbot(self, xbot_id: int) -> _MockXBot:
        self._require_connected()
        try:
            return self._xbots[int(xbot_id)]
        except KeyError as exc:
            raise ConfigurationError(
                f"XBot {xbot_id} was not found",
                error_code=error_codes.XBOT_NOT_FOUND,
                details={"xbot_id": xbot_id},
            ) from exc

    @staticmethod
    def _device_state_for(xbot: _MockXBot) -> DeviceState:
        if xbot.busy:
            return DeviceState.BUSY
        if xbot.raw_state == "XBOT_STOPPED":
            return DeviceState.STOPPED
        if xbot.raw_state in {"XBOT_DISABLED", "XBOT_LANDED"}:
            return DeviceState.NOT_READY
        return DeviceState.READY
