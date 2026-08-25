from __future__ import annotations

import yaml

from promoc_bringup.launch_utils import materialize_dynamic_parameters_yaml


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
