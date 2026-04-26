"""Static smoke checks for the minimal messstand launch path."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

def test_optical_launch_has_no_verification_node():
    content = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "scientific_verification" not in content
    assert "package='verification'" not in content
    assert "runtime_mode" in content
    assert "/promoc/camera/autofocus" in content
    assert "/promoc/camera/measure_mtf_center" in content
    assert "/promoc/camera/measure_mtf_roi" in content
    assert "/promoc/camera/set_exposure" in content
    assert "camera_info_example_uv.yaml" not in content
    assert "\"ExposureTime\"" in content
    assert "\"OffsetX\"" in content
    assert "\"camera.image_topic\"" in content
    assert "\"camera.default_pixel_format\"" in content
    assert "\"camera.default_exposure_us\"" in content
    assert "\"dynamic_parameters_yaml_url\"" in content


def test_only_one_camera_profile_is_maintained_for_messstand():
    cameras_dir = ROOT / "promoc_bringup" / "config" / "cameras"
    yaml_profiles = sorted(path.name for path in cameras_dir.glob("*.yaml"))

    assert yaml_profiles == ["ids_u3_3800cp_hq.yaml"]
