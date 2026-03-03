"""Static checks for canonical and legacy service namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_camera_node_registers_canonical_and_legacy_services():
    content = (ROOT / "camera_nodes" / "camera_nodes" / "camera_node.py").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "/promoc/camera/autofocus" in content
    assert "/promoc/camera/measure_mtf" in content
    assert "/promoc/camera/detect_rois" in content
    assert "/promoc/camera/set_exposure" in content

    assert "/promoc/camera_node/autofocus" in content
    assert "/promoc/camera_node/measure_mtf" in content
    assert "/promoc/camera_node/detect_rois" in content
    assert "/promoc/camera_node/set_exposure" in content


def test_camera_node_logs_deprecation_for_legacy_service_calls():
    content = (ROOT / "camera_nodes" / "camera_nodes" / "camera_node.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "Deprecated service" in content


def test_camera_axis_topic_supports_canonical_and_legacy_paths():
    node_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "camera_node.py"
    ).read_text(encoding="utf-8", errors="ignore")
    simulator_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "camera_simulator.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "/promoc/linear_axis/" in node_content
    assert "/promoc_assembly/" in node_content
    assert "axis_position_callback_legacy_ns" in node_content
    assert "axis_position_callback_legacy_float" in node_content
    assert "Deprecated topic '/" in node_content

    assert "/promoc/linear_axis/lts300_x_axis/position" in simulator_content
    assert "/promoc_assembly/lts300_x_axis/position" in simulator_content
    assert "position_callback_legacy" in simulator_content
