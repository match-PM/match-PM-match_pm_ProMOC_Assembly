"""System-level monitoring and stop coordination for the ProMOC runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import threading
import time

from . import error_codes
from .status import DeviceState

try:  # pragma: no cover - exercised in integration tests after ROS setup.
    import rclpy
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
except ImportError:  # pragma: no cover - allows source-only unit tests.
    rclpy = None
    ReentrantCallbackGroup = None
    MultiThreadedExecutor = None
    Node = object
    DurabilityPolicy = None
    QoSProfile = None
    ReliabilityPolicy = None

try:  # pragma: no cover - exercised in integration tests after interface build.
    from promoc_assembly_interfaces.msg import DeviceStatus, SystemStatus, XBotInfo
    from promoc_assembly_interfaces.srv import Stop, StopMotion
except ImportError:  # pragma: no cover - allows source-only unit tests.
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

SAFE_RESET_STATES = {
    "camera": {
        int(DeviceState.CONNECTED),
        int(DeviceState.NOT_READY),
        int(DeviceState.READY),
        int(DeviceState.STOPPED),
    },
    "x_axis": {
        int(DeviceState.CONNECTED),
        int(DeviceState.NOT_READY),
        int(DeviceState.READY),
        int(DeviceState.STOPPED),
    },
    "z_axis": {
        int(DeviceState.CONNECTED),
        int(DeviceState.NOT_READY),
        int(DeviceState.READY),
        int(DeviceState.STOPPED),
    },
    "planar_motor": {
        int(DeviceState.CONNECTED),
        int(DeviceState.NOT_READY),
        int(DeviceState.READY),
        int(DeviceState.STOPPED),
    },
}

@dataclass(frozen=True)
class DeviceRecord:
    """Latest observed state for one monitored device."""

    state: int = int(DeviceState.DISCONNECTED)
    error_code: int = int(error_codes.SUCCESS)
    message: str = "no status received"
    has_message: bool = False
    received_at: float | None = None

    def is_fresh(self, now: float, timeout_sec: float) -> bool:
        """Return whether the record has a recent enough observation."""
        if not self.has_message or self.received_at is None:
            return False
        return (now - self.received_at) <= timeout_sec


@dataclass(frozen=True)
class SystemStatusSnapshot:
    """Minimal combined system status published by the controller."""

    state: int
    stop_latched: bool
    all_required_present: bool
    all_required_fresh: bool
    error_code: int
    message: str


@dataclass(frozen=True)
class StopCallResult:
    """Outcome of one motion-device stop request."""

    device_name: str
    success: bool
    error_code: int
    status_message: str


@dataclass(frozen=True)
class StopEndpoint:
    """Callables that let the pure stop helper drive one stop service."""

    device_name: str
    wait_for_service: Callable[[float], bool]
    call_async: Callable[[object], Any]
    make_request: Callable[[], object]
    is_safely_stopped: Callable[[], bool]
    is_service_ready: Callable[[], bool] | None = None


@dataclass(frozen=True)
class SystemControllerConfig:
    """Typed runtime configuration for the system controller."""

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
        """Declare and load all controller parameters."""
        node.declare_parameter("required_devices", list(KNOWN_DEVICE_NAMES))
        node.declare_parameter("camera_status_topic", "/promoc/camera/status")
        node.declare_parameter(
            "x_axis_status_topic",
            "/promoc/linear_axis/lts300_x_axis/status",
        )
        node.declare_parameter(
            "z_axis_status_topic",
            "/promoc/linear_axis/lts300_z_axis/status",
        )
        node.declare_parameter("planar_motor_status_topic", "/promoc/mover/xbot_info")
        node.declare_parameter(
            "x_axis_stop_service",
            "/promoc/linear_axis/lts300_x_axis/stop",
        )
        node.declare_parameter(
            "z_axis_stop_service",
            "/promoc/linear_axis/lts300_z_axis/stop",
        )
        node.declare_parameter("planar_motor_stop_service", "/promoc/mover/stop_motion")
        node.declare_parameter("planar_motor_xbot_id", 0)
        node.declare_parameter("status_timeout_sec", 2.0)
        node.declare_parameter("service_call_timeout_sec", 1.0)
        node.declare_parameter("status_publication_rate_hz", 10.0)

        required_devices = tuple(
            str(name) for name in node.get_parameter("required_devices").value
        )
        invalid_devices = sorted(set(required_devices) - set(KNOWN_DEVICE_NAMES))
        if invalid_devices:
            raise ValueError(
                f"required_devices contains unknown device names: {invalid_devices}"
            )

        return cls(
            required_devices=required_devices or KNOWN_DEVICE_NAMES,
            camera_status_topic=str(node.get_parameter("camera_status_topic").value),
            x_axis_status_topic=str(node.get_parameter("x_axis_status_topic").value),
            z_axis_status_topic=str(node.get_parameter("z_axis_status_topic").value),
            planar_motor_status_topic=str(
                node.get_parameter("planar_motor_status_topic").value
            ),
            x_axis_stop_service=str(node.get_parameter("x_axis_stop_service").value),
            z_axis_stop_service=str(node.get_parameter("z_axis_stop_service").value),
            planar_motor_stop_service=str(
                node.get_parameter("planar_motor_stop_service").value
            ),
            planar_motor_xbot_id=int(node.get_parameter("planar_motor_xbot_id").value),
            status_timeout_sec=max(
                0.1, float(node.get_parameter("status_timeout_sec").value)
            ),
            service_call_timeout_sec=max(
                0.1, float(node.get_parameter("service_call_timeout_sec").value)
            ),
            status_publication_rate_hz=max(
                0.1, float(node.get_parameter("status_publication_rate_hz").value)
            ),
        )


class SystemStateStore:
    """Pure-Python state store used by the ROS node and most unit tests."""

    def __init__(
        self,
        *,
        required_devices: tuple[str, ...] = KNOWN_DEVICE_NAMES,
        status_timeout_sec: float = 2.0,
    ) -> None:
        """Create an empty store for the configured required devices."""
        self.required_devices = tuple(required_devices)
        self.status_timeout_sec = float(status_timeout_sec)
        self._records = {name: DeviceRecord() for name in KNOWN_DEVICE_NAMES}
        self._lock = threading.RLock()
        self._stop_latched = False
        self._latched_error_code = int(error_codes.SUCCESS)
        self._latched_message = "system not stopped"

    @property
    def stop_latched(self) -> bool:
        """Return whether system stop is currently latched."""
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
        """Update the latest observation for one monitored device."""
        with self._lock:
            self._records[device_name] = DeviceRecord(
                state=int(state),
                error_code=int(error_code),
                message=str(message),
                has_message=True,
                received_at=float(received_at),
            )

    def record_for(self, device_name: str) -> DeviceRecord:
        """Return the latest stored record for the given device."""
        with self._lock:
            return self._records[device_name]

    def missing_devices(self) -> list[str]:
        """List required devices that have never published status."""
        with self._lock:
            return [
                name
                for name in self.required_devices
                if not self._records[name].has_message
            ]

    def stale_devices(self, now: float) -> list[str]:
        """List required devices whose statuses are missing or stale."""
        with self._lock:
            return [
                name
                for name in self.required_devices
                if self._records[name].has_message
                and not self._records[name].is_fresh(now, self.status_timeout_sec)
            ]

    def device_is_safely_stopped(self, device_name: str, now: float) -> bool:
        """Return whether a motion-capable device is confirmed STOPPED and fresh."""
        with self._lock:
            record = self._records[device_name]
            return (
                record.is_fresh(now, self.status_timeout_sec)
                and record.state == STOPPED_STATE
            )

    def latch_stop(self, *, error_code: int, message: str) -> None:
        """Latch the system-wide stop state with the latest stop summary."""
        with self._lock:
            self._stop_latched = True
            self._latched_error_code = int(error_code)
            self._latched_message = str(message)

    def update_latched_message(self, *, error_code: int, message: str) -> None:
        """Keep the stop latch active while updating its visible reason."""
        with self._lock:
            self._latched_error_code = int(error_code)
            self._latched_message = str(message)

    def clear_stop_latch(self) -> None:
        """Clear the latched stop state after a successful reset."""
        with self._lock:
            self._stop_latched = False
            self._latched_error_code = int(error_codes.SUCCESS)
            self._latched_message = "system stop cleared"

    def compute_status(self, now: float) -> SystemStatusSnapshot:
        """Compute the current combined system status."""
        with self._lock:
            missing = [
                name
                for name in self.required_devices
                if not self._records[name].has_message
            ]
            stale = [
                name
                for name in self.required_devices
                if self._records[name].has_message
                and not self._records[name].is_fresh(now, self.status_timeout_sec)
            ]
            all_present = not missing
            all_fresh = not missing and not stale

            if self._stop_latched:
                return SystemStatusSnapshot(
                    state=STOPPED_STATE,
                    stop_latched=True,
                    all_required_present=all_present,
                    all_required_fresh=all_fresh,
                    error_code=self._latched_error_code,
                    message=self._latched_message,
                )

            if missing:
                return SystemStatusSnapshot(
                    state=int(DeviceState.NOT_READY),
                    stop_latched=False,
                    all_required_present=False,
                    all_required_fresh=False,
                    error_code=int(error_codes.REQUIRED_DEVICE_MISSING),
                    message=f"missing status from: {', '.join(missing)}",
                )

            if stale:
                return SystemStatusSnapshot(
                    state=int(DeviceState.NOT_READY),
                    stop_latched=False,
                    all_required_present=True,
                    all_required_fresh=False,
                    error_code=int(error_codes.DEVICE_STATUS_STALE),
                    message=f"stale status from: {', '.join(stale)}",
                )

            error_devices = [
                name
                for name in self.required_devices
                if self._records[name].state == ERROR_STATE
            ]
            if error_devices:
                first = self._records[error_devices[0]]
                return SystemStatusSnapshot(
                    state=ERROR_STATE,
                    stop_latched=False,
                    all_required_present=True,
                    all_required_fresh=True,
                    error_code=first.error_code or int(error_codes.RESET_REJECTED_ERROR),
                    message=f"device error: {error_devices[0]} ({first.message})",
                )

            busy_devices = [
                name
                for name in self.required_devices
                if self._records[name].state == BUSY_STATE
            ]
            if busy_devices:
                return SystemStatusSnapshot(
                    state=BUSY_STATE,
                    stop_latched=False,
                    all_required_present=True,
                    all_required_fresh=True,
                    error_code=int(error_codes.SUCCESS),
                    message=f"busy device: {', '.join(busy_devices)}",
                )

            if all(
                self._records[name].state == READY_STATE
                for name in self.required_devices
            ):
                return SystemStatusSnapshot(
                    state=READY_STATE,
                    stop_latched=False,
                    all_required_present=True,
                    all_required_fresh=True,
                    error_code=int(error_codes.SUCCESS),
                    message="all required device statuses are fresh and ready",
                )

            return SystemStatusSnapshot(
                state=int(DeviceState.NOT_READY),
                stop_latched=False,
                all_required_present=True,
                all_required_fresh=True,
                error_code=int(error_codes.DEVICE_NOT_READY),
                message="all required statuses are present, but at least one device is not ready",
            )

    def can_reset(self, now: float) -> tuple[bool, int, str]:
        """Return whether `reset_stop` may safely clear the system latch."""
        with self._lock:
            missing = [
                name
                for name in self.required_devices
                if not self._records[name].has_message
            ]
            if missing:
                return (
                    False,
                    int(error_codes.REQUIRED_DEVICE_MISSING),
                    f"reset rejected: missing status from {', '.join(missing)}",
                )

            stale = [
                name
                for name in self.required_devices
                if self._records[name].has_message
                and not self._records[name].is_fresh(now, self.status_timeout_sec)
            ]
            if stale:
                return (
                    False,
                    int(error_codes.DEVICE_STATUS_STALE),
                    f"reset rejected: stale status from {', '.join(stale)}",
                )

            busy_devices = [
                name
                for name in self.required_devices
                if self._records[name].state == BUSY_STATE
            ]
            if busy_devices:
                return (
                    False,
                    int(error_codes.RESET_REJECTED_BUSY),
                    f"reset rejected: busy device {', '.join(busy_devices)}",
                )

            error_devices = [
                name
                for name in self.required_devices
                if self._records[name].state == ERROR_STATE
            ]
            if error_devices:
                return (
                    False,
                    int(error_codes.RESET_REJECTED_ERROR),
                    f"reset rejected: device error {', '.join(error_devices)}",
                )

            unsafe_devices = [
                name
                for name in self.required_devices
                if self._records[name].state not in SAFE_RESET_STATES[name]
            ]
            if unsafe_devices:
                return (
                    False,
                    int(error_codes.RESET_REJECTED_SAFETY_UNKNOWN),
                    f"reset rejected: safety state unknown for {', '.join(unsafe_devices)}",
                )

            return (
                True,
                int(error_codes.SUCCESS),
                "all required devices are fresh and in safe states",
            )


def execute_stop_requests(
    endpoints: list[StopEndpoint],
    *,
    timeout_sec: float,
    monotonic_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> list[StopCallResult]:
    """Dispatch motion stop requests concurrently and collect a bounded result."""
    results: list[StopCallResult] = []
    pending_endpoints: list[StopEndpoint] = []
    for endpoint in endpoints:
        if endpoint.is_safely_stopped():
            results.append(
                StopCallResult(
                    device_name=endpoint.device_name,
                    success=True,
                    error_code=int(error_codes.SUCCESS),
                    status_message="already safely stopped",
                )
            )
            continue
        pending_endpoints.append(endpoint)

    if not pending_endpoints:
        return results

    readiness_deadline = monotonic_fn() + timeout_sec
    ready_endpoints: list[StopEndpoint] = []
    waiting_endpoints = list(pending_endpoints)
    while waiting_endpoints and monotonic_fn() < readiness_deadline:
        still_waiting: list[StopEndpoint] = []
        for endpoint in waiting_endpoints:
            try:
                if endpoint.is_service_ready is not None:
                    service_ready = endpoint.is_service_ready()
                else:
                    service_ready = endpoint.wait_for_service(0.0)
            except Exception as exc:  # pragma: no cover - defensive
                results.append(
                    StopCallResult(
                        device_name=endpoint.device_name,
                        success=False,
                        error_code=int(error_codes.STOP_SERVICE_UNAVAILABLE),
                        status_message=f"service availability check failed: {exc}",
                    )
                )
                continue

            if service_ready:
                ready_endpoints.append(endpoint)
            else:
                still_waiting.append(endpoint)

        waiting_endpoints = still_waiting
        if waiting_endpoints:
            sleep_fn(0.01)

    for endpoint in waiting_endpoints:
        if endpoint.is_safely_stopped():
            results.append(
                StopCallResult(
                    device_name=endpoint.device_name,
                    success=True,
                    error_code=int(error_codes.SUCCESS),
                    status_message="already safely stopped",
                )
            )
        else:
            results.append(
                StopCallResult(
                    device_name=endpoint.device_name,
                    success=False,
                    error_code=int(error_codes.STOP_SERVICE_UNAVAILABLE),
                    status_message="stop service unavailable",
                )
            )

    pending_futures: dict[str, tuple[StopEndpoint, Any]] = {}
    for endpoint in ready_endpoints:
        try:
            pending_futures[endpoint.device_name] = (
                endpoint,
                endpoint.call_async(endpoint.make_request()),
            )
        except Exception as exc:
            results.append(
                StopCallResult(
                    device_name=endpoint.device_name,
                    success=False,
                    error_code=int(error_codes.STOP_REQUEST_FAILED),
                    status_message=f"stop request raised exception: {exc}",
                )
            )

    response_deadline = monotonic_fn() + timeout_sec
    while pending_futures and monotonic_fn() < response_deadline:
        completed = [
            device_name
            for device_name, (_endpoint, future) in pending_futures.items()
            if future.done()
        ]
        for device_name in completed:
            endpoint, future = pending_futures.pop(device_name)
            try:
                response = future.result()
            except Exception as exc:
                results.append(
                    StopCallResult(
                        device_name=endpoint.device_name,
                        success=False,
                        error_code=int(error_codes.STOP_REQUEST_FAILED),
                        status_message=f"stop request failed: {exc}",
                    )
                )
                continue

            if response.success:
                results.append(
                    StopCallResult(
                        device_name=endpoint.device_name,
                        success=True,
                        error_code=int(response.error_code),
                        status_message=str(response.status_message),
                    )
                )
                continue

            if endpoint.is_safely_stopped():
                results.append(
                    StopCallResult(
                        device_name=endpoint.device_name,
                        success=True,
                        error_code=int(error_codes.SUCCESS),
                        status_message="already safely stopped",
                    )
                )
                continue

            results.append(
                StopCallResult(
                    device_name=endpoint.device_name,
                    success=False,
                    error_code=int(response.error_code),
                    status_message=str(response.status_message),
                )
            )

        if pending_futures:
            sleep_fn(0.01)

    for device_name, (endpoint, future) in pending_futures.items():
        if future.done():
            try:
                response = future.result()
            except Exception as exc:
                results.append(
                    StopCallResult(
                        device_name=endpoint.device_name,
                        success=False,
                        error_code=int(error_codes.STOP_REQUEST_FAILED),
                        status_message=f"stop request failed: {exc}",
                    )
                )
                continue

            if response.success or endpoint.is_safely_stopped():
                results.append(
                    StopCallResult(
                        device_name=endpoint.device_name,
                        success=True,
                        error_code=int(response.error_code),
                        status_message=str(response.status_message),
                    )
                )
                continue

            results.append(
                StopCallResult(
                    device_name=device_name,
                    success=False,
                    error_code=int(response.error_code),
                    status_message=str(response.status_message),
                )
            )
            continue

        results.append(
            StopCallResult(
                device_name=device_name,
                success=False,
                error_code=int(error_codes.STOP_REQUEST_TIMED_OUT),
                status_message="stop request timed out",
            )
        )

    return results


def summarize_stop_results(results: list[StopCallResult]) -> tuple[bool, int, str]:
    """Turn individual stop-call outcomes into one service response."""
    if not results:
        return True, int(error_codes.STOP_REQUESTED), "stop_all succeeded (no motion devices configured)"

    failures = [result for result in results if not result.success]
    if not failures:
        summary = ", ".join(
            f"{result.device_name}: {result.status_message}" for result in results
        )
        return True, int(error_codes.STOP_REQUESTED), f"stop_all succeeded ({summary})"

    failure_summary = "; ".join(
        f"{result.device_name}: {result.status_message}" for result in failures
    )
    return (
        False,
        int(failures[0].error_code),
        f"stop_all partial failure ({failure_summary})",
    )


def device_state_name(state: int) -> str:
    """Return a readable state name for a numeric device-state value."""
    try:
        return DeviceState(int(state)).name
    except ValueError:
        return str(state)


def _ensure_ros_runtime() -> None:
    """Raise a clear error when the ROS runtime is unavailable."""
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
    """ROS node that monitors device status and coordinates stop/reset."""

    def __init__(self) -> None:
        """Initialize subscriptions, publishers, services, and stop clients."""
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

        self.create_subscription(
            DeviceStatus,
            self._config.camera_status_topic,
            self._handle_camera_status,
            10,
            callback_group=self._subscription_group,
        )
        self.create_subscription(
            DeviceStatus,
            self._config.x_axis_status_topic,
            self._make_status_handler("x_axis"),
            10,
            callback_group=self._subscription_group,
        )
        self.create_subscription(
            DeviceStatus,
            self._config.z_axis_status_topic,
            self._make_status_handler("z_axis"),
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
        """Return the monotonic time source used for freshness checks."""
        return time.monotonic()

    def _make_status_handler(self, device_name: str) -> Callable[[Any], None]:
        """Build a status callback for one plain `DeviceStatus` topic."""

        def handler(message: Any) -> None:
            self._store.observe(
                device_name,
                state=message.state,
                error_code=message.error_code,
                message=message.message,
                received_at=self._now(),
            )
            self.publish_status()

        return handler

    def _handle_camera_status(self, message: Any) -> None:
        """Store the latest camera status."""
        self._store.observe(
            "camera",
            state=message.state,
            error_code=message.error_code,
            message=message.message,
            received_at=self._now(),
        )
        self.publish_status()

    def _handle_planar_motor_status(self, message: Any) -> None:
        """Store the latest planar-motor status from `XBotInfo`."""
        self._store.observe(
            "planar_motor",
            state=message.device_status.state,
            error_code=message.device_status.error_code,
            message=message.device_status.message,
            received_at=self._now(),
        )
        self.publish_status()

    def publish_status(self) -> None:
        """Publish the current combined system status."""
        snapshot = self._store.compute_status(self._now())
        status_message = SystemStatus()
        status_message.stamp = self.get_clock().now().to_msg()
        status_message.state = snapshot.state
        status_message.stop_latched = snapshot.stop_latched
        status_message.all_required_present = snapshot.all_required_present
        status_message.all_required_fresh = snapshot.all_required_fresh
        status_message.error_code = snapshot.error_code
        status_message.message = snapshot.message
        self._status_publisher.publish(status_message)

    def _build_stop_endpoints(self) -> list[StopEndpoint]:
        """Create pure stop-call endpoints around the configured ROS clients."""
        endpoints = {
            "x_axis": StopEndpoint(
                device_name="x_axis",
                wait_for_service=self._x_axis_stop_client.wait_for_service,
                call_async=self._x_axis_stop_client.call_async,
                make_request=Stop.Request,
                is_safely_stopped=lambda: self._store.device_is_safely_stopped(
                    "x_axis", self._now()
                ),
                is_service_ready=self._x_axis_stop_client.service_is_ready,
            ),
            "z_axis": StopEndpoint(
                device_name="z_axis",
                wait_for_service=self._z_axis_stop_client.wait_for_service,
                call_async=self._z_axis_stop_client.call_async,
                make_request=Stop.Request,
                is_safely_stopped=lambda: self._store.device_is_safely_stopped(
                    "z_axis", self._now()
                ),
                is_service_ready=self._z_axis_stop_client.service_is_ready,
            ),
            "planar_motor": StopEndpoint(
                device_name="planar_motor",
                wait_for_service=self._planar_motor_stop_client.wait_for_service,
                call_async=self._planar_motor_stop_client.call_async,
                make_request=self._make_planar_motor_stop_request,
                is_safely_stopped=lambda: self._store.device_is_safely_stopped(
                    "planar_motor", self._now()
                ),
                is_service_ready=self._planar_motor_stop_client.service_is_ready,
            ),
        }
        return [
            endpoints[device_name]
            for device_name in MOTION_DEVICE_NAMES
            if device_name in self._config.required_devices
        ]

    def _make_planar_motor_stop_request(self) -> object:
        """Create a `StopMotion` request for the configured XBot."""
        request = StopMotion.Request()
        request.xbot_id = int(self._config.planar_motor_xbot_id)
        return request

    def _handle_stop_all(self, request: Any, response: Any) -> Any:
        """Latch STOPPED and forward stop requests to all motion devices."""
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
        """Clear the system stop latch only when safe fresh device state is known."""
        del request
        can_reset, error_code, message = self._store.can_reset(self._now())
        if not can_reset:
            self._store.update_latched_message(error_code=error_code, message=message)
            self.publish_status()
            response.success = False
            response.error_code = int(error_code)
            response.status_message = message
            return response

        self._store.clear_stop_latch()
        snapshot = self._store.compute_status(self._now())
        self.publish_status()
        response.success = True
        response.error_code = int(error_codes.SUCCESS)
        response.status_message = (
            f"system stop cleared; current state {device_state_name(snapshot.state)}"
        )
        return response


def main(args: list[str] | None = None) -> None:
    """Run the system controller node with a small multithreaded executor."""
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
