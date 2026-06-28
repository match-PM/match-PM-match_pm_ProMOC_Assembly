"""Hardware-backed planar-motor driver with lazy vendor imports."""

from __future__ import annotations

import time
from typing import Any

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


class HardwarePlanarMotorDriver(PlanarMotorDriver):
    """Small adapter from the internal driver contract to the vendor API.

    Uebersetzt die abstrakten Treibermethoden in Aufrufe der proprietaren
    PMCLib (xbot_commands, system_commands). Verwaltet Verbindung und
    XBot-Statusabfrage ueber die Vendor-API.
    """

    # Wiederholungsintervall fuer Verbindungsversuche
    CONNECT_RETRY_INTERVAL_S = 0.1
    CONNECT_LOG_EVERY_ATTEMPTS = 25

    def __init__(self, logger):
        self._logger = logger
        self._sys_cmd: Any | None = None
        self._bot: Any | None = None
        self._connected = False

    def connect(self, controller_address: str) -> None:
        # Verbindet zum PMC-Controller mit Wiederholungslogik.
        # Laedt zuerst das PMCLib-Backend (lazy import), versucht dann
        # system_commands.connect_to_pmc() bis es erfolgreich ist.
        self._load_backend()
        attempts = 0

        while not self._connected:
            attempts += 1
            try:
                success = self._sys_cmd.connect_to_pmc(controller_address)
            except Exception as exc:
                success = False
                if attempts == 1 or attempts % self.CONNECT_LOG_EVERY_ATTEMPTS == 0:
                    self._log(
                        "warning",
                        "PMC connection attempt "
                        f"{attempts} to {controller_address} failed: {exc}",
                    )

            if success:
                break

            if attempts == 1 or attempts % self.CONNECT_LOG_EVERY_ATTEMPTS == 0:
                self._log(
                    "warning",
                    "Waiting for PMC connection at "
                    f"{controller_address}; attempt {attempts} failed",
                )
            time.sleep(self.CONNECT_RETRY_INTERVAL_S)

        self._connected = True
        if attempts > 1:
            self._log(
                "info",
                f"Connected to PMC at {controller_address} after {attempts} attempts",
            )

    def disconnect(self) -> None:
        self._connected = False

    def list_xbot_ids(self) -> list[int]:
        # Liest alle XBots vom Controller, extrahiert deren IDs, prueft
        # auf Duplikate und gibt eine sortierte Liste zurueck.
        xbots = self._read_all_xbots()
        ids = [self._extract_xbot_id(xbot) for xbot in xbots]
        if len(ids) != len(set(ids)):
            raise HardwareError(
                "Duplicate XBot IDs returned by the planar-motor driver",
                error_code=error_codes.DRIVER_FAILURE,
                details={"xbot_ids": ids},
            )
        return sorted(ids)

    def activate_xbots(self) -> None:
        self._require_connected()
        self._bot.activate_xbots()

    def deactivate_xbots(self) -> None:
        self._require_connected()
        deactivate = getattr(self._bot, "deactivate_xbots", None)
        if callable(deactivate):
            deactivate()

    def set_levitation(self, xbot_id: int, enabled: bool = True) -> None:
        self._require_connected()
        self._bot.levitation_command(int(xbot_id), 1 if enabled else 0)

    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        # Baut einen XBotSnapshot aus den Rohdaten des Controllers.
        # 1. XBot-Daten lesen (_read_xbot)
        # 2. Status aus dem xbot_state-Attribut ableiten
        # 3. Pose extrahieren (x/y/z/rx/ry/rz)
        # 4. device_state aus raw_state ableiten
        # 5. active/levitated/busy Flags setzen
        self._require_connected()
        xbot = self._read_xbot(xbot_id)
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
        return self._bot.linear_motion_si(
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
        return self._bot.six_d_of_motion_si(
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
        # Kreisbogenbewegung ueber PMCLib.
        # Bei relativer Bewegung: target_x/y werden zum aktuellen X/Y addiert.
        # pos_mode wird als 0 (absolut) oder 1 (relativ) an PMCLib uebergeben.
        self._require_connected()
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
        return self._bot.arc_motion_si(
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
        return self._bot.rotary_motion(
            xbot_id,
            target_rz,
            max_speed,
            max_accel,
            0,
            mode,
        )

    def stop(self, xbot_id: int) -> None:
        self._require_connected()
        self._bot.stop_motion(xbot_id)

    def stop_all(self) -> None:
        self._require_connected()
        self._bot.stop_motion(0)

    def _load_backend(self) -> None:
        # Laedt die PMCLib-Module (system_commands, xbot_commands)
        # ueber den Lazy-Loader. Wirft DriverNotAvailableError, wenn die
        # PMCLib nicht installiert/verfuegbar ist.
        if self._sys_cmd is not None and self._bot is not None:
            return
        try:
            self._sys_cmd, self._bot = load_pmclib()
        except ImportError as exc:
            raise DriverNotAvailableError(
                f"Vendor planar-motor driver is unavailable: {exc}",
                error_code=error_codes.DRIVER_FAILURE,
            ) from exc

    def _require_connected(self) -> None:
        if not self._connected or self._sys_cmd is None or self._bot is None:
            raise ConnectionError(
                "Planar motor controller is not connected",
                error_code=error_codes.CONTROLLER_NOT_CONNECTED,
            )

    def _log(self, level: str, message: str) -> None:
        log_fn = getattr(self._logger, level, None)
        if callable(log_fn):
            log_fn(message)

    def _read_all_xbots(self) -> list[Any]:
        # Liest alle XBot-Daten vom Controller.
        # Nutzt denselben PMCLib-Pfad wie main: get_all_xbot_info(0).
        # Wirft HardwareError, wenn keine Daten zurueckkommen.
        self._load_backend()
        xbots = self._bot.get_all_xbot_info(0)
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
        # Mappt den rohen Zustandsstring des Controllers auf DeviceState.
        # MOTION/WAIT/DISCOVERING -> BUSY (XBot bewegt sich)
        # STOPPING/STOPPED -> STOPPED
        # ERROR/OBSTACLE -> ERROR
        # LANDED/UNDETECTED/DISABLED -> NOT_READY
        # Alles andere -> READY
        if any(token in raw_state for token in ("MOTION", "WAIT", "DISCOVERING")):
            return DeviceState.BUSY
        if any(token in raw_state for token in ("STOPPING", "STOPPED")):
            return DeviceState.STOPPED
        if any(token in raw_state for token in ("ERROR", "OBSTACLE")):
            return DeviceState.ERROR
        if any(token in raw_state for token in ("LANDED", "UNDETECTED", "DISABLED")):
            return DeviceState.NOT_READY
        return DeviceState.READY
