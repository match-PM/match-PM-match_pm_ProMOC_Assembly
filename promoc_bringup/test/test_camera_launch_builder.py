"""Unit tests for camera launch parameter builders."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
path_str = str(ROOT / "promoc_bringup")
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from promoc_bringup.camera_launch_builder import build_camera_node_parameters  # noqa: E402


def test_camera_node_parameters_enable_scientific_raw_mtf_defaults():
    params = build_camera_node_parameters(
        camera_params={
            "sensor_resolution_h": 5536,
            "sensor_resolution_v": 3692,
        },
        camera_config={
            "camera_info": {
                "image_width": 5536,
                "image_height": 3692,
            },
            "mtf_params": {
                "recommended_exposure_ms": 100.0,
                "recommended_gain": 0.0,
                "wavelength_um": 0.53,
            },
        },
    )

    assert params["mtf.use_raw_capture"] is True
    assert params["mtf.capture_required_raw"] is True
    assert params["mtf.capture_pixel_format"] == "BayerRG12"
    assert params["mtf.capture_bayer_pattern"] == "RGGB"
    assert params["mtf.capture_width"] == 5536
    assert params["mtf.capture_height"] == 3692
    assert params["mtf.capture_binning"] == 1
    assert params["mtf.capture_exposure_us"] == 100000.0
    assert params["mtf.capture_gain"] == 0.0
    assert params["mtf.green_wavelength_um"] == 0.53
