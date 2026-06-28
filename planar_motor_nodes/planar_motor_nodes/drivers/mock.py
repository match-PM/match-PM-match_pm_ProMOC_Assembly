"""Tiny local dummy driver for running the node without PMCLib."""

from __future__ import annotations

from dataclasses import dataclass

from promoc_core import error_codes
from promoc_core.promoc_exceptions import ConfigurationError, MotionError
from promoc_core.status import DeviceState

from .base import PlanarMotorDriver
from ..models import SpeedProfile, XBotPose, XBotSnapshot


@dataclass
class _MockXBot:
    xbot_id: int
    pose: XBotPose
    active: bool = False
    levitated: bool = False
    raw_state: str = "XBOT_LANDED"


class MockPlanarMotorDriver(PlanarMotorDriver):
    """Minimal home-test driver.

    This is not a physics simulation. It only keeps enough state so the ROS node
    can start, accept commands, and publish plausible status without hardware.
    """

    def __init__(self, logger, mock_xbot_count: int = 1):
        self._logger = logger
        self._connected = False
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
        self._connected = False

    def list_xbot_ids(self) -> list[int]:
        self._require_connected()
        return sorted(self._xbots)

    def activate_xbots(self) -> None:
        self._require_connected()
        for xbot in self._xbots.values():
            xbot.active = True
            xbot.levitated = True
            xbot.raw_state = "XBOT_IDLE"

    def deactivate_xbots(self) -> None:
        self._require_connected()
        for xbot in self._xbots.values():
            xbot.active = False
            xbot.levitated = False
            xbot.raw_state = "XBOT_DISABLED"

    def set_levitation(self, xbot_id: int, enabled: bool = True) -> None:
        xbot = self._require_xbot(xbot_id)
        if enabled and not xbot.active:
            raise MotionError(
                f"XBot {xbot_id} is not active",
                error_code=error_codes.XBOT_NOT_ACTIVE,
                details={"xbot_id": xbot_id},
            )
        xbot.levitated = enabled
        xbot.raw_state = "XBOT_IDLE" if enabled else "XBOT_LANDED"

    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        xbot = self._require_xbot(xbot_id)
        return XBotSnapshot(
            xbot_id=xbot.xbot_id,
            pose=xbot.pose,
            raw_state=xbot.raw_state,
            device_state=self._device_state_for(xbot),
            active=xbot.active,
            levitated=xbot.levitated,
            busy=False,
            error_code=error_codes.SUCCESS,
            message=xbot.raw_state,
        )

    def move_linear_absolute(
        self,
        xbot_id: int,
        target_x: float,
        target_y: float,
        speed: SpeedProfile,
    ) -> float | None:
        xbot = self._require_ready_xbot(xbot_id)
        _ = speed
        xbot.pose = XBotPose(
            target_x,
            target_y,
            xbot.pose.z,
            xbot.pose.rx,
            xbot.pose.ry,
            xbot.pose.rz,
        )
        return 0.0

    def move_six_dof_absolute(
        self,
        xbot_id: int,
        target_pose: XBotPose,
        speed: SpeedProfile,
    ) -> float | None:
        _ = speed
        self._require_ready_xbot(xbot_id).pose = target_pose
        return 0.0

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
        _ = radius_m, max_speed, max_accel, final_speed, arc_mode, arc_type
        _ = arc_direction, angle_rad
        xbot = self._require_ready_xbot(xbot_id)
        if relative:
            target_x += xbot.pose.x
            target_y += xbot.pose.y
        xbot.pose = XBotPose(
            target_x,
            target_y,
            xbot.pose.z,
            xbot.pose.rx,
            xbot.pose.ry,
            xbot.pose.rz,
        )
        return 0.0

    def rotate(
        self,
        xbot_id: int,
        target_rz: float,
        max_speed: float,
        max_accel: float,
        mode: int,
    ) -> float | None:
        _ = max_speed, max_accel, mode
        xbot = self._require_ready_xbot(xbot_id)
        xbot.pose = XBotPose(
            xbot.pose.x,
            xbot.pose.y,
            xbot.pose.z,
            xbot.pose.rx,
            xbot.pose.ry,
            target_rz,
        )
        return 0.0

    def stop(self, xbot_id: int) -> None:
        self._require_xbot(xbot_id).raw_state = "XBOT_STOPPED"

    def stop_all(self) -> None:
        for xbot_id in self._xbots:
            self.stop(xbot_id)

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

    def _require_ready_xbot(self, xbot_id: int) -> _MockXBot:
        xbot = self._require_xbot(xbot_id)
        if not xbot.active or not xbot.levitated:
            raise MotionError(
                f"XBot {xbot_id} is not active",
                error_code=error_codes.XBOT_NOT_ACTIVE,
                details={"xbot_id": xbot_id},
            )
        xbot.raw_state = "XBOT_IDLE"
        return xbot

    @staticmethod
    def _device_state_for(xbot: _MockXBot) -> DeviceState:
        if xbot.raw_state == "XBOT_STOPPED":
            return DeviceState.STOPPED
        if not xbot.active or not xbot.levitated:
            return DeviceState.NOT_READY
        return DeviceState.READY
