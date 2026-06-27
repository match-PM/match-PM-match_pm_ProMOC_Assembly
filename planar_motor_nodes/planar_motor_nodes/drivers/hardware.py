"""Hardware-backed planar-motor driver with lazy vendor imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from promoc_core import error_codes
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ConnectionError,
    DriverNotAvailableError,
    HardwareError,
    MotionError,
)
from promoc_core.status import DeviceState

from .base import PlanarMotorDriver
from .pmclib_loader import load_pmclib
from ..models import SpeedProfile, XBotPose, XBotSnapshot


@dataclass(frozen=True)
class _BackendModules:
    bot: Any
    sys_cmd: Any
    pmc_types: Any
    source: str


class HardwarePlanarMotorDriver(PlanarMotorDriver):
    """Small adapter from the internal driver contract to the vendor API."""

    def __init__(self, logger):
        self._logger = logger
        self._backend: _BackendModules | None = None
        self._connected = False

    def connect(self, controller_address: str) -> None:
        backend = self._backend or self._load_backend()
        success = backend.sys_cmd.connect_to_pmc(controller_address)
        if not success:
            raise ConnectionError(
                f"Failed to connect to PMC at {controller_address}",
                error_code=error_codes.CONNECTION_FAILED,
                details={"controller_address": controller_address},
            )
        gain_mastership = getattr(backend.sys_cmd, "gain_mastership", None)
        if callable(gain_mastership):
            gain_mastership()
        self._connected = True

    def disconnect(self) -> None:
        if not self._backend:
            return
        try:
            release_mastership = getattr(self._backend.sys_cmd, "release_mastership", None)
            if callable(release_mastership):
                release_mastership()
        finally:
            self._connected = False

    def list_xbot_ids(self) -> list[int]:
        xbots = self._read_all_xbots()
        ids = [self._extract_xbot_id(xbot) for xbot in xbots]
        if len(ids) != len(set(ids)):
            raise HardwareError(
                "Duplicate XBot IDs returned by the planar-motor driver",
                error_code=error_codes.DRIVER_FAILURE,
                details={"xbot_ids": ids},
            )
        return sorted(ids)

    def activate_xbots(self, xbot_ids: Sequence[int] | None = None) -> None:
        self._require_connected()
        if xbot_ids:
            for xbot_id in xbot_ids:
                self._validate_known_xbot(xbot_id)
        self._backend.bot.activate_xbots()

    def deactivate_xbots(self, xbot_ids: Sequence[int] | None = None) -> None:
        self._require_connected()
        if xbot_ids:
            for xbot_id in xbot_ids:
                self._validate_known_xbot(xbot_id)
        deactivate = getattr(self._backend.bot, "deactivate_xbots", None)
        if callable(deactivate):
            deactivate()

    def set_levitation(
        self, xbot_ids: Sequence[int] | None = None, enabled: bool = True
    ) -> None:
        self._require_connected()
        if xbot_ids and len(xbot_ids) == 1:
            target_id = int(xbot_ids[0])
            self._validate_known_xbot(target_id)
        else:
            target_id = 0
        self._backend.bot.levitation_command(target_id, 1 if enabled else 0)

    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        self._require_connected()
        xbot = self._read_xbot(xbot_id)
        raw_state = "UNKNOWN"
        try:
            status = self._backend.bot.get_xbot_status(xbot_id)
            raw_state = self._state_name(getattr(status, "xbot_state", None))
        except Exception:
            raw_state = self._state_name(getattr(xbot, "xbot_state", None))

        pose = XBotPose(
            x=float(xbot.x_pos),
            y=float(xbot.y_pos),
            z=float(xbot.z_pos),
            rx=float(xbot.rx_pos),
            ry=float(xbot.ry_pos),
            rz=float(xbot.rz_pos),
        )
        device_state = self._device_state_from_raw(raw_state)
        return XBotSnapshot(
            xbot_id=xbot_id,
            pose=pose,
            raw_state=raw_state,
            device_state=device_state,
            active=device_state not in {DeviceState.NOT_READY, DeviceState.ERROR},
            levitated=raw_state not in {"XBOT_LANDED", "XBOT_DISABLED"},
            busy=device_state == DeviceState.BUSY,
        )

    def move_linear_absolute(
        self,
        xbot_id: int,
        target_x: float,
        target_y: float,
        speed: SpeedProfile,
    ) -> float | None:
        self._require_connected()
        self._validate_known_xbot(xbot_id)
        return self._backend.bot.linear_motion_si(
            xbot_id,
            target_x,
            target_y,
            speed.xy_vel,
            speed.xy_max_accel,
        )

    def move_six_dof_absolute(
        self,
        xbot_id: int,
        target_pose: XBotPose,
        speed: SpeedProfile,
    ) -> float | None:
        self._require_connected()
        self._validate_known_xbot(xbot_id)
        return self._backend.bot.six_d_of_motion_si(
            xbot_id,
            target_pose.x,
            target_pose.y,
            target_pose.z,
            target_pose.rx,
            target_pose.ry,
            target_pose.rz,
            speed.xy_vel,
            speed.xy_max_accel,
            speed.z_vel,
            speed.rx_vel,
            speed.ry_vel,
            speed.rz_vel,
        )

    def move_relative(
        self,
        xbot_id: int,
        delta_pose: XBotPose,
        speed: SpeedProfile,
    ) -> float | None:
        current = self.get_snapshot(xbot_id).pose
        if current is None:
            raise MotionError(
                "Current position unavailable for relative motion",
                error_code=error_codes.POSITION_UNAVAILABLE,
                details={"xbot_id": xbot_id},
            )
        return self.move_six_dof_absolute(xbot_id, current.with_delta(delta_pose), speed)

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
        self._require_connected()
        self._validate_known_xbot(xbot_id)
        if relative:
            current = self.get_snapshot(xbot_id).pose
            if current is None:
                raise MotionError(
                    "Current position unavailable for relative arc motion",
                    error_code=error_codes.POSITION_UNAVAILABLE,
                    details={"xbot_id": xbot_id},
                )
            target_x += current.x
            target_y += current.y
        return self._backend.bot.arc_motion_si(
            xbot_id,
            target_x,
            target_y,
            radius_m,
            max_speed,
            max_accel,
            0,
            arc_mode,
            arc_type,
            arc_direction,
            0 if not relative else 1,
            final_speed,
            angle_rad,
        )

    def rotate(
        self,
        xbot_id: int,
        target_rz: float,
        max_speed: float,
        max_accel: float,
        mode: int,
    ) -> float | None:
        self._require_connected()
        self._validate_known_xbot(xbot_id)
        return self._backend.bot.rotary_motion(
            xbot_id,
            target_rz,
            max_speed,
            max_accel,
            0,
            mode,
        )

    def stop(self, xbot_id: int) -> None:
        self._require_connected()
        self._validate_known_xbot(xbot_id)
        self._backend.bot.stop_motion(xbot_id)

    def stop_all(self) -> None:
        self._require_connected()
        self._backend.bot.stop_motion(0)

    def _load_backend(self) -> _BackendModules:
        try:
            modules = load_pmclib()
            self._backend = _BackendModules(
                bot=modules.xbot_commands,
                sys_cmd=modules.system_commands,
                pmc_types=modules.pmc_types,
                source=modules.source,
            )
            return self._backend
        except ImportError as exc:
            raise DriverNotAvailableError(
                f"Vendor planar-motor driver is unavailable: {exc}",
                error_code=error_codes.DRIVER_FAILURE,
            ) from exc

    def _require_connected(self) -> None:
        if not self._connected:
            raise ConnectionError(
                "Planar motor controller is not connected",
                error_code=error_codes.CONTROLLER_NOT_CONNECTED,
            )

    def _read_all_xbots(self) -> list[Any]:
        backend = self._backend or self._load_backend()
        get_xbot_data = getattr(backend.bot, "get_xbot_data", None)
        if callable(get_xbot_data):
            xbots = get_xbot_data()
        else:
            xbots = backend.bot.get_all_xbot_info(0)
        if not xbots:
            raise HardwareError(
                "No XBot data returned by the planar-motor driver",
                error_code=error_codes.POSITION_UNAVAILABLE,
            )
        return list(xbots)

    def _read_xbot(self, xbot_id: int) -> Any:
        xbots = self._read_all_xbots()
        for xbot in xbots:
            candidate_id = self._extract_xbot_id(xbot)
            if candidate_id == int(xbot_id):
                return xbot
        raise ConfigurationError(
            f"XBot {xbot_id} was not found",
            error_code=error_codes.XBOT_NOT_FOUND,
            details={"xbot_id": xbot_id},
        )

    def _validate_known_xbot(self, xbot_id: int) -> None:
        self._read_xbot(xbot_id)

    @staticmethod
    def _extract_xbot_id(xbot: Any) -> int:
        raw_id = getattr(xbot, "xbot_id", None)
        if raw_id is None:
            raise HardwareError(
                "XBot status from the planar-motor driver is missing xbot_id",
                error_code=error_codes.DRIVER_FAILURE,
            )
        try:
            xbot_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise HardwareError(
                f"Invalid XBot ID from the planar-motor driver: {raw_id!r}",
                error_code=error_codes.DRIVER_FAILURE,
                details={"xbot_id": raw_id},
            ) from exc
        if xbot_id < 0:
            raise HardwareError(
                f"Invalid negative XBot ID from the planar-motor driver: {xbot_id}",
                error_code=error_codes.DRIVER_FAILURE,
                details={"xbot_id": xbot_id},
            )
        return xbot_id

    @staticmethod
    def _state_name(raw_state: Any) -> str:
        if raw_state is None:
            return "UNKNOWN"
        if hasattr(raw_state, "name"):
            return str(raw_state.name)
        return str(raw_state)

    @staticmethod
    def _device_state_from_raw(raw_state: str) -> DeviceState:
        if any(token in raw_state for token in ("MOTION", "WAIT", "DISCOVERING")):
            return DeviceState.BUSY
        if any(token in raw_state for token in ("STOPPING", "STOPPED")):
            return DeviceState.STOPPED
        if any(token in raw_state for token in ("ERROR", "OBSTACLE")):
            return DeviceState.ERROR
        if any(token in raw_state for token in ("LANDED", "UNDETECTED", "DISABLED")):
            return DeviceState.NOT_READY
        return DeviceState.READY
