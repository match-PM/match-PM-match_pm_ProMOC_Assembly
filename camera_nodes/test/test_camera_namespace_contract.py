"""Static checks for canonical service/topic namespace support."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_camera_node_registers_only_canonical_services():
    content = (ROOT / "camera_nodes" / "camera_nodes" / "node.py").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "/promoc/camera/autofocus" in content
    assert "/promoc/camera/autofocus_roi" in content
    assert "/promoc/camera/measure_mtf_center" in content
    assert "/promoc/camera/measure_mtf_roi" in content
    assert '"/promoc/camera/measure_mtf",' not in content
    assert "/promoc/camera/set_exposure" in content
    assert "/promoc/camera/autofocus_comparison" not in content
    assert "/promoc/camera/detect_rois" not in content
    assert "/promoc/camera/select_roi" not in content

    assert "/promoc/camera_node/" not in content
    assert "use_simulator" not in content
    assert "x_axis_node_name" not in content
    assert "SimulatedCameraDriver" not in content
    assert 'self.set_exposure_service = self.create_service(' in content
    assert "self.exposure_handler.manual_set_exposure_callback" in content


def test_legacy_callbacks_package_path_is_removed():
    callbacks_dir = ROOT / "camera_nodes" / "camera_nodes" / "callbacks"
    assert not callbacks_dir.exists()


def test_camera_axis_topic_uses_canonical_paths_only():
    node_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")
    sim_node_path = ROOT / "camera_nodes" / "camera_nodes" / "sim_node.py"
    sim_driver_path = ROOT / "camera_nodes" / "camera_nodes" / "drivers" / "sim.py"

    assert "/promoc/linear_axis/lts300_x_axis/position" in node_content
    assert "/promoc_assembly/" not in node_content
    assert "axis_position_callback_legacy_ns" not in node_content
    assert "axis_position_callback_legacy_float" not in node_content
    assert not sim_node_path.exists()
    assert not sim_driver_path.exists()
