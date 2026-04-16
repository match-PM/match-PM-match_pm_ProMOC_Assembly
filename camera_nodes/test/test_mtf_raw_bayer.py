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
