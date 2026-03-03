"""Static checks for canonical and legacy linear-axis namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_lts300_node_registers_canonical_and_legacy_services():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "lts300_node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/" in content
    assert "legacy_path = f" in content
    assert "{node_name}/{suffix}" in content
    assert "Deprecated service" in content


def test_lts300_node_publishes_and_subscribes_with_canonical_topics():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "lts300_node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/{node_name}/position" in content
    assert "/promoc/linear_axis/lts300_" in content
    assert "other_axis_position_callback_legacy" in content
    assert "Deprecated topic '/" in content
