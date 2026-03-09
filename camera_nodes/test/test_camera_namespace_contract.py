"""Static checks for canonical service/topic namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_camera_node_registers_only_canonical_services():
    content = (ROOT / "camera_nodes" / "camera_nodes" / "node.py").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "/promoc/camera/autofocus" in content
    assert "/promoc/camera/measure_mtf" in content
    assert "/promoc/camera/detect_rois" in content
    assert "/promoc/camera/set_exposure" in content

    assert "/promoc/camera_node/" not in content


def test_camera_axis_topic_uses_canonical_paths_only():
    node_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")
    simulator_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "sim_node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/" in node_content
    assert "/promoc_assembly/" not in node_content
    assert "axis_position_callback_legacy_ns" not in node_content
    assert "axis_position_callback_legacy_float" not in node_content

    assert "/promoc/linear_axis/lts300_x_axis/position" in simulator_content
    assert "/promoc_assembly/lts300_x_axis/position" not in simulator_content
    assert "position_callback_legacy" not in simulator_content


