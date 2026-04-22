<<<<<<< HEAD
"""Static checks for canonical mover namespace wiring."""
=======
"""Static checks for canonical mover namespace support."""
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


<<<<<<< HEAD
def test_system_launch_uses_promoc_mover_name():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'package="planar_motor_nodes"' in content
    assert 'name="mover"' in content
    assert 'namespace="promoc"' in content
=======
def test_mover_node_registers_only_canonical_services():
    content = (
        ROOT / "planar_motor_nodes" / "planar_motor_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/mover/" in content
    assert "register_service_alias_pair" not in content
    assert "from .drivers.hardware import PmcInterface" in content
    assert "from .services import MoverUtils, ServiceHandlers" in content


def test_mover_node_publishes_only_canonical_xbot_info_topic():
    content = (
        ROOT / "planar_motor_nodes" / "planar_motor_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert 'XBotInfo, "/promoc/mover/xbot_info", 10' in content
    assert 'XBotInfo, "xbot_info", 10' not in content


def test_mover_services_use_flat_service_modules():
    services_init = (
        ROOT / "planar_motor_nodes" / "planar_motor_nodes" / "services" / "__init__.py"
    ).read_text(encoding="utf-8", errors="ignore")
    handlers_module = (
        ROOT
        / "planar_motor_nodes"
        / "planar_motor_nodes"
        / "services"
        / "registry.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "from .motion import MotionCallbacks" in services_init
    assert "from .control import ControlCallbacks" in services_init
    assert "SERVICE_REGISTRY" in handlers_module
    assert "class ServiceHandlers:" in handlers_module
    assert "self._motion = MotionCallbacks" in handlers_module
    assert "self._control = ControlCallbacks" in handlers_module
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
