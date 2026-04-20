"""Standalone Windows-friendly validation script for synthetic MTF edges.

This script intentionally has no ROS2 and no repository imports so it can be
copied onto a plain Windows machine and run with a local Python installation.

It supports two operating modes:
    - quick: lightweight smoke/regression validation
    - scientific: analytical benchmark sweep for comparative test stands

Dependencies:
    pip install numpy opencv-python matplotlib

Examples:
    python mtf_synthetic_validation.py
    python mtf_synthetic_validation.py --profile scientific --report-json .\\report.json
    python mtf_synthetic_validation.py --mode raw --no-png
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Optional

import cv2
import numpy as np


QUICK_SCENE_OVERSAMPLE = 6
SCIENTIFIC_SCENE_OVERSAMPLE = 8
SCIENTIFIC_ANGLES_DEG = (3.0, 5.0, 7.0, 9.0)
SCIENTIFIC_BLUR_SIGMAS_PX = (0.7, 1.0, 1.5, 2.0, 3.0)
SCIENTIFIC_RAW_ROI_OFFSETS = ((0, 0), (1, 0), (0, 1), (1, 1))
SCIENTIFIC_DENSE_BIAS_LIMIT_PCT = 10.0
SCIENTIFIC_RAW_BIAS_LIMIT_PCT = 12.0
SCIENTIFIC_DENSE_CURVE_RMSE_LIMIT = 0.08
SCIENTIFIC_RAW_CURVE_RMSE_LIMIT = 0.10
SCIENTIFIC_ANGLE_SPREAD_LIMIT_PCT = 5.0
SCIENTIFIC_RAW_PARITY_LIMIT_PCT = 1.0
SCIENTIFIC_RAW_VS_DENSE_LIMIT_PCT = 5.0
MONOTONIC_TOLERANCE_LPMM = 1e-3


@dataclass
class MTFConfig:
    """Configuration for standalone MTF analysis."""

    pixel_size_um: float = 2.40
    input_mode: str = "dense_gray"
    raw_bayer_pattern: str = "RGGB"
    roi_width: int = 200
    roi_height: int = 200
    roi_center: Optional[tuple[int, int]] = None
    min_edge_angle: float = 2.0
    max_edge_angle: float = 10.0
    oversample_factor: int = 4
    f_number: float = 2.8
    wavelength_um: float = 0.555
    lsf_window_mode: str = "full"
    lsf_peak_window_size: int = 0
    derivative_mode: str = "iso"
    apply_derivative_correction: bool = True
    derivative_correction_max: float = 0.0
    apply_angle_correction: bool = True
    esf_smooth_mode: str = "none"
    edge_validation_mode: str = "warn"
    edge_validation_percentile: float = 90.0
    edge_validation_min_points: int = 50
    clip_to_nyquist: bool = True
    mtf_clip_max: float = 0.0
    mtf_warn_threshold: float = 1.05
    raw_green_pair_warn_pct: float = 10.0

    def validate(self) -> None:
        """Validate critical configuration fields."""
        if self.pixel_size_um <= 0:
            raise ValueError("pixel_size_um must be positive")
        if self.input_mode not in {"dense_gray", "raw_bayer_rggb"}:
            raise ValueError("input_mode must be 'dense_gray' or 'raw_bayer_rggb'")
        if self.raw_bayer_pattern != "RGGB":
            raise ValueError("Only RGGB is supported in this standalone validator")
        if self.roi_width <= 0 or self.roi_height <= 0:
            raise ValueError("ROI dimensions must be positive")
        if self.max_edge_angle <= self.min_edge_angle:
            raise ValueError("max_edge_angle must be larger than min_edge_angle")
        if self.oversample_factor < 1:
            raise ValueError("oversample_factor must be >= 1")
        if self.edge_validation_mode not in {"off", "warn", "fail"}:
            raise ValueError("edge_validation_mode must be off, warn, or fail")


@dataclass
class MTFResult:
    """Result object for standalone MTF computation."""

    mtf50: float = 0.0
    mtf20: float = 0.0
    mtf10: float = 0.0
    frequencies: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    mtf_values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    mtf_ideal: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    esf: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    lsf: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    edge_angle: float = 0.0
    valid: bool = False
    error_msg: str = ""
    contrast: float = 0.0
    edge_direction: str = ""
    sensor_nyquist: float = 0.0
    mtf_peak: float = 0.0
    mtf_peak_raw: float = 0.0
    mtf_clipped: bool = False
    warning_msg: str = ""
    capture_mode: str = ""
    g1_mtf50: float = 0.0
    g2_mtf50: float = 0.0
    g1_mtf20: float = 0.0
    g2_mtf20: float = 0.0
    g1_mtf10: float = 0.0
    g2_mtf10: float = 0.0
    g1_g2_delta_pct: float = 0.0

    @property
    def nyquist_frequency(self) -> float:
        """Return Nyquist frequency in lp/mm."""
        if self.sensor_nyquist > 0:
            return float(self.sensor_nyquist)
        if self.frequencies.size > 0:
            return float(np.max(self.frequencies))
        return 0.0


@dataclass
class CheckResult:
    """One validation outcome in the CLI report."""

    name: str
    passed: bool
    summary: str
    metrics: dict[str, object] = field(default_factory=dict)


@dataclass
class ReferenceMetrics:
    """Analytical reference metrics for one synthetic blur setting."""

    mtf50: float
    mtf20: float
    mtf10: float
    frequencies: np.ndarray
    mtf_values: np.ndarray
    monotonic: bool
    nyquist_clipped: bool


@dataclass
class ScientificCaseResult:
    """Serializable benchmark record for one dense/raw scientific case."""

    path: str
    angle_deg: float
    blur_sigma_px: float
    roi_origin_xy: tuple[int, int]
    valid: bool
    edge_angle_deg: float
    mtf50_lpmm: float
    mtf20_lpmm: float
    mtf10_lpmm: float
    reference_mtf50_lpmm: float
    reference_mtf20_lpmm: float
    reference_mtf10_lpmm: float
    mtf50_rel_error_pct: float
    mtf20_rel_error_pct: float
    mtf10_rel_error_pct: float
    curve_rmse: float
    warning: str = ""
    error: str = ""
    g1_mtf50_lpmm: float = 0.0
    g2_mtf50_lpmm: float = 0.0
    g1_g2_delta_pct: float = 0.0
    raw_vs_dense_delta_pct: float = 0.0


@dataclass
class RawGroupSummary:
    """Aggregated summary over the four raw ROI-parity variants of one scene."""

    angle_deg: float
    blur_sigma_px: float
    mean_raw_mtf50_lpmm: float
    roi_spread_pct: float
    max_g1_g2_delta_pct: float
    raw_vs_dense_delta_pct: float


def pixel_pitch_mm(pixel_size_um: float) -> float:
    """Convert one pixel pitch from micrometers to millimeters."""
    return float(pixel_size_um) / 1000.0


def sensor_nyquist_lpmm(pixel_size_um: float) -> float:
    """Return the sensor Nyquist frequency in lp/mm."""
    return 1000.0 / (2.0 * float(pixel_size_um))


def relative_error_pct(measured: float, reference: float) -> float:
    """Return the absolute relative error in percent."""
    if reference <= 0:
        return float("inf")
    return abs(float(measured) - float(reference)) / float(reference) * 100.0


def spread_pct(values: list[float]) -> float:
    """Return spread/mean in percent for one value collection."""
    valid = [float(value) for value in values if np.isfinite(value)]
    if not valid:
        return float("inf")
    mean_value = float(np.mean(valid))
    if mean_value == 0.0:
        return float("inf")
    return (max(valid) - min(valid)) / mean_value * 100.0


def compute_curve_rmse(
    frequencies: np.ndarray,
    measured_mtf: np.ndarray,
    reference_mtf: np.ndarray,
) -> float:
    """Return the RMSE between one measured and one analytical MTF curve."""
    if frequencies.size == 0 or measured_mtf.size == 0 or reference_mtf.size == 0:
        return float("inf")
    min_len = min(frequencies.size, measured_mtf.size, reference_mtf.size)
    if min_len == 0:
        return float("inf")
    delta = measured_mtf[:min_len].astype(np.float64) - reference_mtf[:min_len].astype(np.float64)
    return float(np.sqrt(np.mean(delta**2)))


def centered_roi_bounds(
    image_size: int,
    roi_size: int,
    offset_x: int = 0,
    offset_y: int = 0,
) -> tuple[int, int, int, int]:
    """Return a centered ROI with an optional one-pixel parity shift."""
    base_x = (image_size - roi_size) // 2
    base_y = (image_size - roi_size) // 2
    x1 = base_x + int(offset_x)
    y1 = base_y + int(offset_y)
    return x1, y1, x1 + roi_size, y1 + roi_size


def analytical_gaussian_aperture_mtf(
    frequencies_lpmm: np.ndarray,
    pixel_size_um: float,
    blur_sigma_px: float,
) -> np.ndarray:
    """Analytical MTF = Gaussian PSF MTF * square-pixel aperture MTF."""
    freq_cyc_per_pixel = np.asarray(frequencies_lpmm, dtype=np.float64) * pixel_pitch_mm(pixel_size_um)
    gaussian_mtf = np.exp(-2.0 * (np.pi**2) * (float(blur_sigma_px) ** 2) * (freq_cyc_per_pixel**2))
    aperture_mtf = np.abs(np.sinc(freq_cyc_per_pixel))
    mtf = gaussian_mtf * aperture_mtf
    mtf[freq_cyc_per_pixel > 0.5 + 1e-12] = 0.0
    return mtf


def build_reference_metrics(
    pixel_size_um: float,
    blur_sigma_px: float,
    frequencies_lpmm: Optional[np.ndarray] = None,
    sample_count: int = 1024,
) -> ReferenceMetrics:
    """Build one analytical reference curve on the requested frequency axis."""
    nyquist = sensor_nyquist_lpmm(pixel_size_um)
    if frequencies_lpmm is None:
        frequencies = np.linspace(0.0, nyquist, max(32, int(sample_count)), dtype=np.float64)
    else:
        frequencies = np.asarray(frequencies_lpmm, dtype=np.float64)
        if frequencies.size == 0:
            frequencies = np.linspace(0.0, nyquist, max(32, int(sample_count)), dtype=np.float64)
        frequencies = frequencies[(frequencies >= 0.0) & (frequencies <= nyquist + 1e-9)]
        if frequencies.size == 0:
            frequencies = np.linspace(0.0, nyquist, max(32, int(sample_count)), dtype=np.float64)

    reference_curve = analytical_gaussian_aperture_mtf(frequencies, pixel_size_um, blur_sigma_px)
    return ReferenceMetrics(
        mtf50=find_mtf_frequency(frequencies, reference_curve, 0.5),
        mtf20=find_mtf_frequency(frequencies, reference_curve, 0.2),
        mtf10=find_mtf_frequency(frequencies, reference_curve, 0.1),
        frequencies=frequencies,
        mtf_values=reference_curve,
        monotonic=bool(np.all(np.diff(reference_curve) <= 1e-9)),
        nyquist_clipped=bool(float(np.max(frequencies)) <= nyquist + 1e-9),
    )


def calculate_michelson_contrast(roi: np.ndarray) -> float:
    """Calculate Michelson contrast for one ROI."""
    if roi.size == 0:
        return 0.0
    min_val = float(np.min(roi))
    max_val = float(np.max(roi))
    return (max_val - min_val) / (max_val + min_val + 1e-6)


def compute_esf(roi: np.ndarray, edge_angle: float, oversample_factor: int) -> np.ndarray:
    """Compute a dense ESF by projecting pixels onto the edge normal."""
    height, width = roi.shape
    angle_rad = np.radians(edge_angle)
    esf_points: list[tuple[float, float]] = []
    for row in range(height):
        offset = row * np.tan(angle_rad)
        for col in range(width):
            pos = (col - width / 2 - offset) * oversample_factor
            esf_points.append((pos, roi[row, col]))

    esf_points.sort(key=lambda item: item[0])
    positions = np.array([item[0] for item in esf_points], dtype=np.float64)
    values = np.array([item[1] for item in esf_points], dtype=np.float64)
    bin_edges = np.arange(positions.min(), positions.max(), 1)
    if bin_edges.size < 2:
        return np.array([], dtype=np.float64)

    bin_indices = np.digitize(positions, bin_edges)
    esf = []
    for idx in range(1, len(bin_edges)):
        mask = bin_indices == idx
        if np.any(mask):
            esf.append(float(np.mean(values[mask])))
    return np.array(esf, dtype=np.float64)


def extract_rggb_green_samples(
    roi: np.ndarray,
    *,
    origin_x: int = 0,
    origin_y: int = 0,
    pattern: str = "RGGB",
) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Extract G1/G2 samples while respecting absolute Bayer parity."""
    if roi.ndim != 2:
        raise ValueError("Raw Bayer ROI must be a 2D array")
    if str(pattern or "").upper() != "RGGB":
        raise ValueError(f"Unsupported Bayer pattern '{pattern}'")

    roi_f = roi.astype(np.float64)
    local_row_even = int(origin_y) % 2
    local_row_odd = 1 - local_row_even
    local_col_even = int(origin_x) % 2
    local_col_odd = 1 - local_col_even

    g1_values = roi_f[local_row_even::2, local_col_odd::2]
    g2_values = roi_f[local_row_odd::2, local_col_even::2]

    g1_rows, g1_cols = np.indices(g1_values.shape, dtype=np.float64)
    g2_rows, g2_cols = np.indices(g2_values.shape, dtype=np.float64)

    g1_x = (2.0 * g1_cols + float(local_col_odd)).ravel()
    g1_y = (2.0 * g1_rows + float(local_row_even)).ravel()
    g2_x = (2.0 * g2_cols + float(local_col_even)).ravel()
    g2_y = (2.0 * g2_rows + float(local_row_odd)).ravel()

    return {
        "g1": (g1_x, g1_y, g1_values.ravel()),
        "g2": (g2_x, g2_y, g2_values.ravel()),
    }


def rotate_sample_coordinates_90_cw(
    sample_x: np.ndarray,
    sample_y: np.ndarray,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Rotate sparse sample coordinates like cv2.ROTATE_90_CLOCKWISE."""
    rotated_x = sample_y.astype(np.float64)
    rotated_y = (float(width) - 1.0) - sample_x.astype(np.float64)
    return rotated_x, rotated_y, int(height), int(width)


def compute_esf_from_samples(
    sample_x: np.ndarray,
    sample_y: np.ndarray,
    sample_values: np.ndarray,
    edge_angle: float,
    oversample_factor: int,
    width: int,
    height: int,
) -> np.ndarray:
    """Compute ESF from sparse sample coordinates."""
    if sample_x.size == 0 or sample_y.size == 0 or sample_values.size == 0:
        return np.array([], dtype=np.float64)

    angle_rad = np.radians(edge_angle)
    positions = (sample_x - (width / 2.0) - sample_y * np.tan(angle_rad)) * oversample_factor
    sort_idx = np.argsort(positions)
    positions = positions[sort_idx]
    values = sample_values[sort_idx].astype(np.float64)

    bin_edges = np.arange(positions.min(), positions.max(), 1)
    if bin_edges.size < 2:
        return np.array([], dtype=np.float64)

    bin_indices = np.digitize(positions, bin_edges)
    esf = []
    for idx in range(1, len(bin_edges)):
        mask = bin_indices == idx
        if np.any(mask):
            esf.append(float(np.mean(values[mask])))
    return np.array(esf, dtype=np.float64)


def smooth_esf(esf: np.ndarray, config: MTFConfig) -> tuple[np.ndarray, str]:
    """Return ESF unchanged unless smoothing is explicitly requested."""
    if esf.size == 0:
        return esf, ""
    if config.esf_smooth_mode == "none":
        return esf, ""
    return esf, "ESF smoothing is disabled in the standalone validator"


def compute_lsf(esf: np.ndarray, config: MTFConfig) -> np.ndarray:
    """Compute the line spread function from the ESF."""
    if esf.size < 2:
        return np.array([], dtype=np.float64)
    if config.derivative_mode == "iso":
        if esf.size < 3:
            return np.array([], dtype=np.float64)
        kernel = np.array([-0.5, 0.0, 0.5], dtype=np.float64)
        return np.convolve(esf, kernel, mode="valid")
    return np.diff(esf)


def apply_lsf_window(lsf: np.ndarray, config: MTFConfig) -> np.ndarray:
    """Apply simple windowing to the LSF."""
    if lsf.size == 0:
        return lsf
    if config.lsf_window_mode == "none":
        return lsf
    if config.lsf_window_mode == "peak":
        if config.lsf_peak_window_size > 0:
            size = min(int(config.lsf_peak_window_size), lsf.size)
        else:
            size = min(lsf.size, max(9, lsf.size // 3))
        if size < 4:
            return lsf
        if size % 2 == 0:
            size += 1
            if size > lsf.size:
                size = lsf.size
        peak_idx = int(np.argmax(np.abs(lsf)))
        half = size // 2
        start = max(0, peak_idx - half)
        end = min(lsf.size, peak_idx + half + 1)
        if end - start < size:
            if start == 0:
                end = min(lsf.size, start + size)
            else:
                start = max(0, end - size)
        window = np.hamming(end - start)
        lsf_windowed = np.zeros_like(lsf)
        lsf_windowed[start:end] = lsf[start:end] * window
        return lsf_windowed
    return lsf * np.hamming(lsf.size)


def compute_mtf_from_lsf(
    lsf: np.ndarray,
    config: MTFConfig,
    measure_angle: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Compute frequency axis and MTF from one LSF."""
    if lsf.size == 0:
        raise ValueError("LSF computation failed (empty)")

    lsf_windowed = apply_lsf_window(lsf, config)
    fft_lsf = np.fft.fft(lsf_windowed)
    mtf = np.abs(fft_lsf[: len(fft_lsf) // 2])
    if mtf.size == 0 or mtf[0] <= 0:
        raise ValueError("Zero mean component in MTF")

    mtf_raw = mtf / mtf[0]
    sample_spacing_px = 1.0 / config.oversample_factor
    freq_cyc_per_pixel = np.fft.fftfreq(len(lsf_windowed), d=sample_spacing_px)[: len(lsf_windowed) // 2]
    pixel_pitch_mm = config.pixel_size_um / 1000.0
    frequencies_raw = freq_cyc_per_pixel / pixel_pitch_mm

    if config.apply_derivative_correction and config.derivative_mode == "iso":
        sample_spacing_mm = pixel_pitch_mm / config.oversample_factor
        omega = 2.0 * np.pi * frequencies_raw * sample_spacing_mm
        sin_omega = np.sin(omega)
        corr = np.ones_like(omega)
        mask = np.abs(sin_omega) > 1e-8
        corr[mask] = omega[mask] / sin_omega[mask]
        if config.derivative_correction_max > 0:
            corr = np.minimum(corr, config.derivative_correction_max)
        mtf_raw = mtf_raw * corr

    mtf_peak_raw = float(np.max(mtf_raw)) if mtf_raw.size > 0 else 0.0
    mtf_used = mtf_raw
    if config.mtf_clip_max > 0:
        mtf_used = np.minimum(mtf_raw, config.mtf_clip_max)

    frequencies = frequencies_raw
    if config.apply_angle_correction:
        cos_theta = float(abs(np.cos(np.radians(measure_angle))))
        frequencies = frequencies_raw * cos_theta

    if config.clip_to_nyquist:
        sensor_nyquist = 1000.0 / (2.0 * config.pixel_size_um)
        mask = frequencies <= sensor_nyquist
        if np.any(mask):
            frequencies = frequencies[mask]
            mtf_raw = mtf_raw[mask]
            mtf_used = mtf_used[mask]

    min_len = min(frequencies.size, mtf_raw.size, mtf_used.size)
    frequencies = frequencies[:min_len]
    mtf_raw = mtf_raw[:min_len]
    mtf_used = mtf_used[:min_len]
    return frequencies, mtf_raw, mtf_used, lsf_windowed, mtf_peak_raw


def find_mtf_frequency(frequencies: np.ndarray, mtf: np.ndarray, threshold: float) -> float:
    """Find the frequency where the MTF crosses a threshold."""
    if frequencies.size == 0 or mtf.size == 0:
        return 0.0
    mask = frequencies >= 0
    freq_pos = frequencies[mask]
    mtf_pos = mtf[mask]
    for idx in range(mtf_pos.size - 1):
        if mtf_pos[idx] >= threshold > mtf_pos[idx + 1]:
            f1 = freq_pos[idx]
            f2 = freq_pos[idx + 1]
            m1 = mtf_pos[idx]
            m2 = mtf_pos[idx + 1]
            if m1 != m2:
                return float(f1 + (threshold - m1) * (f2 - f1) / (m2 - m1))
    return float(freq_pos[-1]) if freq_pos.size > 0 else 0.0


def calculate_diffraction_mtf(frequencies: np.ndarray, config: MTFConfig) -> np.ndarray:
    """Calculate a theoretical diffraction-limited MTF curve."""
    if config.f_number <= 0:
        return np.ones_like(frequencies)
    cutoff_freq = 1000.0 / (config.wavelength_um * config.f_number)
    normalized = np.clip(np.abs(frequencies) / cutoff_freq, 0.0, 1.0)
    mtf_diff = (2.0 / np.pi) * (
        np.arccos(normalized) - normalized * np.sqrt(1.0 - normalized**2)
    )
    mtf_diff[frequencies > cutoff_freq] = 0.0
    return mtf_diff


def validate_edge_crossing(
    roi: np.ndarray,
    config: MTFConfig,
) -> tuple[bool, str, Optional[tuple[float, float, float, float]], Optional[str]]:
    """Validate that one dominant edge crosses the ROI boundaries."""
    if roi is None or roi.size == 0:
        return False, "empty ROI", None, None

    gray = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    if height < 4 or width < 4:
        return False, "ROI too small", None, None

    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx**2 + gy**2)
    if float(np.max(mag)) <= 1e-6:
        return False, "no gradients", None, None

    thresh = np.percentile(mag, config.edge_validation_percentile)
    ys, xs = np.where(mag >= thresh)
    if xs.size < max(1, config.edge_validation_min_points):
        return False, "insufficient edge points", None, None

    points = np.column_stack((xs, ys)).astype(np.float32)
    try:
        vx, vy, x0, y0 = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    except Exception:
        return False, "line fit failed", None, None

    eps = 1e-6
    hits: set[str] = set()
    if abs(vx) > eps:
        t_left = (0 - x0) / vx
        y_left = y0 + t_left * vy
        if 0 <= y_left <= height - 1:
            hits.add("left")
        t_right = ((width - 1) - x0) / vx
        y_right = y0 + t_right * vy
        if 0 <= y_right <= height - 1:
            hits.add("right")
    if abs(vy) > eps:
        t_top = (0 - y0) / vy
        x_top = x0 + t_top * vx
        if 0 <= x_top <= width - 1:
            hits.add("top")
        t_bottom = ((height - 1) - y0) / vy
        x_bottom = x0 + t_bottom * vx
        if 0 <= x_bottom <= width - 1:
            hits.add("bottom")

    hits_str = ",".join(sorted(hits)) if hits else ""
    line = (float(x0), float(y0), float(vx), float(vy))
    if ("left" in hits and "right" in hits) or ("top" in hits and "bottom" in hits):
        return True, "", line, hits_str
    if hits:
        return False, f"edge intersects only {sorted(hits)}", line, hits_str
    return False, "edge does not intersect ROI borders", line, hits_str


class MTFAnalyzer:
    """Standalone MTF analyzer based on the repo slanted-edge implementation."""

    def __init__(self, config: Optional[MTFConfig] = None):
        self.config = config or MTFConfig()
        self.config.validate()

    def check_image_quality(self, roi: np.ndarray) -> dict[str, object]:
        """Check basic quality constraints before MTF analysis."""
        res = {"valid": True, "reason": "", "contrast": 0.0}
        if roi.size == 0:
            return {"valid": False, "reason": "Empty ROI", "contrast": 0.0}

        michelson = calculate_michelson_contrast(roi)
        res["contrast"] = michelson
        if michelson < 0.1:
            res["valid"] = False
            res["reason"] = f"Low Contrast ({michelson:.2f})"
            return res

        is_8bit = roi.dtype == np.uint8
        sat_high = 255 if is_8bit else 65535
        sat_percent = (np.sum(roi >= (sat_high - 1)) / roi.size) * 100.0
        if sat_percent > 2.0:
            res["valid"] = False
            res["reason"] = f"Overexposure/Clipping ({sat_percent:.1f}% saturated)"
            return res

        max_value = float(np.max(roi))
        if is_8bit and max_value < 50:
            res["valid"] = False
            res["reason"] = f"Underexposed (max {max_value:.1f})"
            return res
        return res

    def compute_mtf(
        self,
        image: np.ndarray,
        roi: Optional[tuple[int, int, int, int]] = None,
        roi_origin: Optional[tuple[int, int]] = None,
    ) -> MTFResult:
        """Compute MTF for a dense or raw synthetic image."""
        gray = self._prepare_gray_image(image)
        roi_img, roi_bounds = self._extract_roi(gray, roi)
        if roi_img is None:
            return MTFResult(valid=False, error_msg="Failed to extract ROI")

        absolute_roi_origin = self._resolve_absolute_roi_origin(roi_bounds, roi_origin)
        quality_res = self.check_image_quality(roi_img)
        if not bool(quality_res["valid"]):
            return MTFResult(
                valid=False,
                error_msg=f"Image Quality Low: {quality_res['reason']}",
                contrast=float(quality_res["contrast"]),
            )

        normal_angle = self._detect_gradient_normal_angle(roi_img)
        if normal_angle is None:
            return MTFResult(valid=False, error_msg="No edge detected")

        edge_warning = ""
        edge_hits = None
        edge_validation_ok = None
        if self.config.edge_validation_mode != "off":
            ok, msg, _, edge_hits = validate_edge_crossing(roi_img, self.config)
            if not ok:
                if self.config.edge_validation_mode == "fail":
                    return MTFResult(valid=False, error_msg=f"Edge validation failed: {msg}")
                edge_warning = f"Edge validation warning: {msg}"
            edge_validation_ok = ok

        angle_mod = normal_angle % 180
        rotate_for_projection = False
        if 45 <= angle_mod <= 135:
            edge_direction = "horizontal"
            measure_angle = normal_angle - 90
            rotate_for_projection = True
        else:
            edge_direction = "vertical"
            measure_angle = normal_angle

        measure_angle = self._normalize_measure_angle(measure_angle)
        if abs(measure_angle) < self.config.min_edge_angle:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=(
                    f"Edge angle too small: {measure_angle:.1f} deg "
                    f"(min: {self.config.min_edge_angle:.1f} deg)"
                ),
                edge_direction=edge_direction,
            )
        if abs(measure_angle) > self.config.max_edge_angle:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=(
                    f"Edge angle too large: {measure_angle:.1f} deg "
                    f"(max: {self.config.max_edge_angle:.1f} deg)"
                ),
                edge_direction=edge_direction,
            )

        if self.config.input_mode == "raw_bayer_rggb":
            return self._compute_raw_green_result(
                roi_img=roi_img,
                absolute_roi_origin=absolute_roi_origin,
                measure_angle=measure_angle,
                edge_direction=edge_direction,
                rotate_for_projection=rotate_for_projection,
                edge_warning=edge_warning,
                edge_validation_ok=edge_validation_ok,
                edge_hits=edge_hits,
            )

        roi_to_process = roi_img
        if rotate_for_projection:
            roi_to_process = cv2.rotate(roi_img, cv2.ROTATE_90_CLOCKWISE)
        return self._compute_dense_result(
            roi_to_process=roi_to_process,
            measure_angle=measure_angle,
            edge_direction=edge_direction,
            edge_warning=edge_warning,
            edge_validation_ok=edge_validation_ok,
            edge_hits=edge_hits,
        )

    def _normalize_measure_angle(self, measure_angle: float) -> float:
        measure_angle = ((measure_angle + 180.0) % 360.0) - 180.0
        if measure_angle > 90.0:
            measure_angle -= 180.0
        if measure_angle < -90.0:
            measure_angle += 180.0
        return float(measure_angle)

    def _analyze_esf_curve(self, esf: np.ndarray, measure_angle: float) -> dict[str, object]:
        if esf.size < 10:
            raise ValueError("ESF too short for analysis")

        esf_raw = esf
        esf, smooth_warning = smooth_esf(esf, self.config)
        lsf = compute_lsf(esf, self.config)
        if lsf.size == 0:
            raise ValueError("LSF computation failed (empty)")

        frequencies, mtf_raw, mtf_used, _, mtf_peak_raw = compute_mtf_from_lsf(
            lsf,
            self.config,
            measure_angle,
        )
        return {
            "esf_raw": esf_raw,
            "esf": esf,
            "lsf": lsf,
            "frequencies": frequencies,
            "mtf_raw": mtf_raw,
            "mtf_used": mtf_used,
            "smooth_warning": smooth_warning,
            "mtf_peak_raw": mtf_peak_raw,
            "mtf50": find_mtf_frequency(frequencies, mtf_raw, 0.5),
            "mtf20": find_mtf_frequency(frequencies, mtf_raw, 0.2),
            "mtf10": find_mtf_frequency(frequencies, mtf_raw, 0.1),
        }

    def _compute_dense_result(
        self,
        roi_to_process: np.ndarray,
        measure_angle: float,
        edge_direction: str,
        edge_warning: str,
        edge_validation_ok: Optional[bool],
        edge_hits: Optional[str],
    ) -> MTFResult:
        try:
            curve = self._analyze_esf_curve(
                compute_esf(
                    roi_to_process.astype(np.float64),
                    -measure_angle,
                    self.config.oversample_factor,
                ),
                measure_angle,
            )
        except ValueError as exc:
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg=str(exc),
                edge_direction=edge_direction,
            )

        mtf_ideal = calculate_diffraction_mtf(curve["frequencies"], self.config)
        warning_msg = self._build_warning_message(
            edge_warning=edge_warning,
            curve_warnings=[str(curve["smooth_warning"])],
            mtf_peak_raw=float(curve["mtf_peak_raw"]),
            edge_validation_ok=edge_validation_ok,
            edge_hits=edge_hits,
        )
        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)
        return MTFResult(
            mtf50=float(curve["mtf50"]),
            mtf20=float(curve["mtf20"]),
            mtf10=float(curve["mtf10"]),
            frequencies=np.asarray(curve["frequencies"], dtype=np.float64),
            mtf_values=np.asarray(curve["mtf_used"], dtype=np.float64),
            mtf_ideal=mtf_ideal,
            esf=np.asarray(curve["esf"], dtype=np.float64),
            lsf=np.asarray(curve["lsf"], dtype=np.float64),
            edge_angle=measure_angle,
            valid=True,
            edge_direction=edge_direction,
            sensor_nyquist=sensor_nyquist,
            mtf_peak=float(np.max(curve["mtf_used"])) if len(curve["mtf_used"]) > 0 else 0.0,
            mtf_peak_raw=float(curve["mtf_peak_raw"]),
            mtf_clipped=bool(self.config.mtf_clip_max > 0),
            warning_msg=warning_msg,
            capture_mode="dense_gray",
        )

    def _compute_raw_green_result(
        self,
        roi_img: np.ndarray,
        absolute_roi_origin: tuple[int, int],
        measure_angle: float,
        edge_direction: str,
        rotate_for_projection: bool,
        edge_warning: str,
        edge_validation_ok: Optional[bool],
        edge_hits: Optional[str],
    ) -> MTFResult:
        sample_groups = extract_rggb_green_samples(
            roi_img,
            origin_x=absolute_roi_origin[0],
            origin_y=absolute_roi_origin[1],
            pattern=self.config.raw_bayer_pattern,
        )
        roi_h, roi_w = roi_img.shape[:2]
        group_curves: dict[str, dict[str, object]] = {}
        curve_warnings: list[str] = []

        for group_name, (sample_x, sample_y, sample_values) in sample_groups.items():
            if rotate_for_projection:
                proj_x, proj_y, proj_w, proj_h = rotate_sample_coordinates_90_cw(
                    sample_x,
                    sample_y,
                    roi_w,
                    roi_h,
                )
            else:
                proj_x, proj_y = sample_x, sample_y
                proj_w, proj_h = roi_w, roi_h
            esf = compute_esf_from_samples(
                proj_x,
                proj_y,
                sample_values,
                -measure_angle,
                self.config.oversample_factor,
                proj_w,
                proj_h,
            )
            try:
                curve = self._analyze_esf_curve(esf, measure_angle)
            except ValueError as exc:
                return MTFResult(
                    edge_angle=measure_angle,
                    valid=False,
                    error_msg=f"{group_name.upper()} analysis failed: {exc}",
                    edge_direction=edge_direction,
                )
            group_curves[group_name] = curve
            if curve["smooth_warning"]:
                curve_warnings.append(f"{group_name.upper()}: {curve['smooth_warning']}")

        if {"g1", "g2"} - set(group_curves):
            return MTFResult(
                edge_angle=measure_angle,
                valid=False,
                error_msg="Raw green analysis requires both G1 and G2 sample planes",
                edge_direction=edge_direction,
            )

        frequencies, mtf_raw, mtf_used, mtf_ideal = self._merge_group_curves(group_curves)
        avg_esf = self._average_curve([group_curves["g1"]["esf"], group_curves["g2"]["esf"]])
        avg_lsf = self._average_curve([group_curves["g1"]["lsf"], group_curves["g2"]["lsf"]])

        g1_mtf50 = float(group_curves["g1"]["mtf50"])
        g2_mtf50 = float(group_curves["g2"]["mtf50"])
        g1_mtf20 = float(group_curves["g1"]["mtf20"])
        g2_mtf20 = float(group_curves["g2"]["mtf20"])
        g1_mtf10 = float(group_curves["g1"]["mtf10"])
        g2_mtf10 = float(group_curves["g2"]["mtf10"])
        mean_pair = (g1_mtf50 + g2_mtf50) / 2.0
        g1_g2_delta_pct = abs(g1_mtf50 - g2_mtf50) / mean_pair * 100.0 if mean_pair > 0 else 0.0

        if (
            self.config.raw_green_pair_warn_pct > 0
            and g1_g2_delta_pct > self.config.raw_green_pair_warn_pct
        ):
            curve_warnings.append(
                f"G1/G2 mismatch {g1_g2_delta_pct:.1f}% exceeds "
                f"{self.config.raw_green_pair_warn_pct:.1f}%"
            )

        mtf_peak_raw = float(np.max(mtf_raw)) if mtf_raw.size > 0 else 0.0
        warning_msg = self._build_warning_message(
            edge_warning=edge_warning,
            curve_warnings=curve_warnings,
            mtf_peak_raw=mtf_peak_raw,
            edge_validation_ok=edge_validation_ok,
            edge_hits=edge_hits,
        )
        sensor_nyquist = 1000.0 / (2.0 * self.config.pixel_size_um)
        return MTFResult(
            mtf50=find_mtf_frequency(frequencies, mtf_raw, 0.5),
            mtf20=find_mtf_frequency(frequencies, mtf_raw, 0.2),
            mtf10=find_mtf_frequency(frequencies, mtf_raw, 0.1),
            frequencies=frequencies,
            mtf_values=mtf_used,
            mtf_ideal=mtf_ideal,
            esf=avg_esf,
            lsf=avg_lsf,
            edge_angle=measure_angle,
            valid=True,
            edge_direction=edge_direction,
            sensor_nyquist=sensor_nyquist,
            mtf_peak=float(np.max(mtf_used)) if mtf_used.size > 0 else 0.0,
            mtf_peak_raw=mtf_peak_raw,
            mtf_clipped=bool(self.config.mtf_clip_max > 0),
            warning_msg=warning_msg,
            capture_mode="raw_green",
            g1_mtf50=g1_mtf50,
            g2_mtf50=g2_mtf50,
            g1_mtf20=g1_mtf20,
            g2_mtf20=g2_mtf20,
            g1_mtf10=g1_mtf10,
            g2_mtf10=g2_mtf10,
            g1_g2_delta_pct=g1_g2_delta_pct,
        )

    def _average_curve(self, curves: list[np.ndarray]) -> np.ndarray:
        valid_curves = [curve for curve in curves if curve is not None and curve.size > 0]
        if not valid_curves:
            return np.array([], dtype=np.float64)
        max_len = max(curve.size for curve in valid_curves)
        stacked = np.full((len(valid_curves), max_len), np.nan, dtype=np.float64)
        for idx, curve in enumerate(valid_curves):
            stacked[idx, : curve.size] = curve
        return np.nanmean(stacked, axis=0)

    def _merge_group_curves(
        self,
        group_curves: dict[str, dict[str, object]],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        freq_arrays = [
            np.asarray(curve["frequencies"], dtype=np.float64)
            for curve in group_curves.values()
            if np.asarray(curve["frequencies"]).size > 0
        ]
        if not freq_arrays:
            raise ValueError("No valid group frequency arrays for raw-green merge")
        common_max = min(float(freq[-1]) for freq in freq_arrays)
        common_len = max(min(int(freq.size) for freq in freq_arrays), 8)
        frequencies = np.linspace(0.0, common_max, common_len)

        raw_stack = []
        used_stack = []
        for curve in group_curves.values():
            curve_freq = np.asarray(curve["frequencies"], dtype=np.float64)
            curve_raw = np.asarray(curve["mtf_raw"], dtype=np.float64)
            curve_used = np.asarray(curve["mtf_used"], dtype=np.float64)
            raw_stack.append(np.interp(frequencies, curve_freq, curve_raw))
            used_stack.append(np.interp(frequencies, curve_freq, curve_used))

        mtf_raw = np.mean(np.vstack(raw_stack), axis=0)
        mtf_used = np.mean(np.vstack(used_stack), axis=0)
        mtf_ideal = calculate_diffraction_mtf(frequencies, self.config)
        return frequencies, mtf_raw, mtf_used, mtf_ideal

    def _build_warning_message(
        self,
        edge_warning: str,
        curve_warnings: list[str],
        mtf_peak_raw: float,
        edge_validation_ok: Optional[bool],
        edge_hits: Optional[str],
    ) -> str:
        warning_msgs = []
        if edge_warning:
            warning_msgs.append(edge_warning)
        warning_msgs.extend([msg for msg in curve_warnings if msg])
        if edge_validation_ok is False and edge_hits:
            warning_msgs.append(f"edge_hits={edge_hits}")
        if self.config.mtf_warn_threshold > 0 and mtf_peak_raw > self.config.mtf_warn_threshold:
            warning_msgs.append(
                f"MTF overshoot {mtf_peak_raw:.2f} (> {self.config.mtf_warn_threshold:.2f})"
            )
        return "; ".join(warning_msgs)

    def _resolve_absolute_roi_origin(
        self,
        roi_bounds: Optional[tuple[int, int, int, int]],
        roi_origin: Optional[tuple[int, int]],
    ) -> tuple[int, int]:
        base_x = 0 if roi_origin is None else int(roi_origin[0])
        base_y = 0 if roi_origin is None else int(roi_origin[1])
        if roi_bounds is None:
            return base_x, base_y
        return base_x + int(roi_bounds[0]), base_y + int(roi_bounds[1])

    def _prepare_gray_image(self, image: np.ndarray) -> np.ndarray:
        if self.config.input_mode == "raw_bayer_rggb":
            return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _extract_roi(
        self,
        image: np.ndarray,
        roi: Optional[tuple[int, int, int, int]],
    ) -> tuple[Optional[np.ndarray], Optional[tuple[int, int, int, int]]]:
        height, width = image.shape[:2]
        if roi is not None:
            x1, y1, x2, y2 = roi
        else:
            if self.config.roi_center is not None:
                cx, cy = self.config.roi_center
            else:
                cx, cy = width // 2, height // 2
            x1 = max(0, cx - self.config.roi_width // 2)
            x2 = min(width, cx + self.config.roi_width // 2)
            y1 = max(0, cy - self.config.roi_height // 2)
            y2 = min(height, cy + self.config.roi_height // 2)

        if x1 >= x2 or y1 >= y2:
            return None, None
        return image[y1:y2, x1:x2], (x1, y1, x2, y2)

    def _detect_gradient_normal_angle(self, roi: np.ndarray) -> Optional[float]:
        if roi is None or roi.size == 0:
            return None

        img_f = roi.astype(np.float64)
        k_re = np.array(
            [
                [-0.0165, -0.0238, -0.0210, 0.0, 0.0210, 0.0238, 0.0165],
                [-0.0416, -0.0673, -0.0683, 0.0, 0.0683, 0.0673, 0.0416],
                [-0.0637, -0.1162, -0.1432, 0.0, 0.1432, 0.1162, 0.0637],
                [-0.0766, -0.1491, -0.2078, 0.0, 0.2078, 0.1491, 0.0766],
                [-0.0637, -0.1162, -0.1432, 0.0, 0.1432, 0.1162, 0.0637],
                [-0.0416, -0.0673, -0.0683, 0.0, 0.0683, 0.0673, 0.0416],
                [-0.0165, -0.0238, -0.0210, 0.0, 0.0210, 0.0238, 0.0165],
            ],
            dtype=np.float64,
        )
        k_im = k_re.T
        a11_re = cv2.filter2D(img_f, cv2.CV_64F, k_re)
        a11_im = cv2.filter2D(img_f, cv2.CV_64F, k_im)

        magnitude = np.sqrt(a11_re**2 + a11_im**2)
        if float(np.max(magnitude)) <= 1e-6:
            return None
        thresh = np.percentile(magnitude, 90)
        mask = magnitude > thresh
        if int(np.sum(mask)) < 10:
            return None

        phis = np.arctan2(a11_im[mask], a11_re[mask])
        mean_sin = np.mean(np.sin(phis))
        mean_cos = np.mean(np.cos(phis))
        mean_phi = np.arctan2(mean_sin, mean_cos)
        return float(np.degrees(mean_phi))


def generate_oversampled_slanted_edge(
    size: int,
    angle_deg: float,
    blur_sigma_px: float,
    oversample_factor: int,
) -> np.ndarray:
    """Generate one physically more faithful slanted edge via oversampling."""
    if size <= 0:
        raise ValueError("size must be positive")
    if oversample_factor < 1:
        raise ValueError("oversample_factor must be >= 1")

    hi_size = int(size) * int(oversample_factor)
    hi_coords = (np.arange(hi_size, dtype=np.float64) + 0.5) / float(oversample_factor) - float(size) / 2.0
    yy, xx = np.meshgrid(hi_coords, hi_coords, indexing="ij")
    angle_rad = np.radians(float(angle_deg))
    edge = (xx - yy * np.tan(angle_rad) > 0.0).astype(np.float32)

    sigma_hi = float(blur_sigma_px) * float(oversample_factor)
    if sigma_hi > 0.0:
        kernel_size = max(3, int(math.ceil(6.0 * sigma_hi)) | 1)
        edge = cv2.GaussianBlur(
            edge,
            (kernel_size, kernel_size),
            sigmaX=sigma_hi,
            sigmaY=sigma_hi,
            borderType=cv2.BORDER_REPLICATE,
        )

    sensor = edge.reshape(size, oversample_factor, size, oversample_factor).mean(axis=(1, 3))
    sensor = np.clip(sensor, 0.0, 1.0)
    black_level = 512.0
    white_level = 65024.0
    return np.round(black_level + sensor * (white_level - black_level)).astype(np.uint16)


def generate_dense_edge(
    size: int = 240,
    angle_deg: float = 5.0,
    blur_sigma: float = 1.0,
    oversample_factor: int = QUICK_SCENE_OVERSAMPLE,
) -> np.ndarray:
    """Generate a synthetic 16-bit slanted edge scene."""
    return generate_oversampled_slanted_edge(
        size=size,
        angle_deg=angle_deg,
        blur_sigma_px=blur_sigma,
        oversample_factor=oversample_factor,
    )


def green_infill_from_raw(raw_bayer: np.ndarray) -> np.ndarray:
    """Build a simple green-infill reference image from raw Bayer samples."""
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


def build_scientific_case(
    result: MTFResult,
    *,
    path: str,
    angle_deg: float,
    blur_sigma_px: float,
    roi_origin_xy: tuple[int, int],
    pixel_size_um: float,
    raw_vs_dense_delta_pct: float = 0.0,
) -> ScientificCaseResult:
    """Assemble one benchmark case with analytical reference metrics."""
    reference = build_reference_metrics(
        pixel_size_um=pixel_size_um,
        blur_sigma_px=blur_sigma_px,
        frequencies_lpmm=result.frequencies if result.valid else None,
    )
    curve_rmse = compute_curve_rmse(result.frequencies, result.mtf_values, reference.mtf_values)
    return ScientificCaseResult(
        path=path,
        angle_deg=float(angle_deg),
        blur_sigma_px=float(blur_sigma_px),
        roi_origin_xy=(int(roi_origin_xy[0]), int(roi_origin_xy[1])),
        valid=bool(result.valid),
        edge_angle_deg=float(result.edge_angle),
        mtf50_lpmm=float(result.mtf50),
        mtf20_lpmm=float(result.mtf20),
        mtf10_lpmm=float(result.mtf10),
        reference_mtf50_lpmm=float(reference.mtf50),
        reference_mtf20_lpmm=float(reference.mtf20),
        reference_mtf10_lpmm=float(reference.mtf10),
        mtf50_rel_error_pct=relative_error_pct(result.mtf50, reference.mtf50),
        mtf20_rel_error_pct=relative_error_pct(result.mtf20, reference.mtf20),
        mtf10_rel_error_pct=relative_error_pct(result.mtf10, reference.mtf10),
        curve_rmse=curve_rmse,
        warning=result.warning_msg,
        error=result.error_msg,
        g1_mtf50_lpmm=float(result.g1_mtf50),
        g2_mtf50_lpmm=float(result.g2_mtf50),
        g1_g2_delta_pct=float(result.g1_g2_delta_pct),
        raw_vs_dense_delta_pct=float(raw_vs_dense_delta_pct),
    )


def summarize_raw_group(
    angle_deg: float,
    blur_sigma_px: float,
    raw_cases: list[ScientificCaseResult],
    dense_case: ScientificCaseResult,
) -> RawGroupSummary:
    """Aggregate the four raw ROI-origin variants of one physical scene."""
    mtf50_values = [case.mtf50_lpmm for case in raw_cases if case.valid]
    mean_raw = float(np.mean(mtf50_values)) if mtf50_values else 0.0
    max_pair_delta = max((case.g1_g2_delta_pct for case in raw_cases), default=float("inf"))
    delta_pct = relative_error_pct(mean_raw, dense_case.mtf50_lpmm) if dense_case.valid else float("inf")
    return RawGroupSummary(
        angle_deg=float(angle_deg),
        blur_sigma_px=float(blur_sigma_px),
        mean_raw_mtf50_lpmm=mean_raw,
        roi_spread_pct=spread_pct(mtf50_values),
        max_g1_g2_delta_pct=float(max_pair_delta),
        raw_vs_dense_delta_pct=float(delta_pct),
    )


def ensure_matplotlib():
    """Import matplotlib lazily so --no-png works without it."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError(
            "matplotlib is required for PNG export. Install it or use --no-png."
        ) from exc
    return plt


def normalize_for_display(image: np.ndarray) -> np.ndarray:
    """Normalize one image to 8-bit display range."""
    return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def save_scene_png(image: np.ndarray, path: Path, title: str) -> None:
    """Save one grayscale scene image using matplotlib."""
    plt = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(5, 5), constrained_layout=True)
    ax.imshow(normalize_for_display(image), cmap="gray", vmin=0, vmax=255)
    ax.set_title(title)
    ax.set_axis_off()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_result_plot(result: MTFResult, path: Path, title: str) -> None:
    """Save ESF/LSF/MTF plots for one result."""
    plt = ensure_matplotlib()
    fig, axes = plt.subplots(3, 1, figsize=(8, 8), constrained_layout=True)

    axes[0].plot(result.esf, color="tab:blue")
    axes[0].set_title(f"{title} - ESF")
    axes[0].set_ylabel("Intensity")

    axes[1].plot(result.lsf, color="tab:orange")
    axes[1].set_title(f"{title} - LSF")
    axes[1].set_ylabel("dI/dx")

    axes[2].plot(result.frequencies, result.mtf_values, color="tab:green", label="MTF")
    if result.mtf_ideal.size > 0:
        axes[2].plot(result.frequencies, result.mtf_ideal, "--", color="tab:red", label="Ideal")
    axes[2].axhline(0.5, color="gray", linestyle=":", linewidth=1)
    axes[2].axhline(0.2, color="gray", linestyle=":", linewidth=1)
    axes[2].axhline(0.1, color="gray", linestyle=":", linewidth=1)
    axes[2].set_title(f"{title} - MTF")
    axes[2].set_xlabel("Frequency (lp/mm)")
    axes[2].set_ylabel("MTF")
    axes[2].set_ylim(0.0, max(1.1, float(np.nanmax(result.mtf_values)) if result.mtf_values.size > 0 else 1.1))
    axes[2].legend(loc="best")

    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_summary_png(checks: list[CheckResult], path: Path) -> None:
    """Save one summary sheet with pass/fail text and core metrics."""
    plt = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(9, 6), constrained_layout=True)
    ax.set_axis_off()
    ax.set_title("Synthetic MTF Validation Summary", loc="left", fontsize=14, fontweight="bold")

    y = 0.92
    for check in checks:
        color = "tab:green" if check.passed else "tab:red"
        ax.text(0.02, y, f"[{'PASS' if check.passed else 'FAIL'}] {check.name}", color=color, fontsize=11, fontweight="bold")
        y -= 0.05
        ax.text(0.04, y, check.summary, fontsize=10)
        y -= 0.05
        for key, value in check.metrics.items():
            ax.text(0.08, y, f"{key}: {value}", fontsize=9, family="monospace")
            y -= 0.04
        y -= 0.03

    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_dense_config(pixel_size_um: float, roi_size: int) -> MTFConfig:
    """Create dense-path config with stable defaults."""
    return MTFConfig(
        pixel_size_um=pixel_size_um,
        input_mode="dense_gray",
        roi_width=roi_size,
        roi_height=roi_size,
        min_edge_angle=2.0,
        max_edge_angle=10.0,
        esf_smooth_mode="none",
        edge_validation_mode="warn",
    )


def build_raw_config(pixel_size_um: float, roi_size: int) -> MTFConfig:
    """Create raw-path config with stable defaults."""
    return MTFConfig(
        pixel_size_um=pixel_size_um,
        input_mode="raw_bayer_rggb",
        raw_bayer_pattern="RGGB",
        roi_width=roi_size,
        roi_height=roi_size,
        min_edge_angle=2.0,
        max_edge_angle=10.0,
        esf_smooth_mode="none",
        edge_validation_mode="warn",
        raw_green_pair_warn_pct=5.0,
    )


def run_parity_check() -> CheckResult:
    """Validate absolute ROI parity for G1/G2 extraction."""
    sensor = np.zeros((6, 6), dtype=np.uint16)
    sensor[0::2, 0::2] = 11
    sensor[0::2, 1::2] = 101
    sensor[1::2, 0::2] = 202
    sensor[1::2, 1::2] = 22

    even_groups = extract_rggb_green_samples(sensor[0:4, 0:4], origin_x=0, origin_y=0)
    odd_groups = extract_rggb_green_samples(sensor[1:5, 1:5], origin_x=1, origin_y=1)

    even_g1_x, even_g1_y, even_g1_values = even_groups["g1"]
    even_g2_x, even_g2_y, even_g2_values = even_groups["g2"]
    odd_g1_x, odd_g1_y, odd_g1_values = odd_groups["g1"]
    odd_g2_x, odd_g2_y, odd_g2_values = odd_groups["g2"]

    passed = (
        np.all(even_g1_values == 101.0)
        and np.all(even_g2_values == 202.0)
        and np.all(odd_g1_values == 101.0)
        and np.all(odd_g2_values == 202.0)
        and np.array_equal(even_g1_x, np.array([1.0, 3.0, 1.0, 3.0]))
        and np.array_equal(even_g1_y, np.array([0.0, 0.0, 2.0, 2.0]))
        and np.array_equal(even_g2_x, np.array([0.0, 2.0, 0.0, 2.0]))
        and np.array_equal(even_g2_y, np.array([1.0, 1.0, 3.0, 3.0]))
        and np.array_equal(odd_g1_x, np.array([0.0, 2.0, 0.0, 2.0]))
        and np.array_equal(odd_g1_y, np.array([1.0, 1.0, 3.0, 3.0]))
        and np.array_equal(odd_g2_x, np.array([1.0, 3.0, 1.0, 3.0]))
        and np.array_equal(odd_g2_y, np.array([0.0, 0.0, 2.0, 2.0]))
    )

    return CheckResult(
        name="ROI Parity",
        passed=passed,
        summary=(
            "Absolute Bayer parity stays tied to the physical sensor pattern for even "
            "and odd ROI origins."
        ),
        metrics={
            "even_g1_mean": f"{float(np.mean(even_g1_values)):.1f}",
            "even_g2_mean": f"{float(np.mean(even_g2_values)):.1f}",
            "odd_g1_mean": f"{float(np.mean(odd_g1_values)):.1f}",
            "odd_g2_mean": f"{float(np.mean(odd_g2_values)):.1f}",
        },
    )


def evaluate_dense_result(result: MTFResult, config: MTFConfig) -> CheckResult:
    """Check dense-path acceptance criteria."""
    passed = (
        result.valid
        and result.mtf50 > 0.0
        and config.min_edge_angle <= abs(result.edge_angle) <= config.max_edge_angle
        and result.esf.size > 0
        and result.lsf.size > 0
        and result.frequencies.size > 0
        and result.mtf_values.size > 0
    )
    summary = result.error_msg if not result.valid else "Dense slanted-edge path returned valid ESF/LSF/MTF data."
    return CheckResult(
        name="Dense Scene",
        passed=passed,
        summary=summary,
        metrics={
            "valid": result.valid,
            "mtf50_lpmm": f"{result.mtf50:.4f}",
            "edge_angle_deg": f"{result.edge_angle:.4f}",
            "nyquist_lpmm": f"{result.nyquist_frequency:.4f}",
            "warning": result.warning_msg or "-",
        },
    )


def evaluate_raw_result(result: MTFResult) -> CheckResult:
    """Check raw-path acceptance criteria."""
    passed = (
        result.valid
        and result.g1_mtf50 > 0.0
        and result.g2_mtf50 > 0.0
        and result.g1_g2_delta_pct <= 5.0
    )
    summary = result.error_msg if not result.valid else "Raw green path returned valid G1/G2 MTF metrics."
    return CheckResult(
        name="Raw Scene",
        passed=passed,
        summary=summary,
        metrics={
            "valid": result.valid,
            "mtf50_lpmm": f"{result.mtf50:.4f}",
            "g1_mtf50_lpmm": f"{result.g1_mtf50:.4f}",
            "g2_mtf50_lpmm": f"{result.g2_mtf50:.4f}",
            "g1_g2_delta_pct": f"{result.g1_g2_delta_pct:.4f}",
            "warning": result.warning_msg or "-",
        },
    )


def evaluate_raw_vs_dense(
    dense_result: MTFResult,
    raw_result: MTFResult,
    infill_result: MTFResult,
) -> CheckResult:
    """Check raw-vs-dense agreement and infill regression behavior."""
    raw_error = abs(raw_result.mtf50 - dense_result.mtf50)
    infill_error = abs(infill_result.mtf50 - dense_result.mtf50)
    allowed_error = max(1.0, dense_result.mtf50 * 0.05)
    passed = (
        dense_result.valid
        and raw_result.valid
        and infill_result.valid
        and raw_error <= allowed_error
        and raw_error < infill_error
    )
    return CheckResult(
        name="Raw vs Dense",
        passed=passed,
        summary=(
            "Raw Bayer green sampling should stay close to the dense reference and "
            "outperform simple green infill."
        ),
        metrics={
            "dense_mtf50_lpmm": f"{dense_result.mtf50:.4f}",
            "raw_mtf50_lpmm": f"{raw_result.mtf50:.4f}",
            "infill_mtf50_lpmm": f"{infill_result.mtf50:.4f}",
            "raw_error_lpmm": f"{raw_error:.4f}",
            "infill_error_lpmm": f"{infill_error:.4f}",
            "allowed_error_lpmm": f"{allowed_error:.4f}",
        },
    )


def evaluate_reference_self_test(pixel_size_um: float) -> CheckResult:
    """Validate the analytical reference curve itself before the sweep runs."""
    reference = build_reference_metrics(
        pixel_size_um=pixel_size_um,
        blur_sigma_px=SCIENTIFIC_BLUR_SIGMAS_PX[0],
    )
    passed = (
        reference.monotonic
        and reference.nyquist_clipped
        and 0.0 < reference.mtf50 < reference.mtf20 < reference.mtf10
    )
    return CheckResult(
        name="Reference Self-Test",
        passed=passed,
        summary="Analytical Gaussian-PSF * pixel-aperture reference is monotonic and clipped to Nyquist.",
        metrics={
            "reference_mtf50_lpmm": f"{reference.mtf50:.4f}",
            "reference_mtf20_lpmm": f"{reference.mtf20:.4f}",
            "reference_mtf10_lpmm": f"{reference.mtf10:.4f}",
            "monotonic": reference.monotonic,
            "nyquist_clipped": reference.nyquist_clipped,
        },
    )


def evaluate_scientific_bias(
    cases: list[ScientificCaseResult],
    *,
    name: str,
    mtf_error_limit_pct: float,
    curve_rmse_limit: float,
) -> CheckResult:
    """Evaluate analytical bias against the scientific reference."""
    invalid_count = sum(1 for case in cases if not case.valid)
    valid_cases = [case for case in cases if case.valid]
    max_mtf50 = max((case.mtf50_rel_error_pct for case in valid_cases), default=float("inf"))
    max_mtf20 = max((case.mtf20_rel_error_pct for case in valid_cases), default=float("inf"))
    max_rmse = max((case.curve_rmse for case in valid_cases), default=float("inf"))
    passed = (
        len(valid_cases) == len(cases)
        and max_mtf50 <= mtf_error_limit_pct
        and max_mtf20 <= mtf_error_limit_pct
        and max_rmse <= curve_rmse_limit
    )
    return CheckResult(
        name=name,
        passed=passed,
        summary="Measured MTF tracks the analytical reference within the configured bias and RMSE limits.",
        metrics={
            "cases": len(cases),
            "invalid_cases": invalid_count,
            "max_mtf50_error_pct": f"{max_mtf50:.4f}",
            "max_mtf20_error_pct": f"{max_mtf20:.4f}",
            "max_curve_rmse": f"{max_rmse:.4f}",
            "mtf_error_limit_pct": f"{mtf_error_limit_pct:.4f}",
            "curve_rmse_limit": f"{curve_rmse_limit:.4f}",
        },
    )


def evaluate_scientific_ranking(
    dense_cases: list[ScientificCaseResult],
    raw_groups: list[RawGroupSummary],
) -> CheckResult:
    """Validate monotonic blur ranking for dense and raw paths."""
    dense_map = {(case.angle_deg, case.blur_sigma_px): case for case in dense_cases}
    raw_map = {(group.angle_deg, group.blur_sigma_px): group for group in raw_groups}
    dense_max_increase = 0.0
    raw_max_increase = 0.0
    passed = True

    for angle in SCIENTIFIC_ANGLES_DEG:
        dense_values = []
        raw_values = []
        for sigma in SCIENTIFIC_BLUR_SIGMAS_PX:
            dense_case = dense_map.get((angle, sigma))
            raw_group = raw_map.get((angle, sigma))
            if dense_case is None or not dense_case.valid:
                passed = False
            else:
                dense_values.append(dense_case.mtf50_lpmm)
            if raw_group is None or not np.isfinite(raw_group.mean_raw_mtf50_lpmm):
                passed = False
            else:
                raw_values.append(raw_group.mean_raw_mtf50_lpmm)

        for previous, current in zip(dense_values, dense_values[1:]):
            dense_max_increase = max(dense_max_increase, current - previous)
            if current > previous + MONOTONIC_TOLERANCE_LPMM:
                passed = False
        for previous, current in zip(raw_values, raw_values[1:]):
            raw_max_increase = max(raw_max_increase, current - previous)
            if current > previous + MONOTONIC_TOLERANCE_LPMM:
                passed = False

    return CheckResult(
        name="Ranking",
        passed=passed,
        summary="Increasing blur sigma must never produce a higher MTF50 in the scientific sweep.",
        metrics={
            "max_dense_increase_lpmm": f"{max(0.0, dense_max_increase):.6f}",
            "max_raw_increase_lpmm": f"{max(0.0, raw_max_increase):.6f}",
            "tolerance_lpmm": f"{MONOTONIC_TOLERANCE_LPMM:.6f}",
        },
    )


def evaluate_scientific_invariance(
    dense_cases: list[ScientificCaseResult],
    raw_groups: list[RawGroupSummary],
) -> CheckResult:
    """Validate angular invariance for equal blur across the sweep."""
    dense_map = {(case.angle_deg, case.blur_sigma_px): case for case in dense_cases}
    raw_map = {(group.angle_deg, group.blur_sigma_px): group for group in raw_groups}
    dense_spreads = []
    raw_spreads = []
    passed = True

    for sigma in SCIENTIFIC_BLUR_SIGMAS_PX:
        dense_values = []
        raw_values = []
        for angle in SCIENTIFIC_ANGLES_DEG:
            dense_case = dense_map.get((angle, sigma))
            raw_group = raw_map.get((angle, sigma))
            if dense_case is None or not dense_case.valid:
                passed = False
            else:
                dense_values.append(dense_case.mtf50_lpmm)
            if raw_group is None or not np.isfinite(raw_group.mean_raw_mtf50_lpmm):
                passed = False
            else:
                raw_values.append(raw_group.mean_raw_mtf50_lpmm)

        dense_spreads.append(spread_pct(dense_values))
        raw_spreads.append(spread_pct(raw_values))

    max_dense_spread = max(dense_spreads, default=float("inf"))
    max_raw_spread = max(raw_spreads, default=float("inf"))
    passed = (
        passed
        and max_dense_spread <= SCIENTIFIC_ANGLE_SPREAD_LIMIT_PCT
        and max_raw_spread <= SCIENTIFIC_ANGLE_SPREAD_LIMIT_PCT
    )
    return CheckResult(
        name="Invariance",
        passed=passed,
        summary="For fixed blur, the measured MTF50 should stay angle-stable across the scientific sweep.",
        metrics={
            "max_dense_spread_pct": f"{max_dense_spread:.4f}",
            "max_raw_spread_pct": f"{max_raw_spread:.4f}",
            "spread_limit_pct": f"{SCIENTIFIC_ANGLE_SPREAD_LIMIT_PCT:.4f}",
        },
    )


def evaluate_scientific_raw_parity(raw_groups: list[RawGroupSummary]) -> CheckResult:
    """Validate ROI-origin and G1/G2 parity stability in raw mode."""
    worst_roi_spread = max((group.roi_spread_pct for group in raw_groups), default=float("inf"))
    worst_pair_delta = max((group.max_g1_g2_delta_pct for group in raw_groups), default=float("inf"))
    passed = (
        worst_roi_spread <= SCIENTIFIC_RAW_PARITY_LIMIT_PCT
        and worst_pair_delta <= SCIENTIFIC_RAW_PARITY_LIMIT_PCT
    )
    return CheckResult(
        name="Raw Parity",
        passed=passed,
        summary="Raw G1/G2 results and ROI-origin shifts stay tied to physical Bayer phase and remain invariant.",
        metrics={
            "worst_roi_spread_pct": f"{worst_roi_spread:.4f}",
            "worst_g1_g2_delta_pct": f"{worst_pair_delta:.4f}",
            "limit_pct": f"{SCIENTIFIC_RAW_PARITY_LIMIT_PCT:.4f}",
        },
    )


def evaluate_scientific_raw_vs_dense(raw_groups: list[RawGroupSummary]) -> CheckResult:
    """Validate raw-vs-dense agreement for the same physical scene."""
    worst_delta = max((group.raw_vs_dense_delta_pct for group in raw_groups), default=float("inf"))
    passed = worst_delta <= SCIENTIFIC_RAW_VS_DENSE_LIMIT_PCT
    return CheckResult(
        name="Raw vs Dense",
        passed=passed,
        summary="The mean raw-green MTF50 should stay close to the dense result for the same blur and angle.",
        metrics={
            "worst_delta_pct": f"{worst_delta:.4f}",
            "limit_pct": f"{SCIENTIFIC_RAW_VS_DENSE_LIMIT_PCT:.4f}",
        },
    )


def to_jsonable(value: Any) -> Any:
    """Recursively convert numpy-heavy data structures to JSON-safe values."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, float)):
        if not np.isfinite(value):
            return None
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def write_report_json(report: dict[str, Any], path: Path) -> None:
    """Write one machine-readable report file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(report), handle, indent=2, sort_keys=True)


def save_heatmap(
    matrix: np.ndarray,
    *,
    angles_deg: tuple[float, ...],
    blur_sigmas_px: tuple[float, ...],
    path: Path,
    title: str,
    cbar_label: str,
) -> None:
    """Save one small heatmap artifact."""
    plt = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    image = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_title(title)
    ax.set_xlabel("Angle (deg)")
    ax.set_ylabel("Blur sigma (px)")
    ax.set_xticks(range(len(angles_deg)), [f"{angle:.0f}" for angle in angles_deg])
    ax.set_yticks(range(len(blur_sigmas_px)), [f"{sigma:.1f}" for sigma in blur_sigmas_px])
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label(cbar_label)
    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            value = matrix[row_idx, col_idx]
            if np.isfinite(value):
                ax.text(
                    col_idx,
                    row_idx,
                    f"{value:.1f}",
                    ha="center",
                    va="center",
                    color="white" if value > np.nanmean(matrix) else "black",
                    fontsize=8,
                )
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_raw_parity_plot(
    roi_spread_matrix: np.ndarray,
    pair_delta_matrix: np.ndarray,
    *,
    angles_deg: tuple[float, ...],
    blur_sigmas_px: tuple[float, ...],
    path: Path,
) -> None:
    """Save raw parity stability plots for ROI-origin and G1/G2 deltas."""
    plt = ensure_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for axis, matrix, title, label in (
        (axes[0], roi_spread_matrix, "ROI-Origin Spread", "Spread / mean (%)"),
        (axes[1], pair_delta_matrix, "G1/G2 Delta", "Delta (%)"),
    ):
        image = axis.imshow(matrix, aspect="auto", cmap="magma")
        axis.set_title(title)
        axis.set_xlabel("Angle (deg)")
        axis.set_ylabel("Blur sigma (px)")
        axis.set_xticks(range(len(angles_deg)), [f"{angle:.0f}" for angle in angles_deg])
        axis.set_yticks(range(len(blur_sigmas_px)), [f"{sigma:.1f}" for sigma in blur_sigmas_px])
        cbar = fig.colorbar(image, ax=axis)
        cbar.set_label(label)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_blur_ranking_plot(
    dense_cases: list[ScientificCaseResult],
    raw_groups: list[RawGroupSummary],
    path: Path,
) -> None:
    """Save one ranking plot across blur sigma for all sweep angles."""
    plt = ensure_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True, sharey=True)
    dense_map = {(case.angle_deg, case.blur_sigma_px): case for case in dense_cases}
    raw_map = {(group.angle_deg, group.blur_sigma_px): group for group in raw_groups}

    for angle in SCIENTIFIC_ANGLES_DEG:
        dense_series = [dense_map[(angle, sigma)].mtf50_lpmm for sigma in SCIENTIFIC_BLUR_SIGMAS_PX]
        raw_series = [raw_map[(angle, sigma)].mean_raw_mtf50_lpmm for sigma in SCIENTIFIC_BLUR_SIGMAS_PX]
        axes[0].plot(SCIENTIFIC_BLUR_SIGMAS_PX, dense_series, marker="o", label=f"{angle:.0f} deg")
        axes[1].plot(SCIENTIFIC_BLUR_SIGMAS_PX, raw_series, marker="o", label=f"{angle:.0f} deg")

    axes[0].set_title("Dense Blur Ranking")
    axes[1].set_title("Raw Blur Ranking")
    for axis in axes:
        axis.set_xlabel("Blur sigma (px)")
        axis.set_ylabel("MTF50 (lp/mm)")
        axis.grid(True, linestyle=":", alpha=0.5)
    axes[1].legend(loc="best")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def format_check(check: CheckResult) -> str:
    """Format one CLI block."""
    lines = [
        f"[{check.name}]",
        f"status: {'PASS' if check.passed else 'FAIL'}",
        f"summary: {check.summary}",
    ]
    for key, value in check.metrics.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def summarize_mtf_result(result: Optional[MTFResult]) -> dict[str, Any]:
    """Return a compact JSON-friendly summary of one MTF result."""
    if result is None:
        return {}
    return {
        "valid": bool(result.valid),
        "edge_angle_deg": float(result.edge_angle),
        "mtf50_lpmm": float(result.mtf50),
        "mtf20_lpmm": float(result.mtf20),
        "mtf10_lpmm": float(result.mtf10),
        "warning": result.warning_msg,
        "error": result.error_msg,
        "g1_mtf50_lpmm": float(result.g1_mtf50),
        "g2_mtf50_lpmm": float(result.g2_mtf50),
        "g1_g2_delta_pct": float(result.g1_g2_delta_pct),
    }


def run_quick_validation(
    args: argparse.Namespace,
    output_dir: Path,
) -> tuple[list[CheckResult], dict[str, Any]]:
    """Run the lightweight smoke/regression profile."""
    dense_scene = generate_dense_edge(
        size=args.image_size,
        angle_deg=args.angle_deg,
        blur_sigma=args.blur_sigma,
        oversample_factor=QUICK_SCENE_OVERSAMPLE,
    )
    raw_bayer = dense_scene.copy()
    green_infill = green_infill_from_raw(raw_bayer)

    dense_result = None
    raw_result = None
    infill_result = None
    checks: list[CheckResult] = []

    dense_config = build_dense_config(args.pixel_size_um, args.roi_size)
    dense_result = MTFAnalyzer(dense_config).compute_mtf(dense_scene)
    checks.append(evaluate_dense_result(dense_result, dense_config))

    if args.mode in {"raw", "both"}:
        raw_config = build_raw_config(args.pixel_size_um, args.roi_size)
        raw_result = MTFAnalyzer(raw_config).compute_mtf(raw_bayer)
        infill_result = MTFAnalyzer(build_dense_config(args.pixel_size_um, args.roi_size)).compute_mtf(
            green_infill
        )
        checks.append(evaluate_raw_result(raw_result))
        checks.append(evaluate_raw_vs_dense(dense_result, raw_result, infill_result))
        checks.append(run_parity_check())

    if not args.no_png:
        if dense_result is not None:
            save_scene_png(dense_scene, output_dir / "dense_scene.png", "Synthetic Dense Edge")
            save_result_plot(dense_result, output_dir / "dense_mtf.png", "Dense")
        if raw_result is not None:
            save_scene_png(raw_bayer, output_dir / "raw_scene.png", "Synthetic Raw Bayer Edge")
            save_result_plot(raw_result, output_dir / "raw_mtf.png", "Raw Green")
        save_summary_png(checks, output_dir / "validation_summary.png")

    overall_pass = all(check.passed for check in checks)
    report = {
        "profile": "quick",
        "mode": args.mode,
        "parameters": {
            "pixel_size_um": float(args.pixel_size_um),
            "angle_deg": float(args.angle_deg),
            "blur_sigma_px": float(args.blur_sigma),
            "image_size": int(args.image_size),
            "roi_size": int(args.roi_size),
            "scene_oversample": QUICK_SCENE_OVERSAMPLE,
        },
        "checks": checks,
        "dense_result": summarize_mtf_result(dense_result),
        "raw_result": summarize_mtf_result(raw_result),
        "green_infill_result": summarize_mtf_result(infill_result),
        "overall_pass": overall_pass,
    }
    return checks, report


def run_scientific_validation(
    args: argparse.Namespace,
    output_dir: Path,
) -> tuple[list[CheckResult], dict[str, Any]]:
    """Run the analytical benchmark sweep for comparative test stands."""
    include_raw = args.mode in {"raw", "both"}
    dense_config = build_dense_config(args.pixel_size_um, args.roi_size)
    raw_config = build_raw_config(args.pixel_size_um, args.roi_size)
    dense_analyzer = MTFAnalyzer(dense_config)
    raw_analyzer = MTFAnalyzer(raw_config)

    dense_cases: list[ScientificCaseResult] = []
    raw_cases: list[ScientificCaseResult] = []
    raw_groups: list[RawGroupSummary] = []
    dense_bias_matrix = np.full(
        (len(SCIENTIFIC_BLUR_SIGMAS_PX), len(SCIENTIFIC_ANGLES_DEG)),
        np.nan,
        dtype=np.float64,
    )
    raw_bias_matrix = np.full_like(dense_bias_matrix, np.nan)
    raw_roi_spread_matrix = np.full_like(dense_bias_matrix, np.nan)
    raw_pair_delta_matrix = np.full_like(dense_bias_matrix, np.nan)
    checks: list[CheckResult] = [evaluate_reference_self_test(args.pixel_size_um)]

    for sigma_idx, blur_sigma in enumerate(SCIENTIFIC_BLUR_SIGMAS_PX):
        for angle_idx, angle_deg in enumerate(SCIENTIFIC_ANGLES_DEG):
            scene = generate_dense_edge(
                size=args.image_size,
                angle_deg=angle_deg,
                blur_sigma=blur_sigma,
                oversample_factor=SCIENTIFIC_SCENE_OVERSAMPLE,
            )
            raw_bayer = scene.copy()

            dense_roi = centered_roi_bounds(args.image_size, args.roi_size)
            dense_result = dense_analyzer.compute_mtf(scene, roi=dense_roi)
            dense_case = build_scientific_case(
                dense_result,
                path="dense",
                angle_deg=angle_deg,
                blur_sigma_px=blur_sigma,
                roi_origin_xy=(dense_roi[0], dense_roi[1]),
                pixel_size_um=args.pixel_size_um,
            )
            dense_cases.append(dense_case)
            dense_bias_matrix[sigma_idx, angle_idx] = (
                dense_case.mtf50_rel_error_pct if dense_case.valid else np.nan
            )

            if include_raw:
                scene_raw_cases: list[ScientificCaseResult] = []
                for offset_x, offset_y in SCIENTIFIC_RAW_ROI_OFFSETS:
                    roi = centered_roi_bounds(
                        args.image_size,
                        args.roi_size,
                        offset_x=offset_x,
                        offset_y=offset_y,
                    )
                    raw_result = raw_analyzer.compute_mtf(raw_bayer, roi=roi)
                    raw_delta_pct = (
                        relative_error_pct(raw_result.mtf50, dense_case.mtf50_lpmm)
                        if raw_result.valid and dense_case.valid
                        else float("inf")
                    )
                    raw_case = build_scientific_case(
                        raw_result,
                        path="raw",
                        angle_deg=angle_deg,
                        blur_sigma_px=blur_sigma,
                        roi_origin_xy=(roi[0], roi[1]),
                        pixel_size_um=args.pixel_size_um,
                        raw_vs_dense_delta_pct=raw_delta_pct,
                    )
                    raw_cases.append(raw_case)
                    scene_raw_cases.append(raw_case)

                raw_group = summarize_raw_group(angle_deg, blur_sigma, scene_raw_cases, dense_case)
                raw_groups.append(raw_group)
                raw_valid_errors = [case.mtf50_rel_error_pct for case in scene_raw_cases if case.valid]
                raw_bias_matrix[sigma_idx, angle_idx] = (
                    float(np.mean(raw_valid_errors)) if raw_valid_errors else np.nan
                )
                raw_roi_spread_matrix[sigma_idx, angle_idx] = raw_group.roi_spread_pct
                raw_pair_delta_matrix[sigma_idx, angle_idx] = raw_group.max_g1_g2_delta_pct

    checks.append(
        evaluate_scientific_bias(
            dense_cases,
            name="Dense Bias",
            mtf_error_limit_pct=SCIENTIFIC_DENSE_BIAS_LIMIT_PCT,
            curve_rmse_limit=SCIENTIFIC_DENSE_CURVE_RMSE_LIMIT,
        )
    )
    if include_raw:
        checks.append(
            evaluate_scientific_bias(
                raw_cases,
                name="Raw Bias",
                mtf_error_limit_pct=SCIENTIFIC_RAW_BIAS_LIMIT_PCT,
                curve_rmse_limit=SCIENTIFIC_RAW_CURVE_RMSE_LIMIT,
            )
        )
        checks.append(evaluate_scientific_ranking(dense_cases, raw_groups))
        checks.append(evaluate_scientific_invariance(dense_cases, raw_groups))
        checks.append(evaluate_scientific_raw_parity(raw_groups))
        checks.append(evaluate_scientific_raw_vs_dense(raw_groups))
    else:
        checks.append(
            CheckResult(
                name="Ranking",
                passed=True,
                summary="Raw ranking check skipped because --mode dense was selected.",
                metrics={"active_mode": args.mode},
            )
        )
        checks.append(
            CheckResult(
                name="Invariance",
                passed=True,
                summary="Raw invariance check skipped because --mode dense was selected.",
                metrics={"active_mode": args.mode},
            )
        )

    if not args.no_png:
        save_heatmap(
            dense_bias_matrix,
            angles_deg=SCIENTIFIC_ANGLES_DEG,
            blur_sigmas_px=SCIENTIFIC_BLUR_SIGMAS_PX,
            path=output_dir / "dense_bias_heatmap.png",
            title="Dense Bias Heatmap (MTF50 error %)",
            cbar_label="Relative error (%)",
        )
        if include_raw:
            save_heatmap(
                raw_bias_matrix,
                angles_deg=SCIENTIFIC_ANGLES_DEG,
                blur_sigmas_px=SCIENTIFIC_BLUR_SIGMAS_PX,
                path=output_dir / "raw_bias_heatmap.png",
                title="Raw Bias Heatmap (mean MTF50 error %)",
                cbar_label="Relative error (%)",
            )
            save_raw_parity_plot(
                raw_roi_spread_matrix,
                raw_pair_delta_matrix,
                angles_deg=SCIENTIFIC_ANGLES_DEG,
                blur_sigmas_px=SCIENTIFIC_BLUR_SIGMAS_PX,
                path=output_dir / "raw_parity_invariance.png",
            )
            save_blur_ranking_plot(dense_cases, raw_groups, output_dir / "blur_ranking.png")
        save_summary_png(checks, output_dir / "scientific_summary.png")

    overall_pass = all(check.passed for check in checks)
    report: dict[str, Any] = {
        "profile": "scientific",
        "mode": args.mode,
        "parameters": {
            "pixel_size_um": float(args.pixel_size_um),
            "image_size": int(args.image_size),
            "roi_size": int(args.roi_size),
            "angles_deg": list(SCIENTIFIC_ANGLES_DEG),
            "blur_sigmas_px": list(SCIENTIFIC_BLUR_SIGMAS_PX),
            "raw_roi_offsets": [list(offset) for offset in SCIENTIFIC_RAW_ROI_OFFSETS],
            "scene_oversample": SCIENTIFIC_SCENE_OVERSAMPLE,
        },
        "reference_model": "gaussian_psf_times_square_pixel_aperture",
        "checks": checks,
        "dense_cases": dense_cases,
        "raw_cases": raw_cases,
        "raw_groups": raw_groups,
        "dense_bias_heatmap_pct": dense_bias_matrix,
        "raw_bias_heatmap_pct": raw_bias_matrix,
        "raw_roi_spread_heatmap_pct": raw_roi_spread_matrix,
        "raw_pair_delta_heatmap_pct": raw_pair_delta_matrix,
        "overall_pass": overall_pass,
    }
    return checks, report


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate dense and raw MTF paths with synthetic slanted edges.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--profile", choices=("quick", "scientific"), default="quick")
    parser.add_argument("--mode", choices=("dense", "raw", "both"), default="both")
    parser.add_argument("--output-dir", default="mtf_validation_out")
    parser.add_argument("--report-json", default=None)
    parser.add_argument("--pixel-size-um", type=float, default=2.4)
    parser.add_argument("--angle-deg", type=float, default=5.0)
    parser.add_argument("--blur-sigma", type=float, default=1.0)
    parser.add_argument("--image-size", type=int, default=240)
    parser.add_argument("--roi-size", type=int, default=200)
    parser.add_argument("--no-png", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Validate CLI argument ranges."""
    if args.pixel_size_um <= 0:
        raise ValueError("--pixel-size-um must be positive")
    if args.blur_sigma <= 0:
        raise ValueError("--blur-sigma must be positive")
    if args.image_size < 64:
        raise ValueError("--image-size must be >= 64")
    if args.roi_size < 32:
        raise ValueError("--roi-size must be >= 32")
    if args.roi_size > args.image_size:
        raise ValueError("--roi-size must not exceed --image-size")
    if args.profile == "scientific" and args.mode in {"raw", "both"} and (args.image_size - args.roi_size) < 2:
        raise ValueError(
            "--profile scientific with raw mode needs at least a 1-pixel image margin around the ROI"
        )


def main() -> int:
    """Delegate to the shared-core validator wrapper."""
    from mtf_validation_repo import main as shared_main

    return shared_main()


if __name__ == "__main__":
    raise SystemExit(main())
