from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from promoc_bringup.launch_utils import (
    load_target_tilt_config,
    load_user_config,
    materialize_dynamic_parameters_yaml,
    resolve_objective_selection,
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


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ("1x", ("1x", 1.0)),
        ("2", ("2x", 2.0)),
        ("3.0x", ("3x", 3.0)),
        ("4x", ("4x", 4.0)),
    ],
)
def test_resolve_objective_selection_accepts_supported_launch_values(
    override,
    expected,
):
    assert resolve_objective_selection({}, override) == expected


def test_resolve_objective_selection_uses_configured_profile_value():
    config = {"measurement_conditions": {"camera_objective": "2x"}}

    assert resolve_objective_selection(config, "profile") == ("2x", 2.0)


def test_resolve_objective_selection_rejects_unsupported_value():
    with pytest.raises(ValueError, match="1x, 2x, 3x, or 4x"):
        resolve_objective_selection({}, "6x")


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


def test_screening_camera_profiles_expose_measurement_readbacks():
    config_dir = Path(__file__).resolve().parents[1] / "config" / "cameras"
    required_common = {
        "ExposureTime",
        "Gain",
        "PixelFormat",
        "ExposureAuto",
        "GainAuto",
        "BinningHorizontal",
        "BinningVertical",
        "Width",
        "Height",
        "OffsetX",
        "OffsetY",
    }

    for profile_name in (
        "ids_u3_3800cp_m_gl_r22",
        "ids_u3_3800cp_c_hq_r22",
    ):
        with open(config_dir / f"{profile_name}.yaml", encoding="utf-8") as file_handle:
            profile = yaml.safe_load(file_handle)

        features = {
            item["FeatureName"] for item in profile.get("dynamic_parameters", [])
        }
        assert required_common <= features
        assert {"Gamma", "GammaEnable"} & features
        assert profile["exposure_time"]["min_val"] == 80.0
        exposure_feature = next(
            item for item in profile["dynamic_parameters"]
            if item["FeatureName"] == "ExposureTime"
        )
        assert exposure_feature["Min"] == 80.0

        if profile["mtf_params"]["analysis_channel"] == "green":
            assert {"BalanceWhiteAuto", "ColorTransformationEnable"} <= features
