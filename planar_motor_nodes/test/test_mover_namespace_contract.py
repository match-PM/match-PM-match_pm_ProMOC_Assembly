"""Static checks for canonical mover namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mover_node_keeps_canonical_service_namespace():
    registry = (
        ROOT
        / "planar_motor_nodes"
        / "planar_motor_nodes"
        / "services"
        / "registry.py"
    ).read_text(encoding="utf-8", errors="ignore")

    for service_name in (
        "linear_motion_si",
        "six_dof_motion",
        "activate_xbots",
        "levitation_xbots",
        "arc_motion_si",
        "stop_motion",
        "rotary_motion",
        "set_velocity_acceleration",
    ):
        assert service_name in registry


def test_mover_node_publishes_only_canonical_xbot_info_topic():
    content = (
        ROOT / "planar_motor_nodes" / "planar_motor_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert 'XBotInfo, "/promoc/mover/xbot_info", 10' in content
    assert 'XBotInfo, "xbot_info", 10' not in content


def test_runtime_uses_single_entry_point_and_multithreaded_executor():
    content = (
        ROOT / "planar_motor_nodes" / "planar_motor_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "create_planar_motor_driver" in content
    assert "ServiceHandlers" in content
    assert "MultiThreadedExecutor" in content
    assert "callback_group=group" in content
