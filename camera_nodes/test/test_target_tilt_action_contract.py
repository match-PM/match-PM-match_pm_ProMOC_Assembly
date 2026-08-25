"""Static ROS interface and launch wiring checks for target tilt."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_action_contains_required_goal_result_feedback_and_statuses():
    action = (
        ROOT / "promoc_assembly_interfaces" / "action" / "EstimateTargetTilt.action"
    ).read_text(encoding="utf-8")
    for field in (
        "center_z_mm",
        "half_range_mm",
        "step_mm",
        "frames_per_position",
        "fit_field_curvature",
        "return_to_center",
        "tilt_x_deg",
        "uncertainty_x_deg",
        "detection_limit_x_deg",
        "surface_rms_um",
        "x_span_fraction",
        "tilt_x_detectable",
        "within_tolerance_x",
        "resolution_limited_x",
        "decision_x",
        "surface_mae_um",
        "roi_robust_outliers",
        "evaluation_directory",
        "phase",
        "z_index",
        "frames_acquired",
    ):
        assert field in action
    for status in (
        "OK",
        "INSUFFICIENT_TEXTURE",
        "INSUFFICIENT_COVERAGE",
        "FOCUS_OUTSIDE_SCAN",
        "FIT_UNSTABLE",
        "CANCELLED",
        "HARDWARE_TIMEOUT",
        "IMAGE_TIMEOUT",
    ):
        assert status in action


def test_launch_uses_canonical_axis_and_relative_camera_topics():
    launch = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8")
    assert '"image_topic": "stream0/image_raw"' in launch
    assert '"camera_info_topic": "stream0/camera_info"' in launch
    assert '"/promoc/linear_axis/lts300_x_axis"' in launch
    assert 'executable="target_tilt_estimator"' in launch
    assert 'namespace=f"promoc/{camera_name}"' in launch
    assert 'name == "evaluation_focus_metrics" and not config[name]' in launch


def test_settle_sleep_never_passes_negative_duration():
    node = (
        ROOT / "camera_nodes" / "camera_nodes" / "target_tilt_node.py"
    ).read_text(encoding="utf-8")
    assert "remaining = deadline - time.monotonic()" in node
    assert "if remaining <= 0.0:" in node
    assert "time.sleep(min(0.02, remaining))" in node
    assert "time.sleep(min(0.02, deadline - time.monotonic()))" not in node
