"""Optional system monitor and shared stop/reset coordinator.

The normal device nodes work without this node. Start the system controller only
when one process should publish the combined system state and offer one common
`stop_all` / guarded `reset_stop` service for the motion devices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import threading
import time

from . import error_codes
from .status import DeviceState

try:  # pragma: no cover - exercised after ROS setup.
    import rclpy
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
except ImportError:  # pragma: no cover - source-only unit tests.
    rclpy = None
    ReentrantCallbackGroup = None
    MultiThreadedExecutor = None
    Node = object
    DurabilityPolicy = None
    QoSProfile = None
    ReliabilityPolicy = None

try:  # pragma: no cover - exercised after interface build.
    from promoc_assembly_interfaces.msg import DeviceStatus, SystemStatus, XBotInfo
    from promoc_assembly_interfaces.srv import Stop, StopMotion
except ImportError:  # pragma: no cover - source-only unit tests.
    DeviceStatus = None
    SystemStatus = None
    XBotInfo = None
    Stop = None
    StopMotion = None


NODE_NAME = "promoc_system_controller"
NODE_NAMESPACE = "/promoc/system"

KNOWN_DEVICE_NAMES = ("camera", "x_axis", "z_axis", "planar_motor")
MOTION_DEVICE_NAMES = ("x_axis", "z_axis", "planar_motor")

READY_STATE = int(DeviceState.READY)
BUSY_STATE = int(DeviceState.BUSY)
STOPPED_STATE = int(DeviceState.STOPPED)
ERROR_STATE = int(DeviceState.ERROR)
NOT_READY_STATE = int(DeviceState.NOT_READY)
SUCCESS = int(error_codes.SUCCESS)

SAFE_RESET_STATES = {
    int(DeviceState.CONNECTED),
    NOT_READY_STATE,
    READY_STATE,
    STOPPED_STATE,
}

PARAMETER_DEFAULTS = {
    "required_devices": list(KNOWN_DEVICE_NAMES),
    "camera_status_topic": "/promoc/camera/status",
    "x_axis_status_topic": "/promoc/linear_axis/lts300_x_axis/status",
    "z_axis_status_topic": "/promoc/linear_axis/lts300_z_axis/status",
    "planar_motor_status_topic": "/promoc/mover/xbot_info",
    "x_axis_stop_service": "/promoc/linear_axis/lts300_x_axis/stop",
    "z_axis_stop_service": "/promoc/linear_axis/lts300_z_axis/stop",
    "planar_motor_stop_service": "/promoc/mover/stop_motion",
    "planar_motor_xbot_id": 0,
    "status_timeout_sec": 2.0,
    "service_call_timeout_sec": 1.0,
    "status_publication_rate_hz": 10.0,
}


@dataclass(frozen=True)
class DeviceRecord:
    """Last status received from one monitored device."""

    state: int = int(DeviceState.DISCONNECTED)
    error_code: int = SUCCESS
    message: str = "no status received"
    has_message: bool = False
    received_at: float | None = None

    def is_fresh(self, now: float, timeout_sec: float) -> bool:
        if not self.has_message or self.received_at is None:
            return False
        return (now - self.received_at) <= timeout_sec


@dataclass(frozen=True)
class SystemStatusSnapshot:
    """Small value object published as `SystemStatus` by the ROS node."""

    state: int
    stop_latched: bool
    all_required_present: bool
    all_required_fresh: bool
    error_code: int
    message: str


@dataclass(frozen=True)
class StopCallResult:
    """Result of one stop request to one motion device."""

    device_name: str
    success: bool
    error_code: int
    status_message: str


@dataclass(frozen=True)
class StopEndpoint:
    """Tiny adapter around a ROS stop client, kept pure for unit tests."""

    device_name: str
    wait_for_service: Callable[[float], bool]
    call_async: Callable[[object], Any]
    make_request: Callable[[], object]
    is_safely_stopped: Callable[[], bool]
    is_service_ready: Callable[[], bool] | None = None


@dataclass(frozen=True)
class SystemControllerConfig:
    """Runtime configuration loaded from ROS parameters."""

    required_devices: tuple[str, ...]
    camera_status_topic: str
    x_axis_status_topic: str
    z_axis_status_topic: str
    planar_motor_status_topic: str
    x_axis_stop_service: str
    z_axis_stop_service: str
    planar_motor_stop_service: str
    planar_motor_xbot_id: int
    status_timeout_sec: float
    service_call_timeout_sec: float
    status_publication_rate_hz: float

    @classmethod
    def from_node(cls, node: "SystemControllerNode") -> "SystemControllerConfig":
        for name, default in PARAMETER_DEFAULTS.items():
            node.declare_parameter(name, default)

        values = {name: node.get_parameter(name).value for name in PARAMETER_DEFAULTS}
        required_devices = tuple(str(name) for name in values["required_devices"])
        invalid_devices = sorted(set(required_devices) - set(KNOWN_DEVICE_NAMES))
        if invalid_devices:
            raise ValueError(
                f"required_devices contains unknown device names: {invalid_devices}"
            )

        return cls(
            required_devices=required_devices or KNOWN_DEVICE_NAMES,
            camera_status_topic=str(values["camera_status_topic"]),
            x_axis_status_topic=str(values["x_axis_status_topic"]),
            z_axis_status_topic=str(values["z_axis_status_topic"]),
            planar_motor_status_topic=str(values["planar_motor_status_topic"]),
            x_axis_stop_service=str(values["x_axis_stop_service"]),
            z_axis_stop_service=str(values["z_axis_stop_service"]),
            planar_motor_stop_service=str(values["planar_motor_stop_service"]),
            planar_motor_xbot_id=int(values["planar_motor_xbot_id"]),
            status_timeout_sec=max(0.1, float(values["status_timeout_sec"])),
            service_call_timeout_sec=max(
                0.1, float(values["service_call_timeout_sec"])
            ),
            status_publication_rate_hz=max(
                0.1, float(values["status_publication_rate_hz"])
            ),
        )


class SystemStateStore:
    """Thread-safe, ROS-free state machine for combined system status.

    It tracks the latest status per required device, latches `stop_all` until
    `reset_stop`, and rejects reset when the current device state is missing,
    stale, busy, in error, or otherwise not known safe.
    """

    def __init__(
        self,
        *,
        required_devices: tuple[str, ...] = KNOWN_DEVICE_NAMES,
        status_timeout_sec: float = 2.0,
    ) -> None:
        self.required_devices = tuple(required_devices)
        self.status_timeout_sec = float(status_timeout_sec)
        self._records = {name: DeviceRecord() for name in KNOWN_DEVICE_NAMES}
        self._lock = threading.RLock()
        self._stop_latched = False
        self._latched_error_code = SUCCESS
        self._latched_message = "system not stopped"

    @property
    def stop_latched(self) -> bool:
        with self._lock:
            return self._stop_latched

    def observe(
        self,
        device_name: str,
        *,
        state: int,
        error_code: int,
        message: str,
        received_at: float,
    ) -> None:
        with self._lock:
            self._records[device_name] = DeviceRecord(
                state=int(state),
                error_code=int(error_code),
                message=str(message),
                has_message=True,
                received_at=float(received_at),
            )

    def record_for(self, device_name: str) -> DeviceRecord:
        with self._lock:
            return self._records[device_name]

    def missing_devices(self) -> list[str]:
        with self._lock:
            return self._missing_devices()

    def stale_devices(self, now: float) -> list[str]:
        with self._lock:
            return self._stale_devices(now)

    def device_is_safely_stopped(self, device_name: str, now: float) -> bool:
        with self._lock:
            record = self._records[device_name]
            return (
                record.state == STOPPED_STATE
                and record.is_fresh(now, self.status_timeout_sec)
            )

    def latch_stop(self, *, error_code: int, message: str) -> None:
        with self._lock:
            self._stop_latched = True
            self._latched_error_code = int(error_code)
            self._latched_message = str(message)

    def update_latched_message(self, *, error_code: int, message: str) -> None:
        with self._lock:
            self._latched_error_code = int(error_code)
            self._latched_message = str(message)

    def clear_stop_latch(self) -> None:
        with self._lock:
            self._stop_latched = False
            self._latched_error_code = SUCCESS
            self._latched_message = "system stop cleared"

    def compute_status(self, now: float) -> SystemStatusSnapshot:
        with self._lock:
            missing = self._missing_devices()
            stale = self._stale_devices(now)
            all_present = not missing
            all_fresh = all_present and not stale

            if self._stop_latched:
                return self._snapshot(
                    STOPPED_STATE,
                    self._latched_error_code,
                    self._latched_message,
                    stop_latched=True,
                    all_present=all_present,
                    all_fresh=all_fresh,
                )
            if missing:
                return self._snapshot(
                    NOT_READY_STATE,
                    int(error_codes.REQUIRED_DEVICE_MISSING),
                    f"missing status from: {', '.join(missing)}",
                    all_present=False,
                    all_fresh=False,
                )
            if stale:
                return self._snapshot(
                    NOT_READY_STATE,
                    int(error_codes.DEVICE_STATUS_STALE),
                    f"stale status from: {', '.join(stale)}",
                    all_fresh=False,
                )

            error_devices = self._devices_with_state(ERROR_STATE)
            if error_devices:
                first = self._records[error_devices[0]]
                return self._snapshot(
                    ERROR_STATE,
                    first.error_code or int(error_codes.RESET_REJECTED_ERROR),
                    f"device error: {error_devices[0]} ({first.message})",
                )

            busy_devices = self._devices_with_state(BUSY_STATE)
            if busy_devices:
                return self._snapshot(
                    BUSY_STATE,
                    SUCCESS,
                    f"busy device: {', '.join(busy_devices)}",
                )

            if all(self._records[name].state == READY_STATE for name in self.required_devices):
                return self._snapshot(
                    READY_STATE,
                    SUCCESS,
                    "all required device statuses are fresh and ready",
                )

            return self._snapshot(
                NOT_READY_STATE,
                int(error_codes.DEVICE_NOT_READY),
                "all required statuses are present, but at least one device is not ready",
            )

    def can_reset(self, now: float) -> tuple[bool, int, str]:
        with self._lock:
            checks = (
                (
                    self._missing_devices(),
                    int(error_codes.REQUIRED_DEVICE_MISSING),
                    "missing status from",
                ),
                (
                    self._stale_devices(now),
                    int(error_codes.DEVICE_STATUS_STALE),
                    "stale status from",
                ),
                (
                    self._devices_with_state(BUSY_STATE),
                    int(error_codes.RESET_REJECTED_BUSY),
                    "busy device",
                ),
                (
                    self._devices_with_state(ERROR_STATE),
                    int(error_codes.RESET_REJECTED_ERROR),
                    "device error",
                ),
                (
                    [
                        name
                        for name in self.required_devices
                        if self._records[name].state not in SAFE_RESET_STATES
                    ],
                    int(error_codes.RESET_REJECTED_SAFETY_UNKNOWN),
                    "safety state unknown for",
                ),
            )
            for devices, error_code, reason in checks:
                if devices:
                    return False, error_code, f"reset rejected: {reason} {', '.join(devices)}"

            return True, SUCCESS, "all required devices are fresh and in safe states"

    def _missing_devices(self) -> list[str]:
        return [
            name
            for name in self.required_devices
            if not self._records[name].has_message
        ]

    def _stale_devices(self, now: float) -> list[str]:
        return [
            name
            for name in self.required_devices
            if self._records[name].has_message
            and not self._records[name].is_fresh(now, self.status_timeout_sec)
        ]

    def _devices_with_state(self, state: int) -> list[str]:
        return [
            name
            for name in self.required_devices
            if self._records[name].state == state
        ]

    def _snapshot(
        self,
        state: int,
        error_code: int,
        message: str,
        *,
        stop_latched: bool = False,
        all_present: bool = True,
        all_fresh: bool = True,
    ) -> SystemStatusSnapshot:
        return SystemStatusSnapshot(
            state=int(state),
            stop_latched=bool(stop_latched),
            all_required_present=bool(all_present),
            all_required_fresh=bool(all_fresh),
            error_code=int(error_code),
            message=str(message),
        )


def execute_stop_requests(
    endpoints: list[StopEndpoint],
    *,
    timeout_sec: float,
    monotonic_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> list[StopCallResult]:
    """Send stop requests to all motion devices and collect one result per device."""
    results: list[StopCallResult] = []
    endpoints = _skip_already_stopped(endpoints, results)
    if not endpoints:
        return results

    ready, unavailable = _wait_for_ready_services(
        endpoints,
        timeout_sec=timeout_sec,
        monotonic_fn=monotonic_fn,
        sleep_fn=sleep_fn,
    )
    results.extend(unavailable)

    pending: dict[str, tuple[StopEndpoint, Any]] = {}
    for endpoint in ready:
        try:
            pending[endpoint.device_name] = (
                endpoint,
                endpoint.call_async(endpoint.make_request()),
            )
        except Exception as exc:
            results.append(
                StopCallResult(
                    endpoint.device_name,
                    False,
                    int(error_codes.STOP_REQUEST_FAILED),
                    f"stop request raised exception: {exc}",
                )
            )

    deadline = monotonic_fn() + timeout_sec
    while pending and monotonic_fn() < deadline:
        for device_name in [
            name for name, (_endpoint, future) in pending.items() if future.done()
        ]:
            endpoint, future = pending.pop(device_name)
            results.append(_result_from_future(endpoint, future))
        if pending:
            sleep_fn(0.01)

    for device_name, (endpoint, future) in pending.items():
        if future.done():
            results.append(_result_from_future(endpoint, future))
        else:
            results.append(
                StopCallResult(
                    device_name,
                    False,
                    int(error_codes.STOP_REQUEST_TIMED_OUT),
                    "stop request timed out",
                )
            )

    return results


def _skip_already_stopped(
    endpoints: list[StopEndpoint],
    results: list[StopCallResult],
) -> list[StopEndpoint]:
    pending: list[StopEndpoint] = []
    for endpoint in endpoints:
        if endpoint.is_safely_stopped():
            results.append(_already_stopped_result(endpoint.device_name))
        else:
            pending.append(endpoint)
    return pending


def _wait_for_ready_services(
    endpoints: list[StopEndpoint],
    *,
    timeout_sec: float,
    monotonic_fn: Callable[[], float],
    sleep_fn: Callable[[float], None],
) -> tuple[list[StopEndpoint], list[StopCallResult]]:
    ready: list[StopEndpoint] = []
    unavailable: list[StopCallResult] = []
    waiting = list(endpoints)
    deadline = monotonic_fn() + timeout_sec

    while waiting and monotonic_fn() < deadline:
        still_waiting: list[StopEndpoint] = []
        for endpoint in waiting:
            try:
                service_ready = (
                    endpoint.is_service_ready()
                    if endpoint.is_service_ready is not None
                    else endpoint.wait_for_service(0.0)
                )
            except Exception as exc:
                unavailable.append(
                    StopCallResult(
                        endpoint.device_name,
                        False,
                        int(error_codes.STOP_SERVICE_UNAVAILABLE),
                        f"service availability check failed: {exc}",
                    )
                )
                continue

            if service_ready:
                ready.append(endpoint)
            else:
                still_waiting.append(endpoint)

        waiting = still_waiting
        if waiting:
            sleep_fn(0.01)

    for endpoint in waiting:
        if endpoint.is_safely_stopped():
            unavailable.append(_already_stopped_result(endpoint.device_name))
        else:
            unavailable.append(
                StopCallResult(
                    endpoint.device_name,
                    False,
                    int(error_codes.STOP_SERVICE_UNAVAILABLE),
                    "stop service unavailable",
                )
            )

    return ready, unavailable


def _result_from_future(endpoint: StopEndpoint, future: Any) -> StopCallResult:
    try:
        response = future.result()
    except Exception as exc:
        return StopCallResult(
            endpoint.device_name,
            False,
            int(error_codes.STOP_REQUEST_FAILED),
            f"stop request failed: {exc}",
        )

    if response.success:
        return StopCallResult(
            endpoint.device_name,
            True,
            int(response.error_code),
            str(response.status_message),
        )

    if endpoint.is_safely_stopped():
        return _already_stopped_result(endpoint.device_name)

    return StopCallResult(
        endpoint.device_name,
        False,
        int(response.error_code),
        str(response.status_message),
    )


def _already_stopped_result(device_name: str) -> StopCallResult:
    return StopCallResult(
        device_name,
        True,
        SUCCESS,
        "already safely stopped",
    )


def summarize_stop_results(results: list[StopCallResult]) -> tuple[bool, int, str]:
    """Create the `Stop` service response from all individual stop results."""
    if not results:
        return True, int(error_codes.STOP_REQUESTED), "stop_all succeeded (no motion devices configured)"

    failures = [result for result in results if not result.success]
    if failures:
        failure_summary = "; ".join(
            f"{result.device_name}: {result.status_message}" for result in failures
        )
        return (
            False,
            int(failures[0].error_code),
            f"stop_all partial failure ({failure_summary})",
        )

    summary = ", ".join(
        f"{result.device_name}: {result.status_message}" for result in results
    )
    return True, int(error_codes.STOP_REQUESTED), f"stop_all succeeded ({summary})"


def device_state_name(state: int) -> str:
    """Return a readable state name for a numeric device-state value."""
    try:
        return DeviceState(int(state)).name
    except ValueError:
        return str(state)


def _ensure_ros_runtime() -> None:
    if (
        rclpy is None
        or ReentrantCallbackGroup is None
        or MultiThreadedExecutor is None
        or Node is object
        or QoSProfile is None
        or ReliabilityPolicy is None
        or DurabilityPolicy is None
        or DeviceStatus is None
        or SystemStatus is None
        or XBotInfo is None
        or Stop is None
        or StopMotion is None
    ):
        raise RuntimeError(
            "ROS 2 runtime or generated promoc_assembly_interfaces are unavailable"
        )


class SystemControllerNode(Node):
    """ROS wrapper around `SystemStateStore`.

    The node subscribes to device status topics, publishes `/promoc/system/status`,
    forwards `stop_all` to all configured motion devices, and clears the stop
    latch only when fresh safe device states are known.
    """

    def __init__(self) -> None:
        _ensure_ros_runtime()
        super().__init__(NODE_NAME, namespace=NODE_NAMESPACE)
        self._config = SystemControllerConfig.from_node(self)
        self._store = SystemStateStore(
            required_devices=self._config.required_devices,
            status_timeout_sec=self._config.status_timeout_sec,
        )

        self._subscription_group = ReentrantCallbackGroup()
        self._service_group = ReentrantCallbackGroup()
        self._client_group = ReentrantCallbackGroup()

        self._status_publisher = self.create_publisher(
            SystemStatus,
            "status",
            QoSProfile(
                depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )
        self._create_status_subscriptions()
        self._create_stop_clients()

        self.create_service(
            Stop,
            "stop_all",
            self._handle_stop_all,
            callback_group=self._service_group,
        )
        self.create_service(
            Stop,
            "reset_stop",
            self._handle_reset_stop,
            callback_group=self._service_group,
        )
        self.create_timer(
            1.0 / self._config.status_publication_rate_hz,
            self.publish_status,
            callback_group=self._subscription_group,
        )
        self.publish_status()

    def _now(self) -> float:
        return time.monotonic()

    def _create_status_subscriptions(self) -> None:
        plain_status_topics = {
            "camera": self._config.camera_status_topic,
            "x_axis": self._config.x_axis_status_topic,
            "z_axis": self._config.z_axis_status_topic,
        }
        for device_name, topic in plain_status_topics.items():
            self.create_subscription(
                DeviceStatus,
                topic,
                self._make_status_handler(device_name),
                10,
                callback_group=self._subscription_group,
            )
        self.create_subscription(
            XBotInfo,
            self._config.planar_motor_status_topic,
            self._handle_planar_motor_status,
            10,
            callback_group=self._subscription_group,
        )

    def _create_stop_clients(self) -> None:
        self._x_axis_stop_client = self.create_client(
            Stop,
            self._config.x_axis_stop_service,
            callback_group=self._client_group,
        )
        self._z_axis_stop_client = self.create_client(
            Stop,
            self._config.z_axis_stop_service,
            callback_group=self._client_group,
        )
        self._planar_motor_stop_client = self.create_client(
            StopMotion,
            self._config.planar_motor_stop_service,
            callback_group=self._client_group,
        )

    def _make_status_handler(self, device_name: str) -> Callable[[Any], None]:
        def handler(message: Any) -> None:
            self._observe_device(
                device_name,
                state=message.state,
                error_code=message.error_code,
                message=message.message,
            )

        return handler

    def _handle_planar_motor_status(self, message: Any) -> None:
        self._observe_device(
            "planar_motor",
            state=message.device_status.state,
            error_code=message.device_status.error_code,
            message=message.device_status.message,
        )

    def _observe_device(
        self,
        device_name: str,
        *,
        state: int,
        error_code: int,
        message: str,
    ) -> None:
        self._store.observe(
            device_name,
            state=state,
            error_code=error_code,
            message=message,
            received_at=self._now(),
        )
        self.publish_status()

    def publish_status(self) -> None:
        snapshot = self._store.compute_status(self._now())
        message = SystemStatus()
        message.stamp = self.get_clock().now().to_msg()
        message.state = snapshot.state
        message.stop_latched = snapshot.stop_latched
        message.all_required_present = snapshot.all_required_present
        message.all_required_fresh = snapshot.all_required_fresh
        message.error_code = snapshot.error_code
        message.message = snapshot.message
        self._status_publisher.publish(message)

    def _build_stop_endpoints(self) -> list[StopEndpoint]:
        clients = {
            "x_axis": (
                self._x_axis_stop_client,
                Stop.Request,
            ),
            "z_axis": (
                self._z_axis_stop_client,
                Stop.Request,
            ),
            "planar_motor": (
                self._planar_motor_stop_client,
                self._make_planar_motor_stop_request,
            ),
        }
        endpoints: list[StopEndpoint] = []
        for device_name in MOTION_DEVICE_NAMES:
            if device_name not in self._config.required_devices:
                continue
            client, make_request = clients[device_name]
            endpoints.append(
                StopEndpoint(
                    device_name=device_name,
                    wait_for_service=client.wait_for_service,
                    call_async=client.call_async,
                    make_request=make_request,
                    is_safely_stopped=lambda name=device_name: (
                        self._store.device_is_safely_stopped(name, self._now())
                    ),
                    is_service_ready=client.service_is_ready,
                )
            )
        return endpoints

    def _make_planar_motor_stop_request(self) -> object:
        request = StopMotion.Request()
        request.xbot_id = int(self._config.planar_motor_xbot_id)
        return request

    def _handle_stop_all(self, request: Any, response: Any) -> Any:
        del request
        self._store.latch_stop(
            error_code=int(error_codes.STOP_REQUESTED),
            message="system stop latched; coordinating device stop requests",
        )
        self.publish_status()

        results = execute_stop_requests(
            self._build_stop_endpoints(),
            timeout_sec=self._config.service_call_timeout_sec,
        )
        success, error_code, message = summarize_stop_results(results)
        self._store.update_latched_message(error_code=error_code, message=message)
        self.publish_status()

        response.success = bool(success)
        response.error_code = int(error_code)
        response.status_message = message
        return response

    def _handle_reset_stop(self, request: Any, response: Any) -> Any:
        del request
        can_reset, error_code, message = self._store.can_reset(self._now())
        if can_reset:
            self._store.clear_stop_latch()
            snapshot = self._store.compute_status(self._now())
            message = (
                f"system stop cleared; current state "
                f"{device_state_name(snapshot.state)}"
            )
        else:
            self._store.update_latched_message(error_code=error_code, message=message)

        self.publish_status()
        response.success = bool(can_reset)
        response.error_code = int(error_code)
        response.status_message = message
        return response


def main(args: list[str] | None = None) -> None:
    _ensure_ros_runtime()
    rclpy.init(args=args)
    node = SystemControllerNode()
    executor = MultiThreadedExecutor(num_threads=4)
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
