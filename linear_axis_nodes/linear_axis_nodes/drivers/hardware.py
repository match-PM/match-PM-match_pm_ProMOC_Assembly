"""Simple Thorlabs LTS300 driver using pylablib."""

from __future__ import annotations

import glob
import os
import time
from typing import Any, Optional, Tuple
import warnings

from promoc_core.promoc_exceptions import (
    CommunicationError,
    DeviceNotFoundError,
    DriverNotAvailableError,
    HardwareError,
    HomingFailedError,
    MovementTimeoutError,
)

from .base import LinearAxisDriver

try:
    from pylablib.devices import Thorlabs
except ImportError:
    Thorlabs = None


warnings.filterwarnings("ignore", message="can't recognize the stage name*")
warnings.filterwarnings("ignore", message="can't recognize motor model*")


class ThorlabsLTS300Driver(LinearAxisDriver):
    """Thin wrapper around ``Thorlabs.KinesisMotor``.

    The hardware path is intentionally blocking and direct, matching the old
    main-branch style: start a command, wait while ``is_moving()``, then read
    the position.
    """

    device_units_per_mm = 409600.0
    poll_interval_s = 0.1

    def __init__(self, logger, expected_serial: str = ""):
        self.logger = logger
        self.expected_serial = str(expected_serial)
        self.device: Any | None = None
        self.connected = False
        self.serial_no = ""

    def connect(self, port: str = None) -> bool:
        if Thorlabs is None:
            raise DriverNotAvailableError(
                "Thorlabs library (pylablib) is not available",
                details={"library": "pylablib", "module": "Thorlabs"},
            )

        try:
            if not port and self.expected_serial:
                return self._connect_by_serial(self.expected_serial)
            return self._connect_to_port(self._resolve_port(port))
        except DeviceNotFoundError:
            raise
        except Exception as exc:
            raise HardwareError(
                f"Connection failed: {exc}",
                details={"port": port, "error": str(exc)},
            ) from exc

    def disconnect(self) -> None:
        if self.device is not None:
            try:
                self.device.close()
            except Exception as exc:
                self.logger.warning(f"Error during disconnect: {exc}")
        self.connected = False
        self.device = None

    def move_absolute(self, position: float, timeout: Optional[float] = None) -> None:
        self._ensure_connected()
        self.device.move_to(float(position) * self.device_units_per_mm, scale=False)
        self._wait_until_idle(timeout or 300.0, "Absolute movement")

    def move_relative(self, distance: float, timeout: Optional[float] = None) -> None:
        self._ensure_connected()
        target = self.device.get_position() + float(distance) * self.device_units_per_mm
        self.device.move_to(target, scale=False)
        self._wait_until_idle(timeout or 300.0, "Relative movement")

    def jog(self, step_size: float, timeout: Optional[float] = None) -> None:
        self._ensure_connected()
        step_mm = float(step_size)
        step_device = int(abs(step_mm) * self.device_units_per_mm)
        if step_device == 0:
            return

        self.device.setup_jog(
            mode="step",
            step_size=step_device,
            stop_mode="profiled",
            scale=False,
        )
        self.device.jog("+" if step_mm >= 0.0 else "-", kind="builtin")
        self._wait_until_idle(timeout or 300.0, "Jog")

    def home(self, timeout: float = 180.0) -> None:
        self._ensure_connected()
        try:
            self.device.home(force=True, timeout=timeout)
            self._wait_until_idle(timeout + 30.0, "Homing")
        except MovementTimeoutError:
            raise
        except Exception as exc:
            raise HomingFailedError(
                f"Homing failed: {exc}",
                details={"timeout": timeout, "error": str(exc)},
            ) from exc

    def stop(self) -> None:
        self._ensure_connected()
        self.device.stop()

    def get_position(self) -> float:
        self._ensure_connected()
        return self.device.get_position() / self.device_units_per_mm

    def is_moving(self) -> bool:
        if not self.connected or self.device is None:
            return False
        return bool(self.device.is_moving())

    def get_serial_number(self) -> str:
        return self.serial_no

    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        self._ensure_connected()
        params = self.device.get_velocity_parameters(scale=False)
        return (
            params.min_velocity / self.device_units_per_mm,
            params.acceleration / self.device_units_per_mm,
            params.max_velocity / self.device_units_per_mm,
        )

    def set_velocity_parameters(
        self,
        min_velocity: Optional[float] = None,
        acceleration: Optional[float] = None,
        max_velocity: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        current_min, current_accel, current_max = self.get_velocity_parameters()
        min_velocity = current_min if min_velocity is None else float(min_velocity)
        acceleration = current_accel if acceleration is None else float(acceleration)
        max_velocity = current_max if max_velocity is None else float(max_velocity)

        self.device.setup_velocity(
            min_velocity=int(min_velocity * self.device_units_per_mm),
            acceleration=int(acceleration * self.device_units_per_mm),
            max_velocity=int(max_velocity * self.device_units_per_mm),
            scale=False,
        )
        return self.get_velocity_parameters()

    def _wait_until_idle(self, timeout_s: float, operation_name: str) -> None:
        started = time.monotonic()
        while self.device.is_moving():
            if time.monotonic() - started > timeout_s:
                try:
                    self.device.stop()
                except Exception as exc:
                    self.logger.warning(f"Stop after timeout failed: {exc}")
                raise MovementTimeoutError(
                    f"{operation_name} timeout after {timeout_s}s",
                    details={"timeout": timeout_s},
                )
            time.sleep(self.poll_interval_s)

    def _ensure_connected(self) -> None:
        if not self.connected or self.device is None:
            raise CommunicationError("Device not connected")

    def _resolve_port(self, port: str | None) -> str:
        if port:
            return self._resolve_symlink(port)

        candidates = self._candidate_ports()
        if not candidates:
            raise DeviceNotFoundError(
                "No serial port configured and no /dev/ttyUSB* device found",
                details={"port": port},
            )
        self.logger.info(f"No serial_port configured; using {candidates[0]}")
        return candidates[0]

    def _connect_by_serial(self, expected_serial: str) -> bool:
        candidates = self._candidate_ports()
        if not candidates:
            raise DeviceNotFoundError(
                "No serial port configured and no /dev/ttyUSB* device found",
                details={"serial_number": expected_serial},
            )

        errors: list[str] = []
        for port in candidates:
            try:
                device = Thorlabs.KinesisMotor(port, scale="m")
                serial = str(device.get_device_info()[0])
                if serial == expected_serial:
                    self.device = device
                    self.serial_no = serial
                    self.connected = True
                    self.logger.info(
                        f"Connected to LTS300 serial {serial} on {port}"
                    )
                    return True
                self._close_device(device)
                self.logger.debug(
                    f"Skipping LTS300 serial {serial} on {port}; "
                    f"expected {expected_serial}"
                )
            except Exception as exc:
                errors.append(f"{port}: {exc}")
                self.logger.debug(f"Could not inspect {port}: {exc}")

        raise DeviceNotFoundError(
            f"No LTS300 with serial {expected_serial} found",
            details={"serial_number": expected_serial, "ports": candidates, "errors": errors},
        )

    def _connect_to_port(self, port: str) -> bool:
        self.logger.info(f"Connecting to LTS300 on port {port}...")
        self.device = Thorlabs.KinesisMotor(port, scale="m")
        self.serial_no = str(self.device.get_device_info()[0])
        self.connected = True
        self.logger.info(f"Connected to Thorlabs LTS300 (S/N: {self.serial_no})")
        return True

    @staticmethod
    def _candidate_ports() -> list[str]:
        return sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))

    @staticmethod
    def _close_device(device) -> None:
        close = getattr(device, "close", None)
        if callable(close):
            close()

    @staticmethod
    def _resolve_symlink(port: str) -> str:
        if "/dev/serial/by-id/" not in port:
            return port
        return os.path.realpath(port)
