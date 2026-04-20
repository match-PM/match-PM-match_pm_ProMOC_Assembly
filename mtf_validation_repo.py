from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent
CAMERA_NODES_ROOT = ROOT / "camera_nodes"
if str(CAMERA_NODES_ROOT) not in sys.path:
    sys.path.insert(0, str(CAMERA_NODES_ROOT))

from camera_nodes.algorithms.mtf import MTFAnalyzer, MTFConfig, MTFResult  # noqa: E402
from camera_nodes.algorithms.mtf.debug_export import write_curve_csv_artifacts  # noqa: E402
from camera_nodes.algorithms.mtf.processing import extract_rggb_green_samples  # noqa: E402
from camera_nodes.services.mtf_export import write_context_csv, write_summary_csv  # noqa: E402


QUICK_SCENE_OVERSAMPLE = 6
SCIENTIFIC_SCENE_OVERSAMPLE = 8
SCIENTIFIC_ANGLES_DEG = (3.0, 5.0, 7.0, 9.0)
SCIENTIFIC_BLUR_SIGMAS_PX = (0.7, 1.0, 1.5, 2.0, 3.0)
SCIENTIFIC_RAW_ROI_OFFSETS = ((0, 0), (1, 0), (0, 1), (1, 1))
RECOMMENDED_MIN_EDGE_ANGLE_DEG = 3.0
RECOMMENDED_MAX_EDGE_ANGLE_DEG = 10.0
BOUNDARY_TEST_ANGLES_DEG = (2.5, 3.0, 10.0, 10.5)
OFFICIAL_WINDOW_BASIS = "synthetic_nominal_angle_deg"


def check(name: str, passed: bool, summary: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "summary": summary, "metrics": metrics}


def pixel_pitch_mm(pixel_size_um: float) -> float:
    return float(pixel_size_um) / 1000.0


def nyquist_lpmm(pixel_size_um: float) -> float:
    return 1000.0 / (2.0 * float(pixel_size_um))


def rel_err_pct(measured: float, reference: float) -> float:
    if reference <= 0:
        return float("inf")
    return abs(float(measured) - float(reference)) / float(reference) * 100.0


def spread_pct(values: list[float]) -> float:
    values = [float(value) for value in values if np.isfinite(value)]
    if len(values) < 2:
        return float("inf")
    mean_value = float(np.mean(values))
    if mean_value <= 0:
        return float("inf")
    return (float(np.max(values)) - float(np.min(values))) / mean_value * 100.0


def official_angle_window() -> dict[str, Any]:
    """Return the documented validator-only operating window metadata."""
    return {
        "recommended_min_edge_angle_deg": RECOMMENDED_MIN_EDGE_ANGLE_DEG,
        "recommended_max_edge_angle_deg": RECOMMENDED_MAX_EDGE_ANGLE_DEG,
        "basis": OFFICIAL_WINDOW_BASIS,
    }


def is_official_angle_in_window(requested_angle_deg: float) -> bool:
    """Return whether a nominal synthetic edge angle lies inside the official SOP window."""
    abs_angle = abs(float(requested_angle_deg))
    return RECOMMENDED_MIN_EDGE_ANGLE_DEG <= abs_angle <= RECOMMENDED_MAX_EDGE_ANGLE_DEG


def official_angle_window_reason(
    requested_angle_deg: float,
    *,
    node_valid: bool,
    error_msg: str = "",
) -> str:
    """Explain why a validator case is or is not officially accepted."""
    abs_angle = abs(float(requested_angle_deg))
    if not is_official_angle_in_window(abs_angle):
        return (
            f"Requested synthetic angle {abs_angle:.2f}deg lies outside the official SOP "
            f"window [{RECOMMENDED_MIN_EDGE_ANGLE_DEG:.1f}, {RECOMMENDED_MAX_EDGE_ANGLE_DEG:.1f}]deg."
        )
    if not node_valid:
        return str(error_msg or "Node rejected a nominally in-window synthetic case.")
    return ""


def build_official_window_check(
    name: str,
    requested_angle_deg: float,
    result: MTFResult,
) -> dict[str, Any]:
    """Create one user-facing check for the official validator operating window."""
    node_valid = bool(result.valid)
    official_sop_accepted = node_valid and is_official_angle_in_window(requested_angle_deg)
    return check(
        name,
        official_sop_accepted,
        "Official validator acceptance follows the documented 3.0deg to 10.0deg working window.",
        requested_angle_deg=float(requested_angle_deg),
        measured_angle_deg=float(result.edge_angle),
        node_valid=node_valid,
        official_sop_accepted=official_sop_accepted,
        recommended_min_edge_angle_deg=RECOMMENDED_MIN_EDGE_ANGLE_DEG,
        recommended_max_edge_angle_deg=RECOMMENDED_MAX_EDGE_ANGLE_DEG,
        basis=OFFICIAL_WINDOW_BASIS,
        reason=official_angle_window_reason(
            requested_angle_deg,
            node_valid=node_valid,
            error_msg=result.error_msg,
        ) or "-",
    )


def build_official_window_note(requested_angle_deg: float, result: MTFResult) -> str:
    """Build one compact context note that distinguishes technical validity from SOP acceptance."""
    official_sop_accepted = bool(result.valid) and is_official_angle_in_window(requested_angle_deg)
    reason = official_angle_window_reason(
        requested_angle_deg,
        node_valid=bool(result.valid),
        error_msg=result.error_msg,
    )
    note = (
        f"official_window_deg={RECOMMENDED_MIN_EDGE_ANGLE_DEG:.1f}.."
        f"{RECOMMENDED_MAX_EDGE_ANGLE_DEG:.1f}; "
        f"official_basis={OFFICIAL_WINDOW_BASIS}; "
        f"selected_requested_angle_deg={float(requested_angle_deg):.3f}; "
        f"technical_selected_valid={int(bool(result.valid))}; "
        f"official_selected_acceptance={'accepted' if official_sop_accepted else 'rejected'}"
    )
    if reason:
        note += f"; official_reason={reason}"
    return note


def evaluate_boundary_case(
    *,
    requested_angle_deg: float,
    analyzer: MTFAnalyzer,
    image_size: int,
    roi_size: int,
    pixel_size_um: float,
    blur_sigma: float = 1.0,
) -> dict[str, Any]:
    """Evaluate one dense boundary case against both technical and official acceptance."""
    scene = generate_dense_edge(
        image_size,
        requested_angle_deg,
        blur_sigma,
        SCIENTIFIC_SCENE_OVERSAMPLE,
    )
    roi = centered_roi_bounds(image_size, roi_size)
    result = analyzer.compute_mtf(scene, roi=roi)
    expected_official_acceptance = is_official_angle_in_window(requested_angle_deg)
    official_sop_accepted = bool(result.valid) and expected_official_acceptance
    return {
        "requested_angle_deg": float(requested_angle_deg),
        "measured_angle_deg": float(result.edge_angle),
        "node_valid": bool(result.valid),
        "official_sop_accepted": official_sop_accepted,
        "expected_official_acceptance": expected_official_acceptance,
        "matches_expected_official_acceptance": official_sop_accepted == expected_official_acceptance,
        "reason": official_angle_window_reason(
            requested_angle_deg,
            node_valid=bool(result.valid),
            error_msg=result.error_msg,
        ),
        "error": str(result.error_msg or ""),
        "warning": str(result.warning_msg or ""),
        "nyquist_lpmm": nyquist_lpmm(pixel_size_um),
    }


def format_boundary_case_summary(boundary_cases: list[dict[str, Any]]) -> str:
    """Render compact boundary results for the CLI check output."""
    parts = []
    for item in boundary_cases:
        reason = f", reason={item['reason']}" if item["reason"] else ""
        parts.append(
            f"{item['requested_angle_deg']:.1f}deg: node_valid={item['node_valid']}, "
            f"official={item['official_sop_accepted']}, measured={item['measured_angle_deg']:.2f}{reason}"
        )
    return "; ".join(parts)


def centered_roi_bounds(image_size: int, roi_size: int, offset_x: int = 0, offset_y: int = 0) -> tuple[int, int, int, int]:
    margin = (image_size - roi_size) // 2
    x1 = margin + int(offset_x)
    y1 = margin + int(offset_y)
    return (x1, y1, x1 + roi_size, y1 + roi_size)


def threshold_crossing(freqs: np.ndarray, mtf: np.ndarray, threshold: float) -> float:
    if freqs.size == 0 or mtf.size == 0 or float(np.max(mtf)) < threshold:
        return 0.0
    for idx in range(1, mtf.size):
        prev_val = float(mtf[idx - 1])
        cur_val = float(mtf[idx])
        if prev_val >= threshold >= cur_val:
            prev_freq = float(freqs[idx - 1])
            cur_freq = float(freqs[idx])
            delta = prev_val - cur_val
            if abs(delta) < 1e-12:
                return cur_freq
            frac = (prev_val - threshold) / delta
            return prev_freq + frac * (cur_freq - prev_freq)
    return 0.0


def build_reference(pixel_size_um: float, blur_sigma_px: float) -> dict[str, Any]:
    freqs = np.linspace(0.0, nyquist_lpmm(pixel_size_um), 2048, dtype=np.float64)
    pitch = pixel_pitch_mm(pixel_size_um)
    sigma_mm = float(blur_sigma_px) * pitch
    gaussian = np.exp(-2.0 * (math.pi ** 2) * (sigma_mm ** 2) * (freqs ** 2))
    aperture = np.sinc(freqs * pitch)
    mtf = np.clip(gaussian * np.abs(aperture), 0.0, 1.0)
    return {
        "freqs": freqs,
        "mtf": mtf,
        "mtf50": threshold_crossing(freqs, mtf, 0.5),
        "mtf20": threshold_crossing(freqs, mtf, 0.2),
        "mtf10": threshold_crossing(freqs, mtf, 0.1),
    }


def curve_rmse(result: MTFResult, reference: dict[str, Any]) -> float:
    if result.frequencies.size == 0 or result.mtf_values.size == 0:
        return float("inf")
    ref_interp = np.interp(result.frequencies, reference["freqs"], reference["mtf"])
    return float(np.sqrt(np.mean((result.mtf_values - ref_interp) ** 2)))


def generate_dense_edge(size: int, angle_deg: float, blur_sigma: float, oversample_factor: int) -> np.ndarray:
    hi_size = int(size) * int(oversample_factor)
    center = hi_size / 2.0
    ys, xs = np.mgrid[0:hi_size, 0:hi_size]
    x_centered = xs - center
    y_centered = ys - center
    angle_rad = math.radians(angle_deg)
    signed_distance = x_centered * math.cos(angle_rad) + y_centered * math.sin(angle_rad)
    edge = (signed_distance > 0).astype(np.float64)
    sigma_hi = float(blur_sigma) * float(oversample_factor)
    kernel = int(max(3, math.ceil(sigma_hi * 6.0) | 1))
    blurred = cv2.GaussianBlur(edge, (kernel, kernel), sigma_hi, borderType=cv2.BORDER_REPLICATE)
    pixel_integrated = blurred.reshape(size, oversample_factor, size, oversample_factor).mean(axis=(1, 3))
    return np.clip(pixel_integrated * 65280.0, 0.0, 65280.0).astype(np.uint16)


def green_infill_from_raw(raw_bayer: np.ndarray) -> np.ndarray:
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
                    if 0 <= src_row < height and 0 <= src_col < width and not np.isnan(green[src_row, src_col]):
                        samples.append(green[src_row, src_col])
            green[row, col] = float(np.mean(samples))
    return green.astype(raw_bayer.dtype)


def dense_config(pixel_size_um: float, roi_size: int) -> MTFConfig:
    return MTFConfig(pixel_size_um=pixel_size_um, input_mode="dense_gray", roi_width=roi_size, roi_height=roi_size)


def raw_config(pixel_size_um: float, roi_size: int) -> MTFConfig:
    return MTFConfig(
        pixel_size_um=pixel_size_um,
        input_mode="raw_bayer_rggb",
        raw_bayer_pattern="RGGB",
        roi_width=roi_size,
        roi_height=roi_size,
        capture_pixel_format="BayerRG12",
        capture_binning_h=1,
        capture_binning_v=1,
        source_encoding="bayer_rggb16",
    )


def parity_check() -> dict[str, Any]:
    sensor = np.zeros((6, 6), dtype=np.uint16)
    sensor[0::2, 0::2] = 11
    sensor[0::2, 1::2] = 101
    sensor[1::2, 0::2] = 202
    sensor[1::2, 1::2] = 22
    even_groups = extract_rggb_green_samples(sensor[0:4, 0:4], origin_x=0, origin_y=0)
    odd_groups = extract_rggb_green_samples(sensor[1:5, 1:5], origin_x=1, origin_y=1)
    even_g1_mean = float(np.mean(even_groups["g1"][2]))
    even_g2_mean = float(np.mean(even_groups["g2"][2]))
    odd_g1_mean = float(np.mean(odd_groups["g1"][2]))
    odd_g2_mean = float(np.mean(odd_groups["g2"][2]))
    return check(
        "ROI Parity",
        even_g1_mean == 101.0 and even_g2_mean == 202.0 and odd_g1_mean == 101.0 and odd_g2_mean == 202.0,
        "Absolute Bayer parity stays tied to the physical sensor pattern for even and odd ROI origins.",
        even_g1_mean=even_g1_mean,
        even_g2_mean=even_g2_mean,
        odd_g1_mean=odd_g1_mean,
        odd_g2_mean=odd_g2_mean,
    )


def ensure_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def save_scene_png(image: np.ndarray, path: Path, title: str) -> None:
    plt = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.imshow((image.astype(np.float64) / max(1.0, float(np.max(image))) * 255.0).astype(np.uint8), cmap="gray")
    ax.set_title(title)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_result_plot(result: MTFResult, path: Path, title: str) -> None:
    plt = ensure_matplotlib()
    fig, axes = plt.subplots(3, 1, figsize=(8, 10))
    if result.esf_raw.size > 0:
        axes[0].plot(result.esf_raw, alpha=0.5, label="ESF raw")
    axes[0].plot(result.esf, label="ESF used")
    axes[0].set_title(f"{title} - ESF")
    if result.esf_raw.size > 0:
        axes[0].legend(loc="best")
    axes[1].plot(result.lsf, label="LSF")
    if result.lsf_windowed.size > 0:
        axes[1].plot(result.lsf_windowed, label="LSF windowed")
    axes[1].set_title(f"{title} - LSF")
    if result.lsf_windowed.size > 0:
        axes[1].legend(loc="best")
    mtf_raw_curve = result.mtf_raw if result.mtf_raw.size > 0 else result.mtf_values
    axes[2].plot(result.frequencies, mtf_raw_curve, label="MTF raw")
    if result.mtf_values.size > 0 and not np.array_equal(result.mtf_values, mtf_raw_curve):
        axes[2].plot(result.frequencies, result.mtf_values, label="MTF used")
    if result.mtf_ideal.size > 0:
        axes[2].plot(result.frequencies, result.mtf_ideal, "--", label="Ideal")
    if result.frequencies_alt.size > 0 and result.mtf_raw_alt.size > 0:
        axes[2].plot(result.frequencies_alt, result.mtf_raw_alt, ":", label="MTF alt raw")
    axes[2].set_title(f"{title} - MTF")
    axes[2].legend(loc="best")
    for axis in axes:
        axis.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_summary_png(checks: list[dict[str, Any]], path: Path) -> None:
    plt = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(10, max(3, len(checks) * 0.8)))
    ax.set_axis_off()
    y = 0.95
    for item in checks:
        color = "#1b7f3b" if item["passed"] else "#b22222"
        ax.text(0.02, y, f"{item['name']}: {'PASS' if item['passed'] else 'FAIL'}", color=color, weight="bold")
        y -= 0.06
        ax.text(0.04, y, item["summary"])
        y -= 0.07
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_heatmap(matrix: np.ndarray, angles: tuple[float, ...], sigmas: tuple[float, ...], path: Path, title: str, cbar_label: str) -> None:
    plt = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    im = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(angles)), labels=[str(value) for value in angles])
    ax.set_yticks(range(len(sigmas)), labels=[str(value) for value in sigmas])
    ax.set_xlabel("Angle (deg)")
    ax.set_ylabel("Blur sigma (px)")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=cbar_label)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_raw_parity_plot(roi_spread: np.ndarray, pair_delta: np.ndarray, angles: tuple[float, ...], sigmas: tuple[float, ...], path: Path) -> None:
    plt = ensure_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for axis, matrix, title in (
        (axes[0], roi_spread, "ROI-origin spread (%)"),
        (axes[1], pair_delta, "G1/G2 delta (%)"),
    ):
        im = axis.imshow(matrix, aspect="auto", cmap="magma")
        axis.set_xticks(range(len(angles)), labels=[str(value) for value in angles])
        axis.set_yticks(range(len(sigmas)), labels=[str(value) for value in sigmas])
        axis.set_xlabel("Angle (deg)")
        axis.set_ylabel("Blur sigma (px)")
        axis.set_title(title)
        fig.colorbar(im, ax=axis)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_blur_ranking_plot(dense_cases: list[dict[str, Any]], raw_groups: list[dict[str, Any]], path: Path) -> None:
    plt = ensure_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for angle_deg in SCIENTIFIC_ANGLES_DEG:
        dense_series = [item["mtf50"] for item in dense_cases if item["valid"] and item["angle_deg"] == angle_deg]
        raw_series = [item["mean_raw_mtf50_lpmm"] for item in raw_groups if item["valid_case_count"] > 0 and item["angle_deg"] == angle_deg]
        axes[0].plot(SCIENTIFIC_BLUR_SIGMAS_PX[: len(dense_series)], dense_series, marker="o", label=f"{angle_deg} deg")
        axes[1].plot(SCIENTIFIC_BLUR_SIGMAS_PX[: len(raw_series)], raw_series, marker="o", label=f"{angle_deg} deg")
    axes[0].set_title("Dense blur ranking")
    axes[1].set_title("Raw blur ranking")
    for axis in axes:
        axis.set_xlabel("Blur sigma (px)")
        axis.set_ylabel("MTF50 (lp/mm)")
        axis.grid(True, alpha=0.3)
        axis.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_reference_curve_plot(reference: dict[str, Any], path: Path, title: str) -> None:
    plt = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(reference["freqs"], reference["mtf"], color="#444444", label="Analytical reference")
    ax.axhline(0.5, color="#1f77b4", linestyle="--", linewidth=1.0, label="MTF50")
    ax.axhline(0.2, color="#ff7f0e", linestyle="--", linewidth=1.0, label="MTF20")
    ax.axhline(0.1, color="#2ca02c", linestyle="--", linewidth=1.0, label="MTF10")
    ax.set_title(title)
    ax.set_xlabel("Frequency (lp/mm)")
    ax.set_ylabel("MTF")
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def format_check(item: dict[str, Any]) -> str:
    lines = [f"[{item['name']}]", f"status: {'PASS' if item['passed'] else 'FAIL'}", f"summary: {item['summary']}"]
    for key, value in item["metrics"].items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def summarize_result(result: MTFResult) -> dict[str, Any]:
    return {
        "valid": bool(result.valid),
        "mtf50_lpmm": float(result.mtf50),
        "mtf20_lpmm": float(result.mtf20),
        "mtf10_lpmm": float(result.mtf10),
        "edge_angle_deg": float(result.edge_angle),
        "edge_angle_method": result.edge_angle_method,
        "edge_angle_geometric": float(result.edge_angle_geometric),
        "edge_angle_phase": float(result.edge_angle_phase),
        "edge_angle_consistency_deg": float(result.edge_angle_consistency_deg),
        "edge_fit_residual_px": float(result.edge_fit_residual_px),
        "edge_support_points": int(result.edge_support_points),
        "analysis_roi_bounds": result.analysis_roi_bounds,
        "g1_mtf50_lpmm": float(result.g1_mtf50),
        "g2_mtf50_lpmm": float(result.g2_mtf50),
        "g1_g2_delta_pct": float(result.g1_g2_delta_pct),
        "warning": result.warning_msg,
        "error": result.error_msg,
    }


def roi_to_bbox(roi_bounds: tuple[int, int, int, int] | None) -> tuple[int, int, int, int]:
    """Convert x1/y1/x2/y2 bounds into x/y/w/h for CSV exports."""
    if not roi_bounds or len(roi_bounds) != 4:
        return 0, 0, 0, 0
    x1, y1, x2, y2 = [int(value) for value in roi_bounds]
    return x1, y1, max(0, x2 - x1), max(0, y2 - y1)


def build_validator_summary_row(
    *,
    run_id: str,
    label: str,
    result: MTFResult,
    roi_bounds: tuple[int, int, int, int] | None,
    selected_for_response: bool,
) -> dict[str, object]:
    """Build one summary row that matches the ROS-side CSV schema."""
    roi_x, roi_y, roi_w, roi_h = roi_to_bbox(roi_bounds)
    analysis_x, analysis_y, analysis_w, analysis_h = roi_to_bbox(result.analysis_roi_bounds)
    return {
        "run_id": run_id,
        "selected_for_response": int(bool(selected_for_response)),
        "edge_label": label,
        "edge_name": label,
        "edge_direction": str(result.edge_direction or ""),
        "valid": int(bool(result.valid)),
        "sample_count": 1 if result.valid else 0,
        "contrast": float(result.contrast),
        "roi_bbox_x": roi_x,
        "roi_bbox_y": roi_y,
        "roi_bbox_w": roi_w,
        "roi_bbox_h": roi_h,
        "analysis_roi_x": analysis_x,
        "analysis_roi_y": analysis_y,
        "analysis_roi_w": analysis_w,
        "analysis_roi_h": analysis_h,
        "mtf50_lpmm": float(result.mtf50),
        "mtf20_lpmm": float(result.mtf20),
        "mtf10_lpmm": float(result.mtf10),
        "nyquist_lpmm": float(result.nyquist_frequency),
        "edge_angle_deg": float(result.edge_angle),
        "edge_angle_method": str(result.edge_angle_method or ""),
        "edge_angle_geometric_deg": float(result.edge_angle_geometric),
        "edge_angle_phase_deg": float(result.edge_angle_phase),
        "edge_angle_consistency_deg": float(result.edge_angle_consistency_deg),
        "edge_fit_residual_px": float(result.edge_fit_residual_px),
        "edge_support_points": int(result.edge_support_points),
        "g1_mtf50_lpmm": float(result.g1_mtf50),
        "g2_mtf50_lpmm": float(result.g2_mtf50),
        "g1_g2_delta_pct": float(result.g1_g2_delta_pct),
        "capture_mode": str(result.capture_mode or ""),
        "capture_pixel_format": str(result.capture_pixel_format or ""),
        "capture_binning_h": int(result.capture_binning_h),
        "capture_binning_v": int(result.capture_binning_v),
        "capture_exposure_us": float(result.capture_exposure_us),
        "capture_gain": float(result.capture_gain),
        "illumination_wavelength_um": float(result.illumination_wavelength_um),
        "warning_msg": str(result.warning_msg or ""),
        "error_msg": str(result.error_msg or ""),
    }


def build_validator_context_row(
    *,
    run_id: str,
    profile: str,
    pixel_size_um: float,
    selected_label: str,
    selected_result: MTFResult | None,
    row_count: int,
    results: dict[str, MTFResult],
    notes: str,
) -> dict[str, object]:
    """Build one validator context row using the same schema as ROS exports."""
    warnings = "; ".join(
        str(result.warning_msg)
        for result in results.values()
        if str(result.warning_msg or "").strip()
    )
    errors = "; ".join(
        str(result.error_msg)
        for result in results.values()
        if not result.valid and str(result.error_msg or "").strip()
    )
    valid_edge_count = sum(int(result.valid) for result in results.values())
    selected = selected_result or MTFResult()
    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "measurement_success": int(bool(selected_result and selected_result.valid)),
        "measurement_error": errors,
        "measurement_warning": warnings,
        "operator": "synthetic_validator",
        "roi_mode": "synthetic_centered",
        "requested_target_edge": "synthetic_slanted_edge",
        "selected_edge_label": selected_label,
        "edge_count": int(row_count),
        "valid_edge_count": int(valid_edge_count),
        "selected_sample_count": 1 if selected_result and selected_result.valid else 0,
        "camera_objective": "synthetic_reference",
        "objective_magnification_x": 0.0,
        "use_beamsplitter": 0,
        "coaxial_light_voltage": 0.0,
        "coaxial_light_current": 0.0,
        "effective_pixel_size_um": float(pixel_size_um),
        "pixel_size_source": "cli_argument",
        "focus_position_mm": "",
        "capture_readback_ok": 1,
        "capture_readback_mismatches": "",
        "capture_available_keys": "synthetic_scene;analytic_reference",
        "capture_pixel_format": str(selected.capture_pixel_format or ""),
        "capture_binning_h": int(selected.capture_binning_h),
        "capture_binning_v": int(selected.capture_binning_v),
        "capture_exposure_us": float(selected.capture_exposure_us),
        "capture_gain": float(selected.capture_gain),
        "source_encoding": str(selected.source_encoding or ""),
        "selected_capture_mode": str(selected.capture_mode or ""),
        "selected_edge_angle_method": str(selected.edge_angle_method or ""),
        "notes": f"profile={profile}; {notes}",
    }


def write_validator_curve_exports(
    *,
    output_dir: Path,
    label: str,
    result: MTFResult,
) -> None:
    """Write the canonical ESF/LSF/MTF CSV files for one validator result."""
    write_curve_csv_artifacts(
        out_dir=output_dir,
        debug_label=label,
        esf=result.esf,
        lsf=result.lsf,
        lsf_windowed=result.lsf_windowed,
        frequencies=result.frequencies,
        mtf_raw=result.mtf_raw if result.mtf_raw.size > 0 else result.mtf_values,
        mtf_used=result.mtf_values,
        mtf_ideal=result.mtf_ideal,
        esf_raw=result.esf_raw if result.esf_raw.size > 0 else None,
        mtf_raw_alt=result.mtf_raw_alt if result.mtf_raw_alt.size > 0 else None,
        mtf_used_alt=result.mtf_used_alt if result.mtf_used_alt.size > 0 else None,
        frequencies_alt=result.frequencies_alt if result.frequencies_alt.size > 0 else None,
    )


def write_validator_run_exports(
    *,
    output_dir: Path,
    profile: str,
    run_id: str,
    pixel_size_um: float,
    roi_bounds: tuple[int, int, int, int] | None,
    results: dict[str, MTFResult],
    selected_label: str,
    notes: str,
) -> None:
    """Write validator run artifacts in the same top-level structure as ROS runs."""
    summary_rows = []
    for label, result in results.items():
        write_validator_curve_exports(output_dir=output_dir, label=label, result=result)
        summary_rows.append(
            build_validator_summary_row(
                run_id=run_id,
                label=label,
                result=result,
                roi_bounds=roi_bounds,
                selected_for_response=(label == selected_label),
            )
        )
    write_summary_csv(output_dir, summary_rows)
    write_context_csv(
        output_dir,
        build_validator_context_row(
            run_id=run_id,
            profile=profile,
            pixel_size_um=pixel_size_um,
            selected_label=selected_label,
            selected_result=results.get(selected_label),
            row_count=len(summary_rows),
            results=results,
            notes=notes,
        ),
    )


def write_image_u16_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(str(path), image.astype(np.uint16))
    if not success:
        raise RuntimeError(f"Failed to write image: {path}")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def quick(args: argparse.Namespace, output_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dense_scene = generate_dense_edge(args.image_size, args.angle_deg, args.blur_sigma, QUICK_SCENE_OVERSAMPLE)
    raw_bayer = dense_scene.copy()
    roi = centered_roi_bounds(args.image_size, args.roi_size)
    dense_analyzer = MTFAnalyzer(dense_config(args.pixel_size_um, args.roi_size))
    raw_analyzer = MTFAnalyzer(raw_config(args.pixel_size_um, args.roi_size))
    dense_result = dense_analyzer.compute_mtf(dense_scene, roi=roi)
    raw_result = raw_analyzer.compute_mtf(raw_bayer, roi=roi)
    infill_result = dense_analyzer.compute_mtf(green_infill_from_raw(raw_bayer), roi=roi)
    selected_result = raw_result if raw_result.valid else dense_result
    checks = [
        check("Dense Scene", dense_result.valid and dense_result.mtf50 > 0 and dense_result.analysis_roi_bounds is not None, "Dense slanted-edge path returned valid ESF/LSF/MTF data.", valid=dense_result.valid, mtf50_lpmm=float(dense_result.mtf50), edge_angle_deg=float(dense_result.edge_angle), edge_angle_method=dense_result.edge_angle_method, nyquist_lpmm=nyquist_lpmm(args.pixel_size_um), analysis_roi_bounds=dense_result.analysis_roi_bounds, warning=dense_result.warning_msg or "-"),
        check("Raw Scene", raw_result.valid and raw_result.g1_mtf50 > 0 and raw_result.g2_mtf50 > 0 and raw_result.g1_g2_delta_pct <= 5.0 and raw_result.analysis_roi_bounds is not None, "Raw green path returned valid G1/G2 MTF metrics.", valid=raw_result.valid, mtf50_lpmm=float(raw_result.mtf50), g1_mtf50_lpmm=float(raw_result.g1_mtf50), g2_mtf50_lpmm=float(raw_result.g2_mtf50), g1_g2_delta_pct=float(raw_result.g1_g2_delta_pct), edge_angle_deg=float(raw_result.edge_angle), edge_angle_method=raw_result.edge_angle_method, analysis_roi_bounds=raw_result.analysis_roi_bounds, warning=raw_result.warning_msg or "-"),
    ]
    raw_error = abs(float(raw_result.mtf50) - float(dense_result.mtf50))
    infill_error = abs(float(infill_result.mtf50) - float(dense_result.mtf50))
    checks.append(check("Raw vs Dense", dense_result.valid and raw_result.valid and infill_result.valid and raw_error <= max(1.0, float(dense_result.mtf50) * 0.05) and raw_error < infill_error, "Raw Bayer green sampling should stay close to the dense reference and outperform simple green infill.", dense_mtf50_lpmm=float(dense_result.mtf50), raw_mtf50_lpmm=float(raw_result.mtf50), infill_mtf50_lpmm=float(infill_result.mtf50), raw_error_lpmm=raw_error, infill_error_lpmm=infill_error, allowed_error_lpmm=max(1.0, float(dense_result.mtf50) * 0.05)))
    checks.append(parity_check())
    checks.append(
        build_official_window_check(
            "Official Angle Window",
            args.angle_deg,
            selected_result,
        )
    )
    selected_label = "raw" if raw_result.valid else "dense"
    write_validator_run_exports(
        output_dir=output_dir,
        profile="quick",
        run_id="quick_validation",
        pixel_size_um=args.pixel_size_um,
        roi_bounds=roi,
        results={
            "dense": dense_result,
            "raw": raw_result,
            "infill": infill_result,
        },
        selected_label=selected_label,
        notes=(
            f"angle_deg={args.angle_deg:.3f}; blur_sigma_px={args.blur_sigma:.3f}; "
            f"image_size_px={args.image_size}; roi_size_px={args.roi_size}; "
            f"{build_official_window_note(args.angle_deg, selected_result)}"
        ),
    )
    if not args.no_png:
        save_scene_png(dense_scene, output_dir / "dense_scene.png", "Synthetic Dense Edge")
        save_scene_png(raw_bayer, output_dir / "raw_scene.png", "Synthetic Raw/Bayer Edge")
        save_result_plot(dense_result, output_dir / "dense_result.png", "Dense Result")
        save_result_plot(raw_result, output_dir / "raw_result.png", "Raw Result")
        save_summary_png(checks, output_dir / "quick_summary.png")
    report = {
        "profile": "quick",
        "checks": checks,
        "official_angle_window_deg": official_angle_window(),
        "dense_result": summarize_result(dense_result),
        "raw_result": summarize_result(raw_result),
        "infill_result": summarize_result(infill_result),
    }
    return checks, report


def reference_target(args: argparse.Namespace, output_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dense_scene = generate_dense_edge(args.image_size, args.angle_deg, args.blur_sigma, SCIENTIFIC_SCENE_OVERSAMPLE)
    raw_bayer = dense_scene.copy()
    roi = centered_roi_bounds(args.image_size, args.roi_size)
    reference = build_reference(args.pixel_size_um, args.blur_sigma)

    dense_analyzer = MTFAnalyzer(dense_config(args.pixel_size_um, args.roi_size))
    raw_analyzer = MTFAnalyzer(raw_config(args.pixel_size_um, args.roi_size))
    dense_result = dense_analyzer.compute_mtf(dense_scene, roi=roi)
    raw_result = raw_analyzer.compute_mtf(raw_bayer, roi=roi)
    selected_result = raw_result if raw_result.valid else dense_result

    dense_mtf50_error = rel_err_pct(dense_result.mtf50, reference["mtf50"])
    dense_mtf20_error = rel_err_pct(dense_result.mtf20, reference["mtf20"])
    raw_mtf50_error = rel_err_pct(raw_result.mtf50, reference["mtf50"])
    raw_mtf20_error = rel_err_pct(raw_result.mtf20, reference["mtf20"])

    target_basename = (
        f"reference_target_angle_{args.angle_deg:.1f}_deg_sigma_{args.blur_sigma:.2f}_px"
        .replace(".", "p")
    )
    dense_u16_path = output_dir / f"{target_basename}_dense_u16.png"
    raw_u16_path = output_dir / f"{target_basename}_raw_rggb_u16.png"
    metadata_path = output_dir / f"{target_basename}_reference.json"

    target_metadata = {
        "target_name": target_basename,
        "generator": "oversampled_slanted_edge_with_gaussian_psf_and_pixel_integration",
        "pixel_size_um": float(args.pixel_size_um),
        "image_size_px": int(args.image_size),
        "roi_size_px": int(args.roi_size),
        "edge_angle_deg": float(args.angle_deg),
        "blur_sigma_px": float(args.blur_sigma),
        "roi_bounds": list(roi),
        "reference_mtf": {
            "mtf50_lpmm": float(reference["mtf50"]),
            "mtf20_lpmm": float(reference["mtf20"]),
            "mtf10_lpmm": float(reference["mtf10"]),
        },
        "dense_result": summarize_result(dense_result),
        "raw_result": summarize_result(raw_result),
    }

    write_image_u16_png(dense_u16_path, dense_scene)
    write_image_u16_png(raw_u16_path, raw_bayer)
    metadata_path.write_text(json.dumps(to_jsonable(target_metadata), indent=2), encoding="utf-8")

    checks = [
        check(
            "Reference Target",
            True,
            "A synthetic slanted-edge target with analytically known MTF was generated and exported.",
            dense_target_u16_png=str(dense_u16_path.resolve()),
            raw_target_u16_png=str(raw_u16_path.resolve()),
            reference_json=str(metadata_path.resolve()),
            reference_mtf50_lpmm=float(reference["mtf50"]),
            reference_mtf20_lpmm=float(reference["mtf20"]),
            reference_mtf10_lpmm=float(reference["mtf10"]),
        ),
        check(
            "Dense vs Reference",
            dense_result.valid and dense_mtf50_error <= 5.0 and dense_mtf20_error <= 5.0,
            "The dense algorithm result should stay close to the analytical reference for the exported target.",
            valid=bool(dense_result.valid),
            measured_mtf50_lpmm=float(dense_result.mtf50),
            measured_mtf20_lpmm=float(dense_result.mtf20),
            reference_mtf50_lpmm=float(reference["mtf50"]),
            reference_mtf20_lpmm=float(reference["mtf20"]),
            mtf50_error_pct=float(dense_mtf50_error),
            mtf20_error_pct=float(dense_mtf20_error),
            edge_angle_deg=float(dense_result.edge_angle),
            edge_angle_method=dense_result.edge_angle_method,
            analysis_roi_bounds=dense_result.analysis_roi_bounds,
        ),
        check(
            "Raw vs Reference",
            raw_result.valid and raw_mtf50_error <= 5.0 and raw_mtf20_error <= 5.0,
            "The raw-green algorithm result should stay close to the same analytical reference for the exported target.",
            valid=bool(raw_result.valid),
            measured_mtf50_lpmm=float(raw_result.mtf50),
            measured_mtf20_lpmm=float(raw_result.mtf20),
            reference_mtf50_lpmm=float(reference["mtf50"]),
            reference_mtf20_lpmm=float(reference["mtf20"]),
            mtf50_error_pct=float(raw_mtf50_error),
            mtf20_error_pct=float(raw_mtf20_error),
            g1_mtf50_lpmm=float(raw_result.g1_mtf50),
            g2_mtf50_lpmm=float(raw_result.g2_mtf50),
            g1_g2_delta_pct=float(raw_result.g1_g2_delta_pct),
            edge_angle_deg=float(raw_result.edge_angle),
            edge_angle_method=raw_result.edge_angle_method,
            analysis_roi_bounds=raw_result.analysis_roi_bounds,
        ),
        build_official_window_check(
            "Official Angle Window",
            args.angle_deg,
            selected_result,
        ),
    ]

    selected_label = "raw" if raw_result.valid else "dense"
    write_validator_run_exports(
        output_dir=output_dir,
        profile="reference-target",
        run_id=target_basename,
        pixel_size_um=args.pixel_size_um,
        roi_bounds=roi,
        results={
            "dense": dense_result,
            "raw": raw_result,
        },
        selected_label=selected_label,
        notes=(
            f"angle_deg={args.angle_deg:.3f}; blur_sigma_px={args.blur_sigma:.3f}; "
            f"image_size_px={args.image_size}; roi_size_px={args.roi_size}; "
            "reference=gaussian_psf_times_pixel_aperture; "
            f"{build_official_window_note(args.angle_deg, selected_result)}"
        ),
    )

    if not args.no_png:
        save_scene_png(dense_scene, output_dir / f"{target_basename}_preview.png", "Reference Target Preview")
        save_reference_curve_plot(reference, output_dir / f"{target_basename}_reference_curve.png", "Analytical Reference Curve")
        save_result_plot(dense_result, output_dir / f"{target_basename}_dense_result.png", "Dense Measurement")
        save_result_plot(raw_result, output_dir / f"{target_basename}_raw_result.png", "Raw Measurement")
        save_summary_png(checks, output_dir / f"{target_basename}_summary.png")

    report = {
        "profile": "reference-target",
        "checks": checks,
        "official_angle_window_deg": official_angle_window(),
        "target_name": target_basename,
        "reference": {
            "mtf50_lpmm": float(reference["mtf50"]),
            "mtf20_lpmm": float(reference["mtf20"]),
            "mtf10_lpmm": float(reference["mtf10"]),
            "frequencies_lpmm": reference["freqs"],
            "mtf_values": reference["mtf"],
        },
        "dense_target_u16_png": dense_u16_path,
        "raw_target_u16_png": raw_u16_path,
        "reference_json": metadata_path,
        "dense_result": summarize_result(dense_result),
        "raw_result": summarize_result(raw_result),
    }
    return checks, report


def scientific(args: argparse.Namespace, output_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dense_analyzer = MTFAnalyzer(dense_config(args.pixel_size_um, args.roi_size))
    raw_analyzer = MTFAnalyzer(raw_config(args.pixel_size_um, args.roi_size))
    checks = []
    boundary_cases = [
        evaluate_boundary_case(
            requested_angle_deg=angle_deg,
            analyzer=dense_analyzer,
            image_size=args.image_size,
            roi_size=args.roi_size,
            pixel_size_um=args.pixel_size_um,
        )
        for angle_deg in BOUNDARY_TEST_ANGLES_DEG
    ]
    ref = build_reference(args.pixel_size_um, 1.0)
    checks.append(check("Reference Self-Test", np.all(np.diff(ref["mtf"]) <= 1e-9) and ref["mtf50"] > 0 and ref["mtf50"] < ref["mtf20"] < ref["mtf10"], "Analytical Gaussian-PSF * pixel-aperture reference is monotonic and clipped to Nyquist.", reference_mtf50_lpmm=ref["mtf50"], reference_mtf20_lpmm=ref["mtf20"], reference_mtf10_lpmm=ref["mtf10"], monotonic=bool(np.all(np.diff(ref["mtf"]) <= 1e-9)), nyquist_clipped=True))
    checks.append(
        check(
            "Official Boundary Window",
            all(item["matches_expected_official_acceptance"] for item in boundary_cases),
            "Dense boundary cases separate technical node validity from official SOP acceptance for the 3.0deg to 10.0deg operating window.",
            recommended_min_edge_angle_deg=RECOMMENDED_MIN_EDGE_ANGLE_DEG,
            recommended_max_edge_angle_deg=RECOMMENDED_MAX_EDGE_ANGLE_DEG,
            basis=OFFICIAL_WINDOW_BASIS,
            case_results=format_boundary_case_summary(boundary_cases),
        )
    )
    dense_cases = []
    raw_cases = []
    raw_groups = []
    dense_bias_matrix = np.full((len(SCIENTIFIC_BLUR_SIGMAS_PX), len(SCIENTIFIC_ANGLES_DEG)), np.nan)
    raw_bias_matrix = np.full_like(dense_bias_matrix, np.nan)
    raw_roi_spread_matrix = np.full_like(dense_bias_matrix, np.nan)
    raw_pair_delta_matrix = np.full_like(dense_bias_matrix, np.nan)
    for blur_sigma in SCIENTIFIC_BLUR_SIGMAS_PX:
        sigma_idx = SCIENTIFIC_BLUR_SIGMAS_PX.index(blur_sigma)
        for angle_deg in SCIENTIFIC_ANGLES_DEG:
            angle_idx = SCIENTIFIC_ANGLES_DEG.index(angle_deg)
            reference = build_reference(args.pixel_size_um, blur_sigma)
            dense_scene = generate_dense_edge(args.image_size, angle_deg, blur_sigma, SCIENTIFIC_SCENE_OVERSAMPLE)
            raw_bayer = dense_scene.copy()
            dense_roi = centered_roi_bounds(args.image_size, args.roi_size)
            dense_result = dense_analyzer.compute_mtf(dense_scene, roi=dense_roi)
            dense_case = {"path": "dense", "angle_deg": angle_deg, "blur_sigma_px": blur_sigma, "valid": bool(dense_result.valid), "mtf50": float(dense_result.mtf50), "mtf20": float(dense_result.mtf20), "curve_rmse": curve_rmse(dense_result, reference), "mtf50_err_pct": rel_err_pct(dense_result.mtf50, reference["mtf50"]), "mtf20_err_pct": rel_err_pct(dense_result.mtf20, reference["mtf20"])}
            dense_cases.append(dense_case)
            dense_bias_matrix[sigma_idx, angle_idx] = dense_case["mtf50_err_pct"] if dense_case["valid"] else np.nan
            scene_raw = []
            if args.mode in {"raw", "both"}:
                for offset_x, offset_y in SCIENTIFIC_RAW_ROI_OFFSETS:
                    roi = centered_roi_bounds(args.image_size, args.roi_size, offset_x=offset_x, offset_y=offset_y)
                    raw_result = raw_analyzer.compute_mtf(raw_bayer, roi=roi)
                    raw_case = {"path": "raw", "angle_deg": angle_deg, "blur_sigma_px": blur_sigma, "valid": bool(raw_result.valid), "mtf50": float(raw_result.mtf50), "mtf20": float(raw_result.mtf20), "curve_rmse": curve_rmse(raw_result, reference), "mtf50_err_pct": rel_err_pct(raw_result.mtf50, reference["mtf50"]), "mtf20_err_pct": rel_err_pct(raw_result.mtf20, reference["mtf20"]), "g1_g2_delta_pct": float(raw_result.g1_g2_delta_pct), "raw_vs_dense_delta_pct": rel_err_pct(raw_result.mtf50, dense_result.mtf50) if raw_result.valid and dense_result.valid else float("inf")}
                    raw_cases.append(raw_case)
                    scene_raw.append(raw_case)
                valid_raw = [item for item in scene_raw if item["valid"]]
                group = {"angle_deg": angle_deg, "blur_sigma_px": blur_sigma, "valid_case_count": len(valid_raw), "roi_spread_pct": spread_pct([item["mtf50"] for item in valid_raw]), "max_g1_g2_delta_pct": max((item["g1_g2_delta_pct"] for item in valid_raw), default=float("inf")), "mean_raw_mtf50_lpmm": float(np.mean([item["mtf50"] for item in valid_raw])) if valid_raw else 0.0, "raw_vs_dense_delta_pct": rel_err_pct(float(np.mean([item["mtf50"] for item in valid_raw])) if valid_raw else 0.0, dense_result.mtf50) if valid_raw and dense_result.valid else float("inf")}
                raw_groups.append(group)
                raw_bias_matrix[sigma_idx, angle_idx] = float(np.mean([item["mtf50_err_pct"] for item in valid_raw])) if valid_raw else np.nan
                raw_roi_spread_matrix[sigma_idx, angle_idx] = group["roi_spread_pct"]
                raw_pair_delta_matrix[sigma_idx, angle_idx] = group["max_g1_g2_delta_pct"]
    checks.append(check("Dense Bias", all(item["valid"] for item in dense_cases) and max(item["mtf50_err_pct"] for item in dense_cases) <= 10.0 and max(item["mtf20_err_pct"] for item in dense_cases) <= 10.0 and max(item["curve_rmse"] for item in dense_cases) <= 0.08, "Measured MTF tracks the analytical reference within the configured bias and RMSE limits.", cases=len(dense_cases), invalid_cases=sum(1 for item in dense_cases if not item["valid"]), max_mtf50_error_pct=max(item["mtf50_err_pct"] for item in dense_cases), max_mtf20_error_pct=max(item["mtf20_err_pct"] for item in dense_cases), max_curve_rmse=max(item["curve_rmse"] for item in dense_cases), mtf_error_limit_pct=10.0, curve_rmse_limit=0.08))
    if args.mode in {"raw", "both"}:
        checks.append(check("Raw Bias", all(item["valid"] for item in raw_cases) and max(item["mtf50_err_pct"] for item in raw_cases) <= 12.0 and max(item["mtf20_err_pct"] for item in raw_cases) <= 12.0 and max(item["curve_rmse"] for item in raw_cases) <= 0.10, "Measured MTF tracks the analytical reference within the configured bias and RMSE limits.", cases=len(raw_cases), invalid_cases=sum(1 for item in raw_cases if not item["valid"]), max_mtf50_error_pct=max(item["mtf50_err_pct"] for item in raw_cases), max_mtf20_error_pct=max(item["mtf20_err_pct"] for item in raw_cases), max_curve_rmse=max(item["curve_rmse"] for item in raw_cases), mtf_error_limit_pct=12.0, curve_rmse_limit=0.10))
        max_dense_increase = max((series[idx + 1] - series[idx] for angle_deg in SCIENTIFIC_ANGLES_DEG for series in [[item["mtf50"] for item in dense_cases if item["valid"] and item["angle_deg"] == angle_deg]] for idx in range(len(series) - 1)), default=0.0)
        max_raw_increase = max((series[idx + 1] - series[idx] for angle_deg in SCIENTIFIC_ANGLES_DEG for series in [[item["mean_raw_mtf50_lpmm"] for item in raw_groups if item["valid_case_count"] > 0 and item["angle_deg"] == angle_deg]] for idx in range(len(series) - 1)), default=0.0)
        dense_spread_max = max(spread_pct([item["mtf50"] for item in dense_cases if item["blur_sigma_px"] == sigma and item["valid"]]) for sigma in SCIENTIFIC_BLUR_SIGMAS_PX)
        raw_spread_max = max(spread_pct([item["mean_raw_mtf50_lpmm"] for item in raw_groups if item["blur_sigma_px"] == sigma and item["valid_case_count"] > 0]) for sigma in SCIENTIFIC_BLUR_SIGMAS_PX)
        checks.append(check("Ranking", max_dense_increase <= 1e-3 and max_raw_increase <= 1e-3, "Increasing blur sigma must never produce a higher MTF50 in the scientific sweep.", max_dense_increase_lpmm=max_dense_increase, max_raw_increase_lpmm=max_raw_increase, tolerance_lpmm=1e-3))
        checks.append(check("Invariance", dense_spread_max <= 5.0 and raw_spread_max <= 5.0, "For fixed blur, the measured MTF50 should stay angle-stable across the scientific sweep.", max_dense_spread_pct=dense_spread_max, max_raw_spread_pct=raw_spread_max, spread_limit_pct=5.0))
        checks.append(check("Raw Parity", max(group["roi_spread_pct"] for group in raw_groups) <= 1.0 and max(group["max_g1_g2_delta_pct"] for group in raw_groups) <= 1.0, "Raw G1/G2 results and ROI-origin shifts stay tied to physical Bayer phase and remain invariant.", worst_roi_spread_pct=max(group["roi_spread_pct"] for group in raw_groups), worst_g1_g2_delta_pct=max(group["max_g1_g2_delta_pct"] for group in raw_groups), limit_pct=1.0))
        checks.append(check("Raw vs Dense", max(group["raw_vs_dense_delta_pct"] for group in raw_groups) <= 5.0, "The mean raw-green MTF50 should stay close to the dense result for the same blur and angle.", worst_delta_pct=max(group["raw_vs_dense_delta_pct"] for group in raw_groups), limit_pct=5.0))
    if not args.no_png:
        save_heatmap(dense_bias_matrix, SCIENTIFIC_ANGLES_DEG, SCIENTIFIC_BLUR_SIGMAS_PX, output_dir / "dense_bias_heatmap.png", "Dense Bias Heatmap (MTF50 error %)", "Relative error (%)")
        if args.mode in {"raw", "both"}:
            save_heatmap(raw_bias_matrix, SCIENTIFIC_ANGLES_DEG, SCIENTIFIC_BLUR_SIGMAS_PX, output_dir / "raw_bias_heatmap.png", "Raw Bias Heatmap (mean MTF50 error %)", "Relative error (%)")
            save_raw_parity_plot(raw_roi_spread_matrix, raw_pair_delta_matrix, SCIENTIFIC_ANGLES_DEG, SCIENTIFIC_BLUR_SIGMAS_PX, output_dir / "raw_parity_invariance.png")
            save_blur_ranking_plot(dense_cases, raw_groups, output_dir / "blur_ranking.png")
        save_summary_png(checks, output_dir / "scientific_summary.png")
    report = {
        "profile": "scientific",
        "checks": checks,
        "official_angle_window_deg": official_angle_window(),
        "boundary_cases": boundary_cases,
        "dense_cases": dense_cases,
        "raw_cases": raw_cases,
        "raw_groups": raw_groups,
        "dense_bias_heatmap_pct": dense_bias_matrix,
        "raw_bias_heatmap_pct": raw_bias_matrix,
        "raw_roi_spread_heatmap_pct": raw_roi_spread_matrix,
        "raw_pair_delta_heatmap_pct": raw_pair_delta_matrix,
    }
    return checks, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--profile", choices=("quick", "scientific", "reference-target"), default="quick")
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


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.profile == "scientific":
        checks, report = scientific(args, output_dir)
    elif args.profile == "reference-target":
        checks, report = reference_target(args, output_dir)
    else:
        checks, report = quick(args, output_dir)
    if args.report_json:
        Path(args.report_json).write_text(json.dumps(to_jsonable(report), indent=2), encoding="utf-8")
    for item in checks:
        print(format_check(item))
        print()
    overall_pass = all(item["passed"] for item in checks)
    print("[Overall]")
    print(f"status: {'PASS' if overall_pass else 'FAIL'}")
    print(f"profile: {args.profile}")
    if args.report_json:
        print(f"report_json: {Path(args.report_json).resolve()}")
    print(f"artifacts: {output_dir.resolve()}")
    return 0 if overall_pass else 1
