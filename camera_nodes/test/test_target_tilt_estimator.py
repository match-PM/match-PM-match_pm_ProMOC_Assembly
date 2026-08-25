"""Synthetic tests for focus-stack target-tilt estimation."""

from __future__ import annotations

import math

import cv2
import numpy as np
import pytest

from camera_nodes.algorithms.target_tilt import (
    RoiTiltEstimator,
    TiltEstimatorConfig,
    TiltStatus,
    _robust_huber_fit,
    image_to_float32,
    make_grid_rois,
)


def test_supported_ros_encodings_are_normalized_and_green_selected():
    mono8 = np.asarray([[0, 255]], dtype=np.uint8)
    mono16 = np.asarray([[0, 65535]], dtype=np.uint16)
    assert image_to_float32(mono8, "mono8").tolist() == [[0.0, 1.0]]
    assert image_to_float32(mono16, "mono16").tolist() == [[0.0, 1.0]]

    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    rgb[:, :, 0] = 250
    rgb[:, :, 1] = 128
    assert np.allclose(image_to_float32(rgb, "rgb8"), 128.0 / 255.0)
    assert np.allclose(image_to_float32(rgb, "bgr8"), 128.0 / 255.0)

    bayer8 = np.tile(np.asarray([[20, 120], [120, 240]], dtype=np.uint8), (3, 3))
    bayer16 = bayer8.astype(np.uint16) * 257
    for pattern in ("rggb", "bggr", "gbrg", "grbg"):
        assert image_to_float32(bayer8, f"bayer_{pattern}8").dtype == np.float32
        assert image_to_float32(bayer16, f"bayer_{pattern}16").dtype == np.float32

    with pytest.raises(ValueError, match="packed Bayer12"):
        image_to_float32(bayer16, "bayer_rggb12")


def test_scan_rejects_image_format_changes():
    estimator = RoiTiltEstimator(
        make_grid_rois(2, 2),
        TiltEstimatorConfig(object_um_per_pixel=0.8, min_valid_rois=3),
    )
    estimator.add_position(0.0, [(np.ones((80, 100), np.uint8), "mono8")])
    with pytest.raises(ValueError, match="changed during scan"):
        estimator.add_position(0.01, [(np.ones((81, 100), np.uint8), "mono8")])
    with pytest.raises(ValueError, match="changed during scan"):
        estimator.add_position(0.01, [(np.ones((80, 100), np.uint16), "mono16")])


def test_synthetic_focus_stack_recovers_plane_tilt():
    size = 350
    rois = make_grid_rois(
        5,
        5,
        roi_width_fraction=0.13,
        roi_height_fraction=0.13,
        margin_fraction=0.10,
    )
    config = TiltEstimatorConfig(
        object_um_per_pixel=8.0,
        min_valid_rois=15,
        min_peak_prominence=0.01,
        min_fit_r2=0.40,
        repeatability_x_deg=0.001,
        repeatability_y_deg=0.001,
        bootstrap_iterations=8,
    )
    estimator = RoiTiltEstimator(rois, config)
    random = np.random.default_rng(7)
    texture = random.integers(20, 236, (size, size), dtype=np.uint8)
    expected_x_deg = 0.90
    expected_y_deg = -0.55
    slope_x = math.tan(math.radians(expected_x_deg))
    slope_y = math.tan(math.radians(expected_y_deg))

    for z_mm in np.linspace(-0.08, 0.08, 17):
        image = np.full((size, size), 128, dtype=np.uint8)
        for roi in rois:
            x0, y0, x1, y1 = roi.pixels((size, size))
            center_x = (x0 + x1) / 2.0
            center_y = (y0 + y1) / 2.0
            local_focus_mm = (
                slope_x * (center_x - size / 2.0) * 0.008
                + slope_y * (center_y - size / 2.0) * 0.008
            )
            sigma = 0.45 + abs(z_mm - local_focus_mm) * 90.0
            image[y0:y1, x0:x1] = cv2.GaussianBlur(
                texture[y0:y1, x0:x1],
                (0, 0),
                sigmaX=sigma,
                sigmaY=sigma,
            )
        estimator.add_position(z_mm, [(image, "mono8")] * 3)

    result = estimator.solve(peak_half_window=2)
    assert result.status == TiltStatus.OK
    assert result.roi_valid >= 20
    assert result.x_span_fraction >= 0.7
    assert result.y_span_fraction >= 0.7
    assert result.tilt_x_deg == pytest.approx(expected_x_deg, abs=0.08)
    assert result.tilt_y_deg == pytest.approx(expected_y_deg, abs=0.08)
    assert result.tilt_x_detectable
    assert result.tilt_y_detectable
    assert not result.resolution_limited_x
    assert not result.resolution_limited_y
    assert result.bootstrap.successful_iterations == 8

    curved_result = estimator.solve(quadratic_surface=True, peak_half_window=2)
    assert curved_result.status == TiltStatus.OK
    assert curved_result.tilt_x_deg == pytest.approx(expected_x_deg, abs=0.08)
    assert curved_result.tilt_y_deg == pytest.approx(expected_y_deg, abs=0.08)


def test_black_focus_stack_is_insufficient_texture():
    estimator = RoiTiltEstimator(
        make_grid_rois(4, 4),
        TiltEstimatorConfig(object_um_per_pixel=0.8, min_valid_rois=8),
    )
    black = np.zeros((160, 160), dtype=np.uint8)
    for z_mm in (-0.02, 0.0, 0.02):
        estimator.add_position(z_mm, [(black, "mono8")] * 2)
    result = estimator.solve()
    assert result.status == TiltStatus.INSUFFICIENT_TEXTURE
    assert result.roi_valid == 0


def test_monotonic_focus_stack_reports_peak_outside_scan():
    estimator = RoiTiltEstimator(
        make_grid_rois(4, 4),
        TiltEstimatorConfig(object_um_per_pixel=0.8, min_valid_rois=8),
    )
    random = np.random.default_rng(19)
    texture = random.integers(20, 236, (160, 160), dtype=np.uint8)
    for z_mm, sigma in ((-0.02, 4.0), (0.0, 2.0), (0.02, 0.5)):
        image = cv2.GaussianBlur(texture, (0, 0), sigma)
        estimator.add_position(z_mm, [(image, "mono8")] * 2)
    result = estimator.solve()
    assert result.status == TiltStatus.FOCUS_OUTSIDE_SCAN


def test_valid_rois_on_one_side_report_insufficient_coverage():
    rois = make_grid_rois(4, 4, roi_width_fraction=0.16, roi_height_fraction=0.16)
    estimator = RoiTiltEstimator(
        rois,
        TiltEstimatorConfig(
            object_um_per_pixel=4.0,
            min_valid_rois=6,
            min_peak_prominence=0.01,
            min_fit_r2=0.0,
        ),
    )
    size = 200
    random = np.random.default_rng(23)
    texture = random.integers(20, 236, (size, size), dtype=np.uint8)
    for z_mm in np.linspace(-0.04, 0.04, 5):
        image = np.zeros((size, size), dtype=np.uint8)
        for index, roi in enumerate(rois):
            if index % 4 >= 2:
                continue
            x0, y0, x1, y1 = roi.pixels((size, size))
            sigma = 0.5 + abs(z_mm) * 100.0
            image[y0:y1, x0:x1] = cv2.GaussianBlur(
                texture[y0:y1, x0:x1],
                (0, 0),
                sigma,
            )
        estimator.add_position(z_mm, [(image, "mono8")] * 2)
    result = estimator.solve()
    assert result.status == TiltStatus.INSUFFICIENT_COVERAGE
    assert result.roi_valid >= 6
    assert result.x_span_fraction < 0.5


def test_robust_surface_fit_limits_single_outlier():
    random = np.random.default_rng(11)
    x = random.uniform(-2.0, 2.0, 40)
    y = random.uniform(-1.0, 1.0, 40)
    design = np.column_stack((np.ones(x.size), x, y))
    expected = np.asarray([4.2, 0.02, -0.03])
    values = design @ expected
    values[0] += 3.0
    coefficients, covariance, residuals = _robust_huber_fit(design, values)
    assert coefficients == pytest.approx(expected, abs=1.0e-8)
    assert covariance.shape == (3, 3)
    assert residuals[0] > 2.9
