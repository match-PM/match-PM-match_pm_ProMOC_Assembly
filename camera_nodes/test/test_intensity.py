"""Tests for ROS-independent raw intensity and exposure regulation helpers."""

import numpy as np
import pytest

from camera_nodes.intensity import (
    analysis_plane,
    exposure_ratio,
    measure_intensity,
    native_max_value,
)


def test_native_range_detects_right_and_left_aligned_12_bit():
    right = np.asarray([[0, 1024, 4095]], dtype=np.uint16)
    left = np.asarray([[0, 1024 << 4, 4095 << 4]], dtype=np.uint16)
    assert native_max_value("Mono12", right) == 4095
    assert native_max_value("Mono12", left) == 4095 << 4
    assert measure_intensity(right, None, pixel_format="Mono12")["p95_norm"] < 1
    assert measure_intensity(left, None, pixel_format="Mono12")["p95_norm"] < 1


def test_bayer_rggb_uses_only_real_green_sensels():
    image = np.asarray([
        [4000, 1000, 4000, 1000],
        [3000, 0, 3000, 0],
        [4000, 1000, 4000, 1000],
        [3000, 0, 3000, 0],
    ], dtype=np.uint16)
    plane = analysis_plane(image, None, pixel_format="BayerRG12")
    assert plane.shape == (2, 4)
    assert np.array_equal(plane[0], [1000, 3000, 1000, 3000])


def test_segmented_plateau_medians_ignore_eroded_boundary_contamination():
    image = np.full((40, 60), 400, dtype=np.uint16)
    image[:, 30:] = 2800
    image[:, 29:31] = 1600
    result = measure_intensity(image, None, pixel_format="Mono12")
    assert result["intensity_method"] == "segmented_plateau_median"
    assert result["black_level"] == 400
    assert result["white_level"] == 2800


def test_segmentation_falls_back_without_two_valid_plateaus():
    image = np.full((32, 32), 1000, dtype=np.uint16)
    image[0, 0] = 1200
    result = measure_intensity(image, None, pixel_format="Mono12")
    assert result["intensity_method"] == "p95_fallback"
    assert result["white_level"] == pytest.approx(result["p95"])
    assert result["black_level"] == pytest.approx(1000)


def test_p999_and_saturation_fraction_both_detect_clipping():
    image = np.full((100, 100), 1000, dtype=np.uint16)
    image.reshape(-1)[:20] = 4095
    result = measure_intensity(image, None, pixel_format="Mono12")
    assert result["p99_9_norm"] >= 0.95
    assert result["saturation_fraction"] == pytest.approx(0.002)
    assert result["clipping_detected"] is True


def test_exposure_ratio_corrects_black_offset_damps_and_clamps():
    levels = {"white_level_norm": 0.50, "black_level_norm": 0.10,
              "clipping_detected": False}
    expected = np.clip((0.70 - 0.10) / (0.50 - 0.10), 0.5, 2.0) ** 0.7
    assert exposure_ratio(levels, 0.70) == pytest.approx(expected)
    assert exposure_ratio({**levels, "clipping_detected": True}, 0.70) == 0.8
    assert exposure_ratio({"white_level_norm": 0.11, "black_level_norm": 0.10,
                           "clipping_detected": False}, 0.70) == pytest.approx(2.0 ** 0.7)
    assert exposure_ratio({"white_level_norm": 0.95, "black_level_norm": 0.90,
                           "clipping_detected": False}, 0.70) == pytest.approx(0.5 ** 0.7)
