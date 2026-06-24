"""Focused tests for the bounded system-controller milestone."""

from __future__ import annotations

from pathlib import Path

from promoc_core import error_codes
from promoc_core.status import DeviceState
from promoc_core.system_controller import (
    KNOWN_DEVICE_NAMES,
    SystemStateStore,
    StopCallResult,
    StopEndpoint,
    device_state_name,
    execute_stop_requests,
    summarize_stop_results,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class _FakeFuture:
    """Small future stub for stop-call unit tests."""

    def __init__(
        self,
        *,
        done_after_checks: int = 0,
        response: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self._done_after_checks = int(done_after_checks)
        self._response = response
        self._error = error
        self._checks = 0

    def done(self) -> bool:
        self._checks += 1
        return self._checks > self._done_after_checks

    def result(self) -> object:
        if self._error is not None:
            raise self._error
        return self._response


class _FakeResponse:
    """Small service-response stub with the repo's common fields."""

    def __init__(self, *, success: bool, error_code: int, status_message: str) -> None:
        self.success = bool(success)
        self.error_code = int(error_code)
        self.status_message = str(status_message)


def test_store_initial_status_is_not_ready_when_statuses_are_missing() -> None:
    store = SystemStateStore()

    snapshot = store.compute_status(now=10.0)

    assert snapshot.state == int(DeviceState.NOT_READY)
    assert not snapshot.stop_latched
    assert not snapshot.all_required_present
    assert not snapshot.all_required_fresh
    assert snapshot.error_code == error_codes.REQUIRED_DEVICE_MISSING


def test_store_reports_ready_when_all_required_statuses_are_fresh_and_ready() -> None:
    store = SystemStateStore()
    for device_name in KNOWN_DEVICE_NAMES:
        store.observe(
            device_name,
            state=int(DeviceState.READY),
            error_code=error_codes.SUCCESS,
            message=f"{device_name} ready",
            received_at=5.0,
        )

    snapshot = store.compute_status(now=6.0)

    assert snapshot.state == int(DeviceState.READY)
    assert snapshot.all_required_present
    assert snapshot.all_required_fresh
    assert snapshot.error_code == error_codes.SUCCESS


def test_store_reports_not_ready_when_any_required_status_is_stale() -> None:
    store = SystemStateStore(status_timeout_sec=2.0)
    for device_name in KNOWN_DEVICE_NAMES:
        store.observe(
            device_name,
            state=int(DeviceState.READY),
            error_code=error_codes.SUCCESS,
            message=f"{device_name} ready",
            received_at=5.0,
        )

    snapshot = store.compute_status(now=8.5)

    assert snapshot.state == int(DeviceState.NOT_READY)
    assert snapshot.all_required_present
    assert not snapshot.all_required_fresh
    assert snapshot.error_code == error_codes.DEVICE_STATUS_STALE


def test_stop_latch_forces_stopped_state() -> None:
    store = SystemStateStore()
    store.latch_stop(
        error_code=error_codes.STOP_REQUESTED,
        message="system stop latched",
    )

    snapshot = store.compute_status(now=1.0)

    assert snapshot.state == int(DeviceState.STOPPED)
    assert snapshot.stop_latched
    assert snapshot.error_code == error_codes.STOP_REQUESTED


def test_reset_is_rejected_when_a_required_device_status_is_missing() -> None:
    store = SystemStateStore()
    store.observe(
        "camera",
        state=int(DeviceState.READY),
        error_code=error_codes.SUCCESS,
        message="camera ready",
        received_at=1.0,
    )

    can_reset, error_code, message = store.can_reset(now=1.5)

    assert not can_reset
    assert error_code == error_codes.REQUIRED_DEVICE_MISSING
    assert "missing status" in message


def test_reset_is_rejected_when_a_required_status_is_stale() -> None:
    store = SystemStateStore(status_timeout_sec=2.0)
    for device_name in KNOWN_DEVICE_NAMES:
        store.observe(
            device_name,
            state=int(DeviceState.READY),
            error_code=error_codes.SUCCESS,
            message=f"{device_name} ready",
            received_at=1.0,
        )

    can_reset, error_code, message = store.can_reset(now=4.5)

    assert not can_reset
    assert error_code == error_codes.DEVICE_STATUS_STALE
    assert "stale status" in message


def test_reset_is_rejected_when_a_device_is_busy() -> None:
    store = SystemStateStore()
    for device_name in KNOWN_DEVICE_NAMES:
        store.observe(
            device_name,
            state=int(DeviceState.READY),
            error_code=error_codes.SUCCESS,
            message=f"{device_name} ready",
            received_at=2.0,
        )
    store.observe(
        "x_axis",
        state=int(DeviceState.BUSY),
        error_code=error_codes.SUCCESS,
        message="x axis moving",
        received_at=2.0,
    )

    can_reset, error_code, message = store.can_reset(now=2.5)

    assert not can_reset
    assert error_code == error_codes.RESET_REJECTED_BUSY
    assert "busy device" in message


def test_reset_is_rejected_when_a_device_is_in_error() -> None:
    store = SystemStateStore()
    for device_name in KNOWN_DEVICE_NAMES:
        store.observe(
            device_name,
            state=int(DeviceState.READY),
            error_code=error_codes.SUCCESS,
            message=f"{device_name} ready",
            received_at=2.0,
        )
    store.observe(
        "planar_motor",
        state=int(DeviceState.ERROR),
        error_code=77,
        message="driver error",
        received_at=2.0,
    )

    can_reset, error_code, message = store.can_reset(now=2.5)

    assert not can_reset
    assert error_code == error_codes.RESET_REJECTED_ERROR
    assert "device error" in message


def test_reset_succeeds_only_when_all_required_devices_are_safe_and_fresh() -> None:
    store = SystemStateStore()
    store.latch_stop(
        error_code=error_codes.STOP_REQUESTED,
        message="stop latched",
    )
    for device_name in KNOWN_DEVICE_NAMES:
        store.observe(
            device_name,
            state=int(DeviceState.STOPPED if device_name != "camera" else DeviceState.READY),
            error_code=error_codes.SUCCESS,
            message=f"{device_name} safe",
            received_at=3.0,
        )

    can_reset, error_code, message = store.can_reset(now=3.5)

    assert can_reset
    assert error_code == error_codes.SUCCESS
    assert "safe states" in message


def test_execute_stop_requests_calls_every_configured_motion_service() -> None:
    called: list[str] = []
    responses = [
        _FakeResponse(success=True, error_code=0, status_message="x stopped"),
        _FakeResponse(success=True, error_code=0, status_message="z stopped"),
        _FakeResponse(success=True, error_code=0, status_message="planar stopped"),
    ]

    def _endpoint(device_name: str, response: _FakeResponse) -> StopEndpoint:
        def call_async(_request: object) -> _FakeFuture:
            called.append(device_name)
            return _FakeFuture(response=response)

        return StopEndpoint(
            device_name=device_name,
            wait_for_service=lambda _timeout: True,
            call_async=call_async,
            make_request=lambda: object(),
            is_safely_stopped=lambda: False,
        )

    results = execute_stop_requests(
        [
            _endpoint("x_axis", responses[0]),
            _endpoint("z_axis", responses[1]),
            _endpoint("planar_motor", responses[2]),
        ],
        timeout_sec=1.0,
        monotonic_fn=lambda: 10.0,
        sleep_fn=lambda _seconds: None,
    )

    assert called == ["x_axis", "z_axis", "planar_motor"]
    assert all(result.success for result in results)


def test_stop_requests_are_dispatched_before_waiting_for_slow_responses() -> None:
    called: list[str] = []
    time_values = iter([0.0, 0.1, 0.2, 1.2, 1.3])

    def _call_async(device_name: str, future: _FakeFuture):
        def caller(_request: object) -> _FakeFuture:
            called.append(device_name)
            return future

        return caller

    results = execute_stop_requests(
        [
            StopEndpoint(
                device_name="x_axis",
                wait_for_service=lambda _timeout: True,
                call_async=_call_async("x_axis", _FakeFuture(done_after_checks=100)),
                make_request=lambda: object(),
                is_safely_stopped=lambda: False,
                is_service_ready=lambda: True,
            ),
            StopEndpoint(
                device_name="z_axis",
                wait_for_service=lambda _timeout: True,
                call_async=_call_async(
                    "z_axis",
                    _FakeFuture(
                        response=_FakeResponse(
                            success=True,
                            error_code=0,
                            status_message="z stopped",
                        )
                    ),
                ),
                make_request=lambda: object(),
                is_safely_stopped=lambda: False,
                is_service_ready=lambda: True,
            ),
        ],
        timeout_sec=1.0,
        monotonic_fn=lambda: next(time_values),
        sleep_fn=lambda _seconds: None,
    )

    assert called == ["x_axis", "z_axis"]
    assert any(not result.success for result in results)


def test_partial_stop_failure_remains_visible_and_returns_failure() -> None:
    results = [
        StopCallResult("x_axis", True, 0, "accepted"),
        StopCallResult("z_axis", False, error_codes.STOP_REQUEST_FAILED, "driver rejected"),
    ]

    success, error_code, message = summarize_stop_results(results)

    assert not success
    assert error_code == error_codes.STOP_REQUEST_FAILED
    assert "partial failure" in message
    assert "driver rejected" in message


def test_stop_summary_succeeds_when_no_motion_devices_are_configured() -> None:
    success, error_code, message = summarize_stop_results([])

    assert success
    assert error_code == error_codes.STOP_REQUESTED
    assert "no motion devices configured" in message


def test_missing_stop_service_returns_meaningful_error() -> None:
    time_values = iter([0.0, 0.5, 1.1, 1.2])

    results = execute_stop_requests(
        [
            StopEndpoint(
                device_name="x_axis",
                wait_for_service=lambda _timeout: False,
                call_async=lambda _request: _FakeFuture(),
                make_request=lambda: object(),
                is_safely_stopped=lambda: False,
            )
        ],
        timeout_sec=1.0,
        monotonic_fn=lambda: next(time_values),
        sleep_fn=lambda _seconds: None,
    )

    assert results[0].error_code == error_codes.STOP_SERVICE_UNAVAILABLE
    assert "unavailable" in results[0].status_message


def test_stop_timeout_returns_meaningful_error() -> None:
    current_time = {"value": -0.25}

    def monotonic() -> float:
        current_time["value"] += 0.25
        return current_time["value"]

    results = execute_stop_requests(
        [
            StopEndpoint(
                device_name="planar_motor",
                wait_for_service=lambda _timeout: True,
                call_async=lambda _request: _FakeFuture(done_after_checks=100),
                make_request=lambda: object(),
                is_safely_stopped=lambda: False,
            )
        ],
        timeout_sec=1.0,
        monotonic_fn=monotonic,
        sleep_fn=lambda _seconds: None,
    )

    assert results[0].error_code == error_codes.STOP_REQUEST_TIMED_OUT
    assert "timed out" in results[0].status_message


def test_failed_stop_response_is_reported() -> None:
    results = execute_stop_requests(
        [
            StopEndpoint(
                device_name="z_axis",
                wait_for_service=lambda _timeout: True,
                call_async=lambda _request: _FakeFuture(
                    response=_FakeResponse(
                        success=False,
                        error_code=error_codes.STOP_REQUEST_FAILED,
                        status_message="axis driver rejected stop",
                    )
                ),
                make_request=lambda: object(),
                is_safely_stopped=lambda: False,
            )
        ],
        timeout_sec=1.0,
        monotonic_fn=lambda: 0.0,
        sleep_fn=lambda _seconds: None,
    )

    assert not results[0].success
    assert results[0].error_code == error_codes.STOP_REQUEST_FAILED
    assert "rejected stop" in results[0].status_message


def test_already_stopped_device_can_skip_a_stop_request() -> None:
    results = execute_stop_requests(
        [
            StopEndpoint(
                device_name="x_axis",
                wait_for_service=lambda _timeout: True,
                call_async=lambda _request: _FakeFuture(),
                make_request=lambda: object(),
                is_safely_stopped=lambda: True,
            )
        ],
        timeout_sec=1.0,
        monotonic_fn=lambda: 0.0,
        sleep_fn=lambda _seconds: None,
    )

    assert results[0].success
    assert results[0].status_message == "already safely stopped"


def test_device_state_name_returns_human_readable_names() -> None:
    assert device_state_name(int(DeviceState.READY)) == "READY"
    assert device_state_name(999) == "999"


def test_system_controller_yaml_parameter_names_match_defaults() -> None:
    config_path = REPO_ROOT / "promoc_core" / "config" / "system_controller.yaml"
    content = config_path.read_text(encoding="utf-8")

    parameter_names = (
        "required_devices",
        "camera_status_topic",
        "x_axis_status_topic",
        "z_axis_status_topic",
        "planar_motor_status_topic",
        "x_axis_stop_service",
        "z_axis_stop_service",
        "planar_motor_stop_service",
        "planar_motor_xbot_id",
        "status_timeout_sec",
        "service_call_timeout_sec",
        "status_publication_rate_hz",
    )
    for parameter_name in parameter_names:
        assert f"{parameter_name}:" in content


def test_reset_logic_does_not_call_motion_or_homing_services() -> None:
    source = (
        REPO_ROOT / "promoc_core" / "promoc_core" / "system_controller.py"
    ).read_text(encoding="utf-8")

    assert "move_absolute" not in source
    assert "move_relative" not in source
    assert "home" not in source
    assert "activate_xbots" not in source
