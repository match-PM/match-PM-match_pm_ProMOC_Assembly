"""Static checks for the reduced camera runtime contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_camera_node_publishes_canonical_topics_only():
    node_content = (ROOT / "camera_nodes" / "camera_nodes" / "node.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    config_content = (ROOT / "camera_nodes" / "camera_nodes" / "config.py").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "/promoc/camera/image_raw" in config_content
    assert "/promoc/camera/status" in config_content
    assert "/promoc/camera/autofocus" not in node_content
    assert "/promoc/camera/set_exposure" not in node_content
    assert "/promoc/camera/measure_mtf" not in node_content
    assert "cv_bridge" not in node_content


def test_camera_runtime_uses_one_active_entry_point():
    setup_content = (ROOT / "camera_nodes" / "setup.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    launch_content = (ROOT / "promoc_bringup" / "launch" / "camera.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "camera_node = camera_nodes.node:main" in setup_content
    assert "camera_simulator" not in setup_content
    assert 'executable="camera_node"' in launch_content
    assert "camera_simulator" not in launch_content


def test_removed_runtime_paths_are_not_imported():
    node_content = (ROOT / "camera_nodes" / "camera_nodes" / "node.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    drivers_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "drivers" / "__init__.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "services.autofocus" not in node_content
    assert "services.exposure" not in node_content
    assert "fly_over" not in node_content
    assert "algorithms.autofocus" not in node_content
    assert "sim_node" not in node_content
    assert "SimulatedCameraDriver" in drivers_content
