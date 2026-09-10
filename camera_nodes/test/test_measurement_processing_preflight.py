"""Scientific-processing safety checks for measurement preflight."""

import pytest

from camera_nodes.measurement_processing import ProcessingStateError, verify_processing_state


def _bayer_values():
    return {
        "exposure_auto": "Off",
        "gain_auto": "Off",
        "white_balance_auto": "Off",
    }


def test_bayer_accepts_profile_requested_features_proven_unsupported():
    accepted = verify_processing_state(
        _bayer_values(), {"gamma", "color_transform_enable"}, "BayerRG12"
    )
    assert accepted == ["color_transform_enable", "gamma"]


def test_bayer_rejects_merely_missing_processing_readbacks():
    with pytest.raises(ProcessingStateError, match="Gamma"):
        verify_processing_state(_bayer_values(), set(), "BayerRG12")


def test_bayer_rejects_nonunity_gamma_and_enabled_processing():
    with pytest.raises(ProcessingStateError, match="unity"):
        verify_processing_state(
            {**_bayer_values(), "gamma": 1.2}, {"color_transform_enable"}, "BayerRG12"
        )
    with pytest.raises(ProcessingStateError, match="white_balance_auto"):
        verify_processing_state(
            {**_bayer_values(), "white_balance_auto": "Continuous", "gamma": 1.0},
            {"color_transform_enable"}, "BayerRG12",
        )
