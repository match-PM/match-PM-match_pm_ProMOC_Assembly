"""Focused source-level checks for shared interface contracts."""

from __future__ import annotations

from pathlib import Path

from promoc_core.status import AxisState, DeviceState


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_device_status_message_matches_shared_enum_values() -> None:
    content = _read("promoc_assembly_interfaces/msg/DeviceStatus.msg")

    assert "uint8 DISCONNECTED=0" in content
    assert "uint8 CONNECTING=1" in content
    assert "uint8 CONNECTED=2" in content
    assert "uint8 NOT_READY=3" in content
    assert "uint8 READY=4" in content
    assert "uint8 BUSY=5" in content
    assert "uint8 STOPPED=6" in content
    assert "uint8 ERROR=7" in content

    assert DeviceState.DISCONNECTED == 0
    assert DeviceState.ERROR == 7


def test_axis_info_keeps_legacy_string_and_adds_shared_state() -> None:
    content = _read("promoc_assembly_interfaces/msg/linear_axis/LinearAxisInfo.msg")

    assert "string operation_status" in content
    assert "DeviceStatus device_status" in content
    assert "uint8 axis_state" in content
    assert AxisState.UNKNOWN == 0
    assert AxisState.UNHOMED == 1
    assert AxisState.HOMING == 2
    assert AxisState.HOMED == 3


def test_all_service_responses_expose_error_code() -> None:
    services = sorted((REPO_ROOT / "promoc_assembly_interfaces" / "srv").rglob("*.srv"))
    assert services

    for service_path in services:
        response_section = service_path.read_text(encoding="utf-8").split("---", 1)[1]
        assert "success" in response_section, service_path.as_posix()
        assert "error_code" in response_section, service_path.as_posix()


def test_system_status_message_matches_device_state_contract() -> None:
    content = _read("promoc_assembly_interfaces/msg/SystemStatus.msg")

    assert "uint8 DISCONNECTED=0" in content
    assert "uint8 CONNECTING=1" in content
    assert "uint8 CONNECTED=2" in content
    assert "uint8 NOT_READY=3" in content
    assert "uint8 READY=4" in content
    assert "uint8 BUSY=5" in content
    assert "uint8 STOPPED=6" in content
    assert "uint8 ERROR=7" in content
    assert "uint8 state" in content
    assert "bool stop_latched" in content
    assert "bool all_required_present" in content
    assert "bool all_required_fresh" in content
    assert "int32 error_code" in content
    assert "string message" in content
