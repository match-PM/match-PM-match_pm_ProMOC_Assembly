"""Static checks for canonical and legacy mover namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mover_node_registers_canonical_and_legacy_services():
    content = (
        ROOT / "planar_motor_nodes" / "planar_motor_nodes" / "mover_node.py"
    ).read_text(encoding="utf-8", errors="ignore")
    helper_content = (
        ROOT / "promoc_core" / "promoc_core" / "service_alias.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/mover/" in content
    assert 'legacy_path = f"{self.get_name()}/{service_name}"' in content
    assert "register_service_alias_pair" in content
    assert "from .helpers.pmc_interface import PmcInterface" in content
    assert "from .helpers.mover_utils import MoverUtils" in content
    assert "from .services import ServiceCallbacks" in content
    assert "Deprecated service" in helper_content


def test_mover_node_publishes_canonical_and_legacy_xbot_info_topics():
    content = (
        ROOT / "planar_motor_nodes" / "planar_motor_nodes" / "mover_node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert 'XBotInfo, "xbot_info", 10' in content
    assert 'XBotInfo, "/promoc/mover/xbot_info", 10' in content
