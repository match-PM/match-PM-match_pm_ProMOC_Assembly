"""Static checks for canonical linear-axis namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


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
