"""Modular local focus-peak models with covariance-based peak uncertainty."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np


SUPPORTED_PEAK_MODELS = ("quadratic", "gaussian")


@dataclass
class PeakFitResult:
    """Result of fitting one local focus maximum."""

    method: str
    valid: bool
    reject_reason: str
    z_peak_mm: float = math.nan
    uncertainty_mm: float = math.nan
    peak_value: float = math.nan
    width_mm: float = math.nan
    prominence: float = math.nan
    curvature: float = math.nan
    fit_r2: float = math.nan
    fit_rmse: float = math.nan
    local_z_mm: np.ndarray = field(default_factory=lambda: np.empty(0))
    local_measured: np.ndarray = field(default_factory=lambda: np.empty(0))
    local_predicted: np.ndarray = field(default_factory=lambda: np.empty(0))


def fit_focus_peak(
    z_mm: np.ndarray,
    focus_values: np.ndarray,
    *,
    method: str = "quadratic",
    half_window: int = 2,
) -> PeakFitResult:
    """Fit a configured peak model around the discrete focus maximum.

    Peak uncertainty is obtained from the ordinary least-squares covariance of
    the local model and propagated to the vertex with the delta method. It is
    not inferred from R². At least four local points are needed for a finite
    covariance estimate; with exactly three points the peak remains usable but
    its uncertainty is NaN.
    """
    method = str(method).strip().lower()
    if method not in SUPPORTED_PEAK_MODELS:
        raise ValueError(
            f"unsupported peak fit method '{method}'; "
            f"choose one of {SUPPORTED_PEAK_MODELS}"
        )
    z = np.asarray(z_mm, dtype=np.float64)
    values = np.asarray(focus_values, dtype=np.float64)
    if z.ndim != 1 or values.shape != z.shape or z.size < 3:
        return PeakFitResult(method, False, "invalid_peak_fit")
    peak_index = int(np.argmax(values))
    if peak_index in {0, z.size - 1}:
        return PeakFitResult(method, False, "peak_at_scan_boundary")

    half = max(1, int(half_window))
    lo = max(0, peak_index - half)
    hi = min(z.size, peak_index + half + 1)
    if hi - lo < 3:
        return PeakFitResult(method, False, "invalid_peak_fit")

    baseline = float(np.percentile(values, 20.0))
    measured_peak = float(values[peak_index])
    prominence = (measured_peak - baseline) / max(abs(measured_peak), 1.0e-12)
    local_z = z[lo:hi]
    local_values = values[lo:hi]
    center = float(z[peak_index])
    scale = float(np.median(np.diff(z)))
    if not np.isfinite(scale) or scale <= 0.0:
        return PeakFitResult(method, False, "invalid_peak_fit")
    local_t = (local_z - center) / scale

    if method == "quadratic":
        result = _fit_quadratic(local_t, local_values, baseline, center, scale)
    else:
        result = _fit_gaussian(local_t, local_values, baseline, center, scale)
    result.prominence = prominence
    result.local_z_mm = local_z.copy()
    result.local_measured = local_values.copy()
    if result.valid and not (z[0] < result.z_peak_mm < z[-1]):
        result.valid = False
        result.reject_reason = "peak_at_scan_boundary"
    return result


def _fit_quadratic(
    t: np.ndarray,
    values: np.ndarray,
    baseline: float,
    center_mm: float,
    scale_mm: float,
) -> PeakFitResult:
    design = np.column_stack((t * t, t, np.ones(t.size)))
    try:
        coefficients, covariance = _least_squares_with_covariance(design, values)
    except np.linalg.LinAlgError:
        return PeakFitResult("quadratic", False, "invalid_peak_fit")
    a, b, _ = coefficients
    predicted = design @ coefficients
    r2, rmse = _fit_quality(values, predicted)
    if not np.isfinite(a) or a >= 0.0:
        return PeakFitResult(
            "quadratic",
            False,
            "invalid_peak_fit",
            fit_r2=r2,
            fit_rmse=rmse,
            local_predicted=predicted,
        )
    vertex_t = float(-b / (2.0 * a))
    peak_value = float(np.polyval(coefficients, vertex_t))
    curvature = float(-2.0 * a / max(abs(peak_value), 1.0e-12))
    half_height = max(0.0, peak_value - baseline) / 2.0
    width_t = 2.0 * math.sqrt(half_height / max(-a, 1.0e-18))
    uncertainty_t = _vertex_uncertainty(a, b, covariance)
    return PeakFitResult(
        method="quadratic",
        valid=np.isfinite(vertex_t),
        reject_reason="" if np.isfinite(vertex_t) else "invalid_peak_fit",
        z_peak_mm=center_mm + vertex_t * scale_mm,
        uncertainty_mm=uncertainty_t * scale_mm,
        peak_value=peak_value,
        width_mm=width_t * scale_mm,
        curvature=curvature,
        fit_r2=r2,
        fit_rmse=rmse,
        local_predicted=predicted,
    )


def _fit_gaussian(
    t: np.ndarray,
    values: np.ndarray,
    baseline: float,
    center_mm: float,
    scale_mm: float,
) -> PeakFitResult:
    # A fixed baseline makes the log-Gaussian fit linear and reproducible. The
    # baseline is reported implicitly by the exported measured/predicted curve.
    positive = values - baseline
    epsilon = max(float(np.max(positive)) * 1.0e-9, 1.0e-18)
    mask = positive > epsilon
    if int(np.sum(mask)) < 3:
        return PeakFitResult("gaussian", False, "invalid_peak_fit")
    design = np.column_stack((t[mask] ** 2, t[mask], np.ones(int(np.sum(mask)))))
    log_values = np.log(positive[mask])
    try:
        coefficients, covariance = _least_squares_with_covariance(design, log_values)
    except np.linalg.LinAlgError:
        return PeakFitResult("gaussian", False, "invalid_peak_fit")
    a, b, c = coefficients
    if not np.isfinite(a) or a >= 0.0:
        return PeakFitResult("gaussian", False, "invalid_peak_fit")
    vertex_t = float(-b / (2.0 * a))
    exponent = np.clip(a * t * t + b * t + c, -700.0, 700.0)
    predicted = baseline + np.exp(exponent)
    peak_exponent = float(np.clip(c - b * b / (4.0 * a), -700.0, 700.0))
    peak_value = float(baseline + math.exp(peak_exponent))
    sigma_t = math.sqrt(-1.0 / (2.0 * a))
    width_t = 2.0 * math.sqrt(2.0 * math.log(2.0)) * sigma_t
    uncertainty_t = _vertex_uncertainty(a, b, covariance)
    r2, rmse = _fit_quality(values, predicted)
    curvature = float(1.0 / max(sigma_t * sigma_t, 1.0e-18))
    return PeakFitResult(
        method="gaussian",
        valid=np.isfinite(vertex_t),
        reject_reason="" if np.isfinite(vertex_t) else "invalid_peak_fit",
        z_peak_mm=center_mm + vertex_t * scale_mm,
        uncertainty_mm=uncertainty_t * scale_mm,
        peak_value=peak_value,
        width_mm=width_t * scale_mm,
        curvature=curvature,
        fit_r2=r2,
        fit_rmse=rmse,
        local_predicted=predicted,
    )


def _least_squares_with_covariance(
    design: np.ndarray,
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    coefficients = np.linalg.lstsq(design, values, rcond=None)[0]
    normal = design.T @ design
    if np.linalg.matrix_rank(normal) < normal.shape[0]:
        raise np.linalg.LinAlgError("rank-deficient peak design")
    residuals = values - design @ coefficients
    dof = values.size - design.shape[1]
    if dof <= 0:
        covariance = np.full((design.shape[1], design.shape[1]), np.nan)
    else:
        variance = float(np.sum(residuals**2)) / dof
        covariance = np.linalg.inv(normal) * variance
    return coefficients, covariance


def _vertex_uncertainty(a: float, b: float, covariance: np.ndarray) -> float:
    if not np.all(np.isfinite(covariance[:2, :2])):
        return math.nan
    gradient = np.asarray([b / (2.0 * a * a), -1.0 / (2.0 * a), 0.0])
    variance = float(gradient @ covariance @ gradient)
    return math.sqrt(max(0.0, variance))


def _fit_quality(measured: np.ndarray, predicted: np.ndarray) -> tuple[float, float]:
    residuals = measured - predicted
    rmse = float(np.sqrt(np.mean(residuals**2)))
    total = float(np.sum((measured - np.mean(measured)) ** 2))
    r2 = 1.0 - float(np.sum(residuals**2)) / max(total, 1.0e-18)
    return r2, rmse
