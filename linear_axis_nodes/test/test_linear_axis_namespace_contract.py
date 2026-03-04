"""Static checks for canonical linear-axis namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_lts300_node_registers_only_canonical_services():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "lts300_node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/" in content
    assert "register_service_alias_pair" not in content
    assert "/{self.config.namespace}/" not in content
    assert "from .helpers.lts300_interface import Lts300Interface" in content
    assert "from .services import ServiceHandlers" in content


def test_lts300_node_publishes_and_subscribes_with_canonical_topics():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "lts300_node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/{node_name}/position" in content
    assert "/promoc/linear_axis/lts300_" in content
    assert "other_axis_position_callback_legacy" not in content


def test_linear_axis_services_are_split_into_status_and_validation_modules():
    handler_content = (
        ROOT
        / "linear_axis_nodes"
        / "linear_axis_nodes"
        / "services"
        / "service_handlers.py"
    ).read_text(encoding="utf-8", errors="ignore")
    callbacks_path = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "services" / "callbacks.py"
    )
    status_content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "services" / "status.py"
    ).read_text(encoding="utf-8", errors="ignore")
    validation_content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "services" / "validation.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "from .status import OperationStatus" in handler_content
    assert "from .validation import LinearAxisValidator" in handler_content
    assert callbacks_path.exists() is False
    assert "class OperationStatus" in status_content
    assert "class LinearAxisValidator" in validation_content
