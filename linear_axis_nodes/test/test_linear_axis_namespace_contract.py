<<<<<<< HEAD
"""Static checks for canonical linear-axis namespace wiring."""
=======
"""Static checks for canonical linear-axis namespace support."""
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


<<<<<<< HEAD
def test_system_launch_applies_linear_axis_namespace():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'namespace="promoc/linear_axis"' in content
    assert '"namespace": "promoc/linear_axis"' in content


def test_optical_launch_applies_linear_axis_namespace():
    content = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert 'namespace="promoc/linear_axis"' in content
    assert '"namespace": "promoc/linear_axis"' in content
=======
def test_lts300_node_registers_only_canonical_services():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/" in content
    assert "register_service_alias_pair" not in content
    assert "self.config.namespace" not in content
    assert "from .drivers import create_linear_axis_driver, connect_linear_axis_driver" in content
    assert "from .services import ServiceHandlers" in content


def test_lts300_node_publishes_and_subscribes_with_canonical_topics():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/{node_name}/position" in content
    assert "/promoc/linear_axis/lts300_" in content
    assert "other_axis_position_callback_legacy" not in content


def test_linear_axis_services_use_models_and_flat_service_modules():
    registry_content = (
        ROOT
        / "linear_axis_nodes"
        / "linear_axis_nodes"
        / "services"
        / "registry.py"
    ).read_text(encoding="utf-8", errors="ignore")
    models_content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "models.py"
    ).read_text(encoding="utf-8", errors="ignore")
    validation_content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "services" / "validation.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "from ..models import OperationStateStore, OperationStatus" in registry_content
    assert "from .motion import LinearMotionCallbacks" in registry_content
    assert "from .admin import LinearAdminCallbacks" in registry_content
    assert "class OperationStatus" in models_content
    assert "class OperationStateStore" in models_content
    assert "class LinearAxisValidator" in validation_content
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
