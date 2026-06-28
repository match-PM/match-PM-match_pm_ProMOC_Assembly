"""Unified ROS 2 node for both ProMOC linear axes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import threading

from promoc_assembly_interfaces.msg import DeviceStatus
from promoc_assembly_interfaces.srv import (
    EmergencyStop,
    GetOperationStatus,
    GetPosition,
    GetVelocityParameters,
    Home,
    JogAxis,
    MoveAbsolute,
    MoveRelative,
    SetVelocityParameters,
    ShutdownLinearAxis,
    Stop,
)
from promoc_core import error_codes
from promoc_core.promoc_exceptions import (
    CommunicationError,
    ConnectionError,
    DriverNotAvailableError,
    MovementTimeoutError,
    ProMocError,
    SafetyError,
)
from promoc_core.status import AxisState, DeviceState
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Float64

from .config import LinearAxisConfig
from .drivers.hardware import ThorlabsLTS300Driver
from .drivers.sim import MockLinearAxisDriver


class AxisOperationError(Exception):
    """Structured controller error that maps directly to service responses."""

    def __init__(self, error_code: int, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass(frozen=True)
class AxisSnapshot:
    """Current state published and returned by query services."""

    connected: bool
    device_state: DeviceState
    axis_state: AxisState
    operation_status: str
    error_code: int
    status_message: str
    position_mm: float


class AxisController:
    """Gemeinsame Achsenlogik fuer X- und Z-Achsen-Instanzen.

    Verwaltet:
    - Verbindungsaufbau und Seriennummer-Verifikation
    - Bewegungssteuerung (absolute, relative, jog, homing)
    - Geschwindigkeitsprofile (get/set)
    - Stop-Mechanismus (einfaches Stop-Flag + Motion-Lock)
    - Zustandsverfolgung (DeviceState, AxisState)
    - Fehlermapping von Treiber-Exceptions auf AxisOperationError
    """

    def __init__(self, logger, config: LinearAxisConfig):
        self._logger = logger
        self._config = config
        self._driver = self._create_driver()
        self._state_lock = threading.Lock()    # Schuetzt Status-Felder
        self._motion_lock = threading.Lock()   # Verhindert parallele Bewegungen
        self._stop_requested = False
        self._connected = False
        self._device_state = DeviceState.DISCONNECTED
        self._axis_state = AxisState.UNKNOWN
        self._operation_status = "idle"
        self._error_code = error_codes.SUCCESS
        self._status_message = "Axis not connected"
        self._last_position = config.min_position
        self._connect()  # Verbinde sofort bei Initialisierung

    def _create_driver(self):
        # Waehle Treiber: Mock (in-process) oder ThorlabsLTS300 (echte Hardware)
        if self._config.driver_mode == "mock":
            self._logger.info("Using mock linear-axis driver")
            return MockLinearAxisDriver(self._logger, self._config)

        if self._config.driver_mode == "hardware":
            self._logger.info("Using Thorlabs LTS300 hardware driver")
            return ThorlabsLTS300Driver(
                self._logger,
                expected_serial=self._config.serial_number,
            )

        raise ValueError(
            "Unsupported driver_mode "
            f"'{self._config.driver_mode}'. Use 'hardware' or 'mock'."
        )

    def snapshot(self) -> AxisSnapshot:
        with self._state_lock:
            return AxisSnapshot(
                connected=self._connected,
                device_state=self._device_state,
                axis_state=self._axis_state,
                operation_status=self._operation_status,
                error_code=self._error_code,
                status_message=self._status_message,
                position_mm=self._last_position,
            )

    def serial_number(self) -> str:
        return self._config.serial_number

    def axis_id(self) -> str:
        return self._config.axis_id

    def get_position(self) -> float:
        self._require_connected()
        self._last_position = self._driver.get_position()
        return self._last_position

    def get_velocity_parameters(self) -> tuple[float, float, float]:
        self._require_connected()
        return self._driver.get_velocity_parameters()

    def set_velocity_parameters(
        self,
        min_velocity: float | None,
        acceleration: float | None,
        max_velocity: float | None,
    ) -> tuple[float, float, float]:
        self._require_connected()
        self._validate_velocity(min_velocity=min_velocity, max_velocity=max_velocity)
        self._validate_acceleration(acceleration)
        values = self._driver.set_velocity_parameters(
            min_velocity=min_velocity,
            acceleration=acceleration,
            max_velocity=max_velocity,
        )
        self._set_status(
            device_state=DeviceState.READY,
            operation_status="idle",
            error_code=error_codes.SUCCESS,
            status_message="Velocity parameters updated",
        )
        return values

    def home(self) -> None:
        self._require_connected()
        self._run_motion(
            operation_status="homing",
            busy_message="Homing axis",
            success_message="Axis homed",
            success_axis_state=AxisState.HOMED,
            operation=lambda: self._driver.home(timeout=self._config.homing_timeout),
            starting_axis_state=AxisState.HOMING,
            error_axis_state=AxisState.UNHOMED,
        )

    def move_absolute(self, target_position: float) -> float:
        self._require_connected()
        self._require_homed()
        self._validate_position(target_position)
        return self._run_motion(
            operation_status="moving",
            busy_message=f"Moving to {target_position:.3f} mm",
            success_message="Absolute move complete",
            success_axis_state=AxisState.HOMED,
            operation=lambda: self._driver.move_absolute(
                target_position,
                timeout=self._config.movement_timeout,
            ),
            error_axis_state=AxisState.HOMED,
        )

    def move_relative(self, distance: float) -> float:
        self._require_connected()
        self._require_homed()
        target_position = self.get_position() + distance
        self._validate_position(target_position)
        return self._run_motion(
            operation_status="moving",
            busy_message=f"Moving by {distance:.3f} mm",
            success_message="Relative move complete",
            success_axis_state=AxisState.HOMED,
            operation=lambda: self._driver.move_relative(
                distance,
                timeout=self._config.movement_timeout,
            ),
            error_axis_state=AxisState.HOMED,
        )

    def jog(self, step_size: float) -> float:
        self._require_connected()
        self._require_homed()
        target_position = self.get_position() + step_size
        self._validate_position(target_position)
        return self._run_motion(
            operation_status="jogging",
            busy_message=f"Jogging by {step_size:.3f} mm",
            success_message="Jog complete",
            success_axis_state=AxisState.HOMED,
            operation=lambda: self._driver.jog(
                step_size,
                timeout=self._config.movement_timeout,
            ),
            error_axis_state=AxisState.HOMED,
        )

    def stop(self) -> bool:
        self._require_connected()
        was_busy = self._motion_lock.locked() or self._driver.is_moving()
        self._stop_requested = True
        try:
            self._driver.stop()
        except Exception as exc:
            raise self._map_driver_error(exc) from exc

        if was_busy:
            self._set_status(
                device_state=DeviceState.STOPPED,
                operation_status="stopped",
                error_code=error_codes.STOP_REQUESTED,
                status_message="Stop requested",
            )
        else:
            self._set_status(
                device_state=DeviceState.READY,
                operation_status="idle",
                error_code=error_codes.SUCCESS,
                status_message="Axis already idle",
            )
        return was_busy

    def shutdown(self) -> None:
        if self._connected:
            if self._motion_lock.locked() or self._driver.is_moving():
                self._stop_requested = True
                try:
                    self._driver.stop()
                except Exception as exc:
                    self._logger.warning(f"Stop during shutdown failed: {exc}")
            try:
                self._driver.disconnect()
            finally:
                with self._state_lock:
                    self._connected = False
                    self._device_state = DeviceState.DISCONNECTED
                    self._operation_status = "idle"
                    self._status_message = "Axis disconnected"

    def _connect(self) -> None:
        # Verbindungsaufbau: Treiber verbinden, Seriennummer pruefen,
        # Default-Geschwindigkeiten setzen, Position abfragen.
        self._set_status(
            device_state=DeviceState.CONNECTING,
            operation_status="idle",
            error_code=error_codes.SUCCESS,
            status_message="Connecting to axis",
            axis_state=AxisState.UNKNOWN,
        )
        try:
            self._driver.connect(port=self._config.serial_port or None)
            serial = self._driver.get_serial_number()
            if self._config.serial_number and serial != self._config.serial_number:
                raise AxisOperationError(
                    error_codes.CONNECTION_FAILED,
                    (
                        "Connected serial number does not match configuration "
                        f"({serial} != {self._config.serial_number})"
                    ),
                )
            self._connected = True
            self._driver.set_velocity_parameters(
                min_velocity=0.0,
                acceleration=self._config.default_acceleration,
                max_velocity=self._config.default_velocity,
            )
            self._last_position = self._driver.get_position()
            self._set_status(
                device_state=DeviceState.READY,
                operation_status="idle",
                error_code=error_codes.SUCCESS,
                status_message="Connected; homing required",
                axis_state=AxisState.UNHOMED,
            )
        except AxisOperationError as exc:
            self._connected = False
            self._set_status(
                device_state=DeviceState.ERROR,
                operation_status="error",
                error_code=exc.error_code,
                status_message=exc.message,
                axis_state=AxisState.UNKNOWN,
            )
        except Exception as exc:
            self._connected = False
            mapped = self._map_driver_error(exc, connect_error=True)
            self._set_status(
                device_state=DeviceState.ERROR,
                operation_status="error",
                error_code=mapped.error_code,
                status_message=mapped.message,
                axis_state=AxisState.UNKNOWN,
            )

    def _run_motion(
        self,
        *,
        operation_status: str,
        busy_message: str,
        success_message: str,
        success_axis_state: AxisState,
        operation,
        starting_axis_state: AxisState | None = None,
        error_axis_state: AxisState | None = None,
    ) -> float:
        # Generische Bewegungsausfuehrung mit Locking und Fehlerbehandlung.
        # 1. Motion-Lock holen (nicht-blockierend -> DEVICE_BUSY wenn belegt)
        # 2. Status auf BUSY setzen, Stop-Flag zuruecksetzen
        # 3. Operation ausfuehren (Treiber-Aufruf)
        # 4. Stop-Flag pruefen (wurde waehrend der Fahrt Stop gerufen?)
        # 5. Bei Erfolg: Position aktualisieren, Status auf READY
        # 6. Bei Fehler: Exception mappen und Status setzen
        # 7. Lock in finally immer freigeben
        if not self._motion_lock.acquire(blocking=False):
            raise AxisOperationError(error_codes.DEVICE_BUSY, "Axis is already busy")

        self._stop_requested = False
        active_axis_state = starting_axis_state or self.snapshot().axis_state
        self._set_status(
            device_state=DeviceState.BUSY,
            operation_status=operation_status,
            error_code=error_codes.SUCCESS,
            status_message=busy_message,
            axis_state=active_axis_state,
        )
        try:
            operation()
            if self._stop_requested:
                raise AxisOperationError(
                    error_codes.STOP_REQUESTED,
                    f"{operation_status.capitalize()} stopped",
                )

            self._last_position = self._driver.get_position()
            self._set_status(
                device_state=DeviceState.READY,
                operation_status="idle",
                error_code=error_codes.SUCCESS,
                status_message=success_message,
                axis_state=success_axis_state,
            )
            return self._last_position
        except AxisOperationError as exc:
            self._apply_operation_error(
                exc,
                error_axis_state=error_axis_state or self.snapshot().axis_state,
            )
            raise
        except Exception as exc:
            mapped = self._map_driver_error(exc)
            self._apply_operation_error(
                mapped,
                error_axis_state=error_axis_state or self.snapshot().axis_state,
            )
            raise mapped from exc
        finally:
            self._motion_lock.release()

    def _apply_operation_error(
        self,
        exc: AxisOperationError,
        *,
        error_axis_state: AxisState,
    ) -> None:
        # Setzt den Status nach einem Bewegungsfehler.
        # STOP_REQUESTED -> STOPPED, DEVICE_BUSY/UNHOMED/TARGET_OUT_OF_RANGE -> READY,
        # alles andere -> ERROR.
        device_state = DeviceState.ERROR
        operation_status = "error"
        if exc.error_code == error_codes.STOP_REQUESTED:
            device_state = DeviceState.STOPPED
            operation_status = "stopped"
        elif exc.error_code in {
            error_codes.DEVICE_BUSY,
            error_codes.DEVICE_UNHOMED,
            error_codes.TARGET_OUT_OF_RANGE,
            error_codes.INVALID_PARAMETER,
        }:
            device_state = DeviceState.READY
            operation_status = "idle"

        self._set_status(
            device_state=device_state,
            operation_status=operation_status,
            error_code=exc.error_code,
            status_message=exc.message,
            axis_state=error_axis_state,
        )

    def _set_status(
        self,
        *,
        device_state: DeviceState,
        operation_status: str,
        error_code: int,
        status_message: str,
        axis_state: AxisState | None = None,
    ) -> None:
        with self._state_lock:
            self._device_state = device_state
            self._operation_status = operation_status
            self._error_code = error_code
            self._status_message = status_message
            if axis_state is not None:
                self._axis_state = axis_state

    def _require_connected(self) -> None:
        if not self._connected:
            raise AxisOperationError(
                error_codes.CONNECTION_FAILED,
                "Axis is not connected",
            )

    def _require_homed(self) -> None:
        if self.snapshot().axis_state != AxisState.HOMED:
            raise AxisOperationError(
                error_codes.DEVICE_UNHOMED,
                "Axis must be homed before movement",
            )

    def _validate_position(self, position: float) -> None:
        if position < self._config.min_position or position > self._config.max_position:
            raise AxisOperationError(
                error_codes.TARGET_OUT_OF_RANGE,
                (
                    f"Target {position:.3f} mm outside soft limits "
                    f"[{self._config.min_position:.3f}, "
                    f"{self._config.max_position:.3f}]"
                ),
            )

    def _validate_velocity(
        self,
        *,
        min_velocity: float | None,
        max_velocity: float | None,
    ) -> None:
        if min_velocity is not None and min_velocity < 0.0:
            raise AxisOperationError(
                error_codes.INVALID_PARAMETER,
                "min_velocity must be greater than or equal to 0",
            )
        if max_velocity is not None and max_velocity <= 0.0:
            raise AxisOperationError(
                error_codes.INVALID_PARAMETER,
                "max_velocity must be greater than 0",
            )

    def _validate_acceleration(self, acceleration: float | None) -> None:
        if acceleration is not None and acceleration <= 0.0:
            raise AxisOperationError(
                error_codes.INVALID_PARAMETER,
                "acceleration must be greater than 0",
            )

    def _map_driver_error(
        self,
        exc: Exception,
        *,
        connect_error: bool = False,
    ) -> AxisOperationError:
        # Kleine Zuordnung: Verbindung, Timeout, Safety/Parameter, Rest.
        if isinstance(exc, AxisOperationError):
            return exc
        if isinstance(exc, (DriverNotAvailableError, ConnectionError, CommunicationError)):
            return AxisOperationError(
                error_codes.CONNECTION_FAILED
                if connect_error
                else error_codes.CONNECTION_LOST,
                str(exc),
            )
        if isinstance(exc, MovementTimeoutError):
            return AxisOperationError(error_codes.MOVEMENT_TIMEOUT, str(exc))
        if isinstance(exc, SafetyError):
            return AxisOperationError(error_codes.TARGET_OUT_OF_RANGE, str(exc))
        if isinstance(exc, ValueError):
            return AxisOperationError(error_codes.INVALID_PARAMETER, str(exc))
        if isinstance(exc, ProMocError):
            return AxisOperationError(
                getattr(exc, "error_code", error_codes.MOVEMENT_FAILED),
                str(exc),
            )
        return AxisOperationError(error_codes.UNKNOWN_ERROR, str(exc))


class LTS300Node(Node):
    """Konfigurationsgetriebener ROS-Knoten fuer X- und Z-Linearachse.

    Der gleiche Node-Typ wird zweimal instanziiert (mit axis_id="x" bzw. "z"),
    jeweils mit eigenem Namespace und eigener Konfigurations-YAML.
    """

    def __init__(self):
        super().__init__("lts300_node")
        self.config = LinearAxisConfig.from_node(self)
        self.config.validate()
        self.controller = AxisController(self.get_logger(), self.config)

        # Callback-Gruppen: Bewegung parallel (Reentrant), Control/Status seriell
        self._movement_group = ReentrantCallbackGroup()
        self._control_group = MutuallyExclusiveCallbackGroup()
        self._state_group = MutuallyExclusiveCallbackGroup()

        # Basis-Topic: /promoc/linear_axis/lts300_<x|z>_axis
        base_topic = f"{self.get_namespace().rstrip('/')}/{self.get_name()}"
        self._base_topic = base_topic.replace("//", "/")

        self.position_publisher = self.create_publisher(
            Float64,
            f"{self._base_topic}/position",
            10,
        )
        self.status_publisher = self.create_publisher(
            DeviceStatus,
            f"{self._base_topic}/status",
            10,
        )

        period_s = 1.0 / self.config.state_publish_rate_hz
        self.create_timer(
            period_s,
            self.publish_state_and_position,
            callback_group=self._state_group,
        )

        self._create_services()
        self.publish_state()
        self.publish_position()

    def _create_services(self) -> None:
        self.create_service(
            MoveAbsolute,
            f"{self._base_topic}/move_absolute",
            self._handle_move_absolute,
            callback_group=self._movement_group,
        )
        self.create_service(
            MoveRelative,
            f"{self._base_topic}/move_relative",
            self._handle_move_relative,
            callback_group=self._movement_group,
        )
        self.create_service(
            Home,
            f"{self._base_topic}/home",
            self._handle_home,
            callback_group=self._movement_group,
        )
        self.create_service(
            JogAxis,
            f"{self._base_topic}/jog_axis",
            self._handle_jog_axis,
            callback_group=self._movement_group,
        )
        self.create_service(
            Stop,
            f"{self._base_topic}/stop",
            self._handle_stop,
            callback_group=self._control_group,
        )
        self.create_service(
            EmergencyStop,
            f"{self._base_topic}/emergency_stop",
            self._handle_emergency_stop,
            callback_group=self._control_group,
        )
        self.create_service(
            GetOperationStatus,
            f"{self._base_topic}/get_operation_status",
            self._handle_get_operation_status,
            callback_group=self._control_group,
        )
        self.create_service(
            GetPosition,
            f"{self._base_topic}/get_position",
            self._handle_get_position,
            callback_group=self._control_group,
        )
        self.create_service(
            GetVelocityParameters,
            f"{self._base_topic}/get_velocity_parameters",
            self._handle_get_velocity_parameters,
            callback_group=self._control_group,
        )
        self.create_service(
            SetVelocityParameters,
            f"{self._base_topic}/set_velocity_parameters",
            self._handle_set_velocity_parameters,
            callback_group=self._control_group,
        )
        self.create_service(
            ShutdownLinearAxis,
            f"{self._base_topic}/shutdown",
            self._handle_shutdown,
            callback_group=self._control_group,
        )

    def publish_state_and_position(self) -> None:
        self.publish_state()
        self.publish_position()

    def publish_position(self) -> None:
        try:
            position = self.controller.get_position()
        except AxisOperationError:
            position = self.controller.snapshot().position_mm
        msg = Float64()
        msg.data = position
        self.position_publisher.publish(msg)

    def publish_state(self) -> None:
        # Baut eine DeviceStatus-Nachricht mit Achsenzustand, Position und Status
        snapshot = self.controller.snapshot()
        msg = DeviceStatus()
        msg.stamp = self.get_clock().now().to_msg()
        msg.state = int(snapshot.device_state)
        msg.error_code = snapshot.error_code
        msg.message = (
            f"axis={self.config.axis_id} "
            f"axis_state={snapshot.axis_state.name.lower()} "
            f"operation={snapshot.operation_status} "
            f"{snapshot.status_message}"
        )
        self.status_publisher.publish(msg)

    def destroy_node(self) -> bool:
        # Sauberes Herunterfahren: Achse stoppen und Verbindung trennen
        self.controller.shutdown()
        return super().destroy_node()

    def _handle_home(self, request, response):
        _ = request
        try:
            self.controller.home()
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Operation completed successfully"
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
        return response

    def _handle_move_absolute(self, request, response):
        try:
            self.controller.move_absolute(request.axis_position)
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Operation completed successfully"
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
        return response

    def _handle_move_relative(self, request, response):
        try:
            self.controller.move_relative(request.axis_position)
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Operation completed successfully"
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
        return response

    def _handle_jog_axis(self, request, response):
        try:
            final_position = self.controller.jog(request.step_size)
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Jog complete"
            response.final_position = final_position
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
            response.final_position = self.controller.snapshot().position_mm
        return response

    def _handle_stop(self, request, response):
        _ = request
        try:
            self.controller.stop()
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Stop request accepted"
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
        return response

    def _handle_emergency_stop(self, request, response):
        _ = request
        try:
            was_moving = self.controller.stop()
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Emergency stop request accepted"
            response.was_moving = was_moving
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
            response.was_moving = False
        return response

    def _handle_get_operation_status(self, request, response):
        _ = request
        snapshot = self.controller.snapshot()
        response.success = True
        response.error_code = snapshot.error_code
        response.status_message = snapshot.status_message
        response.operation_status = snapshot.operation_status
        return response

    def _handle_get_position(self, request, response):
        _ = request
        try:
            position = self.controller.get_position()
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Position query succeeded"
            response.axis_position = position
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
            response.axis_position = self.controller.snapshot().position_mm
        return response

    def _handle_get_velocity_parameters(self, request, response):
        _ = request
        try:
            min_velocity, acceleration, max_velocity = (
                self.controller.get_velocity_parameters()
            )
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Velocity query succeeded"
            response.min_velocity = min_velocity
            response.acceleration = acceleration
            response.max_velocity = max_velocity
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
        return response

    def _handle_set_velocity_parameters(self, request, response):
        try:
            min_velocity, acceleration, max_velocity = (
                self.controller.set_velocity_parameters(
                    request.min_velocity,
                    request.acceleration,
                    request.max_velocity,
                )
            )
            response.success = True
            response.error_code = error_codes.SUCCESS
            response.status_message = "Velocity parameters updated"
            response.actual_min_velocity = min_velocity
            response.actual_acceleration = acceleration
            response.actual_max_velocity = max_velocity
        except AxisOperationError as exc:
            response.success = False
            response.error_code = exc.error_code
            response.status_message = exc.message
            response.actual_min_velocity = 0.0
            response.actual_acceleration = 0.0
            response.actual_max_velocity = 0.0
        return response

    def _handle_shutdown(self, request, response):
        _ = request
        self.controller.shutdown()
        response.success = True
        response.error_code = error_codes.SUCCESS
        response.status_message = "Axis disconnected"
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LTS300Node()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
