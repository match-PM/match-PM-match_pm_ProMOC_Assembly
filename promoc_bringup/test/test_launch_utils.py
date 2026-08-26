from __future__ import annotations

import yaml

from promoc_bringup.launch_utils import (
    load_target_tilt_config,
    load_user_config,
    materialize_dynamic_parameters_yaml,
)


def test_dynamic_parameter_descriptions_are_always_strings(tmp_path):
    target = tmp_path / "dynamic_parameters.yaml"
    result = materialize_dynamic_parameters_yaml(
        [
            {"FeatureName": "ExposureTime", "Type": "float"},
            {
                "FeatureName": "Gain",
                "Type": "float",
                "Description": "Analog gain.",
            },
        ],
        target_path=str(target),
    )

    with open(result, encoding="utf-8") as file_handle:
        payload = yaml.safe_load(file_handle)

    assert payload[0]["Description"] == "Dynamic GenICam feature ExposureTime."
    assert payload[1]["Description"] == "Analog gain."
    assert all(isinstance(item["Description"], str) for item in payload)


def test_user_config_preserves_target_tilt_section(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "user_config.yaml").write_text(
        """
camera:
  profile: ids_u3_3800cp_m_gl_r22
target_tilt:
  magnification: 3.0
  object_um_per_pixel: 0.8
  roi_rows: 7
  repeatability_x_deg: 0.002
""",
        encoding="utf-8",
    )

    config = load_user_config(str(tmp_path))

    assert config["target_tilt"] == {
        "magnification": 3.0,
        "object_um_per_pixel": 0.8,
        "roi_rows": 7,
        "repeatability_x_deg": 0.002,
    }


def test_target_tilt_user_values_override_selected_imaging_profile(tmp_path):
    profile_dir=tmp_path/"config"/"imaging_profiles"; profile_dir.mkdir(parents=True)
    (profile_dir/"test_profile.yaml").write_text(
        """
imaging_profile:
  object_um_per_pixel: 0.9
target_tilt:
  roi_selection_mode: fixed_grid
  minimum_selected_rois: 12
""",encoding="utf-8")
    user_config={"target_tilt":{"imaging_profile":"test_profile","roi_selection_mode":"auto_texture"}}

    resolved,profile_name,error=load_target_tilt_config(str(tmp_path),user_config)

    assert error is None
    assert profile_name=="test_profile"
    assert resolved["object_um_per_pixel"]==0.9
    assert resolved["minimum_selected_rois"]==12
    assert resolved["roi_selection_mode"]=="auto_texture"
    assert "imaging_profile" not in resolved
