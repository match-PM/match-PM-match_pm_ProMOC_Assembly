"""Regression tests for the scientific raw-green MTF path."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest


if "cv2" in sys.modules and not hasattr(sys.modules["cv2"], "GaussianBlur"):
    del sys.modules["cv2"]

cv2 = pytest.importorskip("cv2")

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camera_nodes.algorithms.mtf import MTFAnalyzer, MTFConfig  # noqa: E402
from camera_nodes.algorithms.mtf import analyzer as analyzer_module  # noqa: E402
from camera_nodes.algorithms.mtf import processing as processing_module  # noqa: E402
from camera_nodes.algorithms.mtf.processing import extract_rggb_green_samples  # noqa: E402
from camera_nodes.algorithms import roi_detection as roi_detection_module  # noqa: E402


analyzer_module.cv2 = cv2
processing_module.cv2 = cv2
roi_detection_module.cv2 = cv2


def _generate_dense_edge(size: int = 240, angle_deg: float = 5.0, blur_sigma: float = 1.0):
    y, x = np.ogrid[:size, :size]
    x_c = x - size / 2
    y_c = y - size / 2
    angle_rad = np.radians(angle_deg)
    x_rot = x_c * np.cos(angle_rad) + y_c * np.sin(angle_rad)
    edge = (x_rot > 0).astype(np.float64)

    edge_u8 = (edge * 255.0).astype(np.uint8)
    ksize = int(6 * blur_sigma + 1)
    if ksize % 2 == 0:
        ksize += 1
    edge_blur = cv2.GaussianBlur(edge_u8, (ksize, ksize), blur_sigma)
    return edge_blur.astype(np.uint16) * 256


def _green_infill_from_raw(raw_bayer: np.ndarray) -> np.ndarray:
    green = np.full(raw_bayer.shape, np.nan, dtype=np.float64)
    green[0::2, 1::2] = raw_bayer[0::2, 1::2]
    green[1::2, 0::2] = raw_bayer[1::2, 0::2]

    height, width = green.shape
    for row in range(height):
        for col in range(width):
            if not np.isnan(green[row, col]):
                continue
            samples = []
            for d_row in (-1, 0, 1):
                for d_col in (-1, 0, 1):
                    src_row = row + d_row
                    src_col = col + d_col
                    if (
                        0 <= src_row < height
                        and 0 <= src_col < width
                        and not np.isnan(green[src_row, src_col])
                    ):
                        samples.append(green[src_row, src_col])
            green[row, col] = float(np.mean(samples))

    return green.astype(np.uint16)


def test_extract_rggb_green_samples_coordinates_and_values():
    roi = np.arange(16, dtype=np.uint16).reshape(4, 4)

    groups = extract_rggb_green_samples(roi)
    g1_x, g1_y, g1_values = groups["g1"]
    g2_x, g2_y, g2_values = groups["g2"]

    assert np.array_equal(g1_x, np.array([1.0, 3.0, 1.0, 3.0]))
    assert np.array_equal(g1_y, np.array([0.0, 0.0, 2.0, 2.0]))
    assert np.array_equal(g1_values, np.array([1.0, 3.0, 9.0, 11.0]))

    assert np.array_equal(g2_x, np.array([0.0, 2.0, 0.0, 2.0]))
    assert np.array_equal(g2_y, np.array([1.0, 1.0, 3.0, 3.0]))
    assert np.array_equal(g2_values, np.array([4.0, 6.0, 12.0, 14.0]))


def test_extract_rggb_green_samples_respects_absolute_roi_origin():
    sensor = np.zeros((6, 6), dtype=np.uint16)
    sensor[0::2, 0::2] = 11
    sensor[0::2, 1::2] = 101
    sensor[1::2, 0::2] = 202
    sensor[1::2, 1::2] = 22

    even_groups = extract_rggb_green_samples(
        sensor[0:4, 0:4],
        origin_x=0,
        origin_y=0,
    )
    odd_groups = extract_rggb_green_samples(
        sensor[1:5, 1:5],
        origin_x=1,
        origin_y=1,
    )

    even_g1_x, even_g1_y, even_g1_values = even_groups["g1"]
    even_g2_x, even_g2_y, even_g2_values = even_groups["g2"]
    odd_g1_x, odd_g1_y, odd_g1_values = odd_groups["g1"]
    odd_g2_x, odd_g2_y, odd_g2_values = odd_groups["g2"]

    assert np.all(even_g1_values == 101.0)
    assert np.all(even_g2_values == 202.0)
    assert np.array_equal(even_g1_x, np.array([1.0, 3.0, 1.0, 3.0]))
    assert np.array_equal(even_g1_y, np.array([0.0, 0.0, 2.0, 2.0]))
    assert np.array_equal(even_g2_x, np.array([0.0, 2.0, 0.0, 2.0]))
    assert np.array_equal(even_g2_y, np.array([1.0, 1.0, 3.0, 3.0]))

    assert np.all(odd_g1_values == 101.0)
    assert np.all(odd_g2_values == 202.0)
    assert np.array_equal(odd_g1_x, np.array([0.0, 2.0, 0.0, 2.0]))
    assert np.array_equal(odd_g1_y, np.array([1.0, 1.0, 3.0, 3.0]))
    assert np.array_equal(odd_g2_x, np.array([1.0, 3.0, 1.0, 3.0]))
    assert np.array_equal(odd_g2_y, np.array([0.0, 0.0, 2.0, 2.0]))


def test_raw_green_analyzer_reports_group_metrics_and_capture_metadata():
    raw_bayer = _generate_dense_edge()
    config = MTFConfig(
        pixel_size_um=2.4,
        min_edge_angle=2.0,
        max_edge_angle=10.0,
        input_mode="raw_bayer_rggb",
        raw_bayer_pattern="RGGB",
        capture_pixel_format="BayerRG12",
        capture_binning_h=1,
        capture_binning_v=1,
        capture_exposure_us=100000.0,
        capture_gain=0.0,
        source_encoding="bayer_rggb16",
        wavelength_um=0.53,
    )

    result = MTFAnalyzer(config).compute_mtf(raw_bayer)

    assert result.valid is True
    assert result.capture_mode == "raw_green"
    assert result.capture_pixel_format == "BayerRG12"
    assert result.capture_binning_h == 1
    assert result.capture_binning_v == 1
    assert result.capture_exposure_us == 100000.0
    assert result.capture_gain == 0.0
    assert result.illumination_wavelength_um == 0.53
    assert result.source_encoding == "bayer_rggb16"
    assert result.g1_mtf50 > 0.0
    assert result.g2_mtf50 > 0.0
    assert result.g1_g2_delta_pct < 5.0


def test_raw_green_path_is_closer_to_ground_truth_than_green_infill():
    dense_scene = _generate_dense_edge()
    raw_bayer = dense_scene.copy()
    green_infill = _green_infill_from_raw(raw_bayer)

    dense_config = MTFConfig(
        pixel_size_um=2.4,
        min_edge_angle=2.0,
        max_edge_angle=10.0,
        input_mode="dense_gray",
    )
    raw_config = MTFConfig(
        pixel_size_um=2.4,
        min_edge_angle=2.0,
        max_edge_angle=10.0,
        input_mode="raw_bayer_rggb",
        raw_bayer_pattern="RGGB",
        capture_pixel_format="BayerRG12",
        source_encoding="bayer_rggb16",
    )

    dense_result = MTFAnalyzer(dense_config).compute_mtf(dense_scene)
    raw_result = MTFAnalyzer(raw_config).compute_mtf(raw_bayer)
    infill_result = MTFAnalyzer(dense_config).compute_mtf(green_infill)

    assert dense_result.valid is True
    assert raw_result.valid is True
    assert infill_result.valid is True

    raw_error = abs(raw_result.mtf50 - dense_result.mtf50)
    infill_error = abs(infill_result.mtf50 - dense_result.mtf50)

    assert raw_error < infill_error


@pytest.mark.parametrize("angle_deg", [3.0, 5.0, 7.0, 9.0])
def test_hybrid_angle_estimator_tracks_nominal_synthetic_angle(angle_deg):
    scene = _generate_dense_edge(angle_deg=angle_deg, blur_sigma=1.0)
    config = MTFConfig(
        pixel_size_um=2.4,
        min_edge_angle=2.0,
        max_edge_angle=10.0,
        input_mode="dense_gray",
    )

    result = MTFAnalyzer(config).compute_mtf(scene)

    assert result.valid is True
    assert result.edge_angle_method == "geometric"
    assert abs(abs(result.edge_angle) - angle_deg) <= 1.0
    assert result.edge_angle_consistency_deg < config.angle_consistency_warn_deg
    assert result.edge_support_points >= config.angle_min_support_points
    assert result.analysis_roi_bounds is not None


def test_analysis_strip_stabilizes_manual_roi_variations():
    scene = _generate_dense_edge(angle_deg=5.0, blur_sigma=1.0)
    analyzer = MTFAnalyzer(
        MTFConfig(
            pixel_size_um=2.4,
            min_edge_angle=2.0,
            max_edge_angle=10.0,
            input_mode="dense_gray",
        )
    )
    rois = [
        (20, 20, 220, 220),
        (40, 40, 200, 200),
        (60, 60, 180, 180),
        (80, 80, 160, 160),
    ]

    results = [analyzer.compute_mtf(scene, roi=roi) for roi in rois]

    assert all(result.valid for result in results)
    assert all(result.edge_angle_method == "geometric" for result in results)

    measured_angles = np.array([abs(result.edge_angle) for result in results], dtype=np.float64)
    measured_mtf50 = np.array([result.mtf50 for result in results], dtype=np.float64)

    assert np.max(measured_angles) - np.min(measured_angles) <= 0.25
    assert np.max(measured_mtf50) - np.min(measured_mtf50) <= 1.0


def test_angle_estimator_reports_phase_fallback_when_support_is_forced_low():
    scene = _generate_dense_edge(angle_deg=5.0, blur_sigma=1.0)
    config = MTFConfig(
        pixel_size_um=2.4,
        min_edge_angle=2.0,
        max_edge_angle=10.0,
        input_mode="dense_gray",
        angle_estimation_mode="hybrid",
        angle_allow_phase_fallback=True,
        angle_min_support_points=1000,
    )

    result = MTFAnalyzer(config).compute_mtf(scene)

    assert result.valid is True
    assert result.edge_angle_method == "phase_fallback"
    assert result.edge_angle_phase != 0.0
    assert result.edge_angle_geometric != 0.0
    assert result.edge_angle_consistency_deg > 0.0
