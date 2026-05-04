"""Small helpers for stable MTF run exports."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np


SUMMARY_FIELDNAMES = [
    "run_id",
    "selected_for_response",
    "edge_label",
    "edge_name",
    "edge_direction",
    "valid",
    "sample_count",
    "stored_sample_count",
    "valid_sample_count",
    "rejected_sample_count",
    "contrast",
    "roi_bbox_x",
    "roi_bbox_y",
    "roi_bbox_w",
    "roi_bbox_h",
    "analysis_roi_x",
    "analysis_roi_y",
    "analysis_roi_w",
    "analysis_roi_h",
    "mtf50_lpmm",
    "mtf20_lpmm",
    "mtf10_lpmm",
    "nyquist_lpmm",
    "mtf_peak_raw",
    "mtf_peak_used",
    "mtf_clipped",
    "edge_angle_deg",
    "edge_angle_method",
    "edge_angle_geometric_deg",
    "edge_angle_phase_deg",
    "edge_angle_consistency_deg",
    "official_sop_angle_window_ok",
    "official_sop_min_angle_deg",
    "official_sop_max_angle_deg",
    "official_sop_angle_basis",
    "official_sop_reason",
    "edge_fit_residual_px",
    "edge_support_points",
    "g1_mtf50_lpmm",
    "g2_mtf50_lpmm",
    "g1_g2_delta_pct",
    "capture_mode",
    "capture_pixel_format",
    "capture_binning_h",
    "capture_binning_v",
    "capture_exposure_us",
    "capture_gain",
    "illumination_wavelength_um",
    "warning_msg",
    "error_msg",
]

CONTEXT_FIELDNAMES = [
    "run_id",
    "timestamp",
    "measurement_success",
    "measurement_error",
    "measurement_warning",
    "operator",
    "roi_mode",
    "measurement_mode",
    "roi_input_source",
    "requested_roi_x",
    "requested_roi_y",
    "requested_roi_width",
    "requested_roi_height",
    "roi_detection_min_contour_area_px",
    "roi_detection_min_square_area_px",
    "roi_detection_min_square_side_px",
    "roi_detection_min_edge_roi_width_px",
    "roi_detection_edge_roi_width_px",
    "requested_target_edge",
    "selected_edge_label",
    "edge_count",
    "valid_edge_count",
    "selected_sample_count",
    "camera_objective",
    "objective_magnification_x",
    "effective_pixel_size_um",
    "pixel_size_source",
    "focus_position_mm",
    "capture_readback_ok",
    "capture_readback_mismatches",
    "capture_available_keys",
    "stream_width_px",
    "stream_height_px",
    "requested_stream_width_px",
    "requested_stream_height_px",
    "stream_geometry_matches_request",
    "capture_pixel_format",
    "capture_binning_h",
    "capture_binning_v",
    "capture_exposure_us",
    "capture_gain",
    "source_encoding",
    "selected_capture_mode",
    "selected_mtf_peak_raw",
    "selected_mtf_peak_used",
    "selected_mtf_clipped",
    "selected_edge_angle_method",
    "selected_measured_edge_angle_deg",
    "selected_official_sop_angle_window_ok",
    "selected_official_sop_min_angle_deg",
    "selected_official_sop_max_angle_deg",
    "selected_official_sop_angle_basis",
    "selected_official_sop_reason",
    "notes",
]

OFFICIAL_SOP_MIN_ANGLE_DEG = 3.0
OFFICIAL_SOP_MAX_ANGLE_DEG = 10.0
OFFICIAL_SOP_ANGLE_BASIS = "measured_final_edge_angle_deg"


def _mean_attr(samples: list[Any], attr_name: str) -> float:
    """Return a stable float mean for one result attribute."""
    if not samples:
        return 0.0
    return float(np.mean([float(getattr(sample, attr_name, 0.0) or 0.0) for sample in samples]))


def _analysis_bounds(result: Any) -> tuple[int, int, int, int]:
    """Return analysis-strip bounds as x/y/w/h."""
    bounds = getattr(result, "analysis_roi_bounds", None)
    if not bounds or len(bounds) != 4:
        return 0, 0, 0, 0
    x1, y1, x2, y2 = [int(value) for value in bounds]
    return x1, y1, max(0, x2 - x1), max(0, y2 - y1)


def _resolve_measured_edge_angle_deg(result: Any, valid_samples: list[Any]) -> float | None:
    """Return the final measured edge angle that should drive SOP acceptance."""
    if valid_samples:
        return _mean_attr(valid_samples, "edge_angle")

    edge_angle = getattr(result, "edge_angle", None)
    if edge_angle is None:
        return None
    return float(edge_angle)


def _build_official_sop_fields(
    *,
    is_valid: bool,
    measured_angle_deg: float | None,
    missing_reason: str,
) -> dict[str, object]:
    """Evaluate the official laboratory angle window independently from node validity."""
    fields: dict[str, object] = {
        "official_sop_angle_window_ok": 0,
        "official_sop_min_angle_deg": OFFICIAL_SOP_MIN_ANGLE_DEG,
        "official_sop_max_angle_deg": OFFICIAL_SOP_MAX_ANGLE_DEG,
        "official_sop_angle_basis": OFFICIAL_SOP_ANGLE_BASIS,
        "official_sop_reason": "",
    }

    if not is_valid:
        fields["official_sop_reason"] = "edge technically invalid; no official SOP acceptance"
        return fields

    if measured_angle_deg is None:
        fields["official_sop_reason"] = missing_reason
        return fields

    abs_angle_deg = abs(float(measured_angle_deg))
    if abs_angle_deg < OFFICIAL_SOP_MIN_ANGLE_DEG:
        fields["official_sop_reason"] = (
            f"measured angle {abs_angle_deg:.2f}deg below official SOP minimum "
            f"{OFFICIAL_SOP_MIN_ANGLE_DEG:.1f}deg"
        )
        return fields

    if abs_angle_deg > OFFICIAL_SOP_MAX_ANGLE_DEG:
        fields["official_sop_reason"] = (
            f"measured angle {abs_angle_deg:.2f}deg above official SOP maximum "
            f"{OFFICIAL_SOP_MAX_ANGLE_DEG:.1f}deg"
        )
        return fields

    fields["official_sop_angle_window_ok"] = 1
    return fields


def build_edge_summary_row(
    *,
    run_id: str,
    edge_label: str,
    edge_roi: Any,
    result: Any,
    valid_samples: list[Any],
    selected_for_response: bool,
    stored_sample_count: int | None = None,
) -> dict[str, object]:
    """Build one normalized summary row for a measured edge."""
    x, y, w, h = [int(value) for value in edge_roi.bbox]
    analysis_x, analysis_y, analysis_w, analysis_h = _analysis_bounds(result)
    measured_angle_deg = _resolve_measured_edge_angle_deg(result, valid_samples)
    valid_sample_count = int(len(valid_samples))
    stored_count = (
        valid_sample_count
        if stored_sample_count is None
        else max(0, int(stored_sample_count))
    )
    sop_fields = _build_official_sop_fields(
        is_valid=bool(getattr(result, "valid", False)),
        measured_angle_deg=measured_angle_deg,
        missing_reason="measured angle unavailable; no official SOP acceptance",
    )

    return {
        "run_id": run_id,
        "selected_for_response": int(bool(selected_for_response)),
        "edge_label": edge_label,
        "edge_name": str(edge_roi.edge_name),
        "edge_direction": str(edge_roi.edge_direction),
        "valid": int(bool(getattr(result, "valid", False))),
        "sample_count": valid_sample_count,
        "stored_sample_count": stored_count,
        "valid_sample_count": valid_sample_count,
        "rejected_sample_count": max(0, stored_count - valid_sample_count),
        "contrast": float(edge_roi.contrast),
        "roi_bbox_x": x,
        "roi_bbox_y": y,
        "roi_bbox_w": w,
        "roi_bbox_h": h,
        "analysis_roi_x": analysis_x,
        "analysis_roi_y": analysis_y,
        "analysis_roi_w": analysis_w,
        "analysis_roi_h": analysis_h,
        "mtf50_lpmm": _mean_attr(valid_samples, "mtf50"),
        "mtf20_lpmm": _mean_attr(valid_samples, "mtf20"),
        "mtf10_lpmm": _mean_attr(valid_samples, "mtf10"),
        "nyquist_lpmm": float(getattr(result, "nyquist_frequency", 0.0) or 0.0),
        "mtf_peak_raw": float(getattr(result, "mtf_peak_raw", 0.0) or 0.0),
        "mtf_peak_used": float(getattr(result, "mtf_peak", 0.0) or 0.0),
        "mtf_clipped": int(bool(getattr(result, "mtf_clipped", False))),
        "edge_angle_deg": float(measured_angle_deg or 0.0),
        "edge_angle_method": str(getattr(result, "edge_angle_method", "") or ""),
        "edge_angle_geometric_deg": float(getattr(result, "edge_angle_geometric", 0.0) or 0.0),
        "edge_angle_phase_deg": float(getattr(result, "edge_angle_phase", 0.0) or 0.0),
        "edge_angle_consistency_deg": float(
            getattr(result, "edge_angle_consistency_deg", 0.0) or 0.0
        ),
        **sop_fields,
        "edge_fit_residual_px": float(getattr(result, "edge_fit_residual_px", 0.0) or 0.0),
        "edge_support_points": int(getattr(result, "edge_support_points", 0) or 0),
        "g1_mtf50_lpmm": _mean_attr(valid_samples, "g1_mtf50"),
        "g2_mtf50_lpmm": _mean_attr(valid_samples, "g2_mtf50"),
        "g1_g2_delta_pct": _mean_attr(valid_samples, "g1_g2_delta_pct"),
        "capture_mode": str(getattr(result, "capture_mode", "") or ""),
        "capture_pixel_format": str(getattr(result, "capture_pixel_format", "") or ""),
        "capture_binning_h": int(getattr(result, "capture_binning_h", 0) or 0),
        "capture_binning_v": int(getattr(result, "capture_binning_v", 0) or 0),
        "capture_exposure_us": float(getattr(result, "capture_exposure_us", 0.0) or 0.0),
        "capture_gain": float(getattr(result, "capture_gain", 0.0) or 0.0),
        "illumination_wavelength_um": float(
            getattr(result, "illumination_wavelength_um", 0.0) or 0.0
        ),
        "warning_msg": str(getattr(result, "warning_msg", "") or ""),
        "error_msg": str(getattr(result, "error_msg", "") or ""),
    }


def build_context_row(
    *,
    run_id: str,
    timestamp: str,
    measurement_metadata: dict[str, object],
    roi_mode: str,
    focus_position_mm: float | None,
    capture_values: dict[str, object],
    capture_available_keys: list[str],
    capture_readback_mismatches: list[str],
    capture_readback_ok: bool,
    image_encoding: str,
    edge_count: int,
    valid_edge_count: int,
    selected_edge_label: str,
    selected_result: Any | None,
    selected_edge_angle_deg: float | None,
    selected_sample_count: int,
    measurement_success: bool,
    measurement_error: str,
) -> dict[str, object]:
    """Build the one-row context CSV used for later comparisons."""
    warning_msg = str(getattr(selected_result, "warning_msg", "") or "")
    if selected_result is None:
        selected_sop_fields = {
            "selected_measured_edge_angle_deg": "",
            "selected_official_sop_angle_window_ok": 0,
            "selected_official_sop_min_angle_deg": OFFICIAL_SOP_MIN_ANGLE_DEG,
            "selected_official_sop_max_angle_deg": OFFICIAL_SOP_MAX_ANGLE_DEG,
            "selected_official_sop_angle_basis": OFFICIAL_SOP_ANGLE_BASIS,
            "selected_official_sop_reason": "no valid selected edge",
        }
    else:
        sop_fields = _build_official_sop_fields(
            is_valid=bool(getattr(selected_result, "valid", False)),
            measured_angle_deg=selected_edge_angle_deg,
            missing_reason="measured angle unavailable; no official SOP acceptance",
        )
        selected_sop_fields = {
            "selected_measured_edge_angle_deg": (
                float(selected_edge_angle_deg) if selected_edge_angle_deg is not None else ""
            ),
            "selected_official_sop_angle_window_ok": sop_fields["official_sop_angle_window_ok"],
            "selected_official_sop_min_angle_deg": sop_fields["official_sop_min_angle_deg"],
            "selected_official_sop_max_angle_deg": sop_fields["official_sop_max_angle_deg"],
            "selected_official_sop_angle_basis": sop_fields["official_sop_angle_basis"],
            "selected_official_sop_reason": sop_fields["official_sop_reason"],
        }
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "measurement_success": int(bool(measurement_success)),
        "measurement_error": measurement_error,
        "measurement_warning": warning_msg,
        "operator": str(measurement_metadata.get("measurement_operator", "default_user")),
        "roi_mode": roi_mode,
        "measurement_mode": str(measurement_metadata.get("measurement_mode", "") or ""),
        "roi_input_source": str(measurement_metadata.get("roi_input_source", "none") or "none"),
        "requested_roi_x": int(measurement_metadata.get("requested_roi_x", 0) or 0),
        "requested_roi_y": int(measurement_metadata.get("requested_roi_y", 0) or 0),
        "requested_roi_width": int(
            measurement_metadata.get("requested_roi_width", 0) or 0
        ),
        "requested_roi_height": int(
            measurement_metadata.get("requested_roi_height", 0) or 0
        ),
        "roi_detection_min_contour_area_px": int(
            measurement_metadata.get("roi_detection_min_contour_area", 0) or 0
        ),
        "roi_detection_min_square_area_px": int(
            measurement_metadata.get("roi_detection_min_square_area", 0) or 0
        ),
        "roi_detection_min_square_side_px": int(
            measurement_metadata.get("roi_detection_min_square_side", 0) or 0
        ),
        "roi_detection_min_edge_roi_width_px": int(
            measurement_metadata.get("roi_detection_min_edge_roi_width", 0) or 0
        ),
        "roi_detection_edge_roi_width_px": int(
            measurement_metadata.get("roi_detection_edge_roi_width", 0) or 0
        ),
        "requested_target_edge": str(measurement_metadata.get("target_edge", "") or ""),
        "selected_edge_label": selected_edge_label,
        "edge_count": int(edge_count),
        "valid_edge_count": int(valid_edge_count),
        "selected_sample_count": int(selected_sample_count),
        "camera_objective": str(measurement_metadata.get("camera_objective", "") or ""),
        "objective_magnification_x": float(
            measurement_metadata.get("objective_magnification_x", 0.0) or 0.0
        ),
        "effective_pixel_size_um": float(
            measurement_metadata.get("effective_pixel_size_um", 0.0) or 0.0
        ),
        "pixel_size_source": str(measurement_metadata.get("pixel_size_source", "") or ""),
        "focus_position_mm": float(focus_position_mm) if focus_position_mm is not None else "",
        "capture_readback_ok": int(bool(capture_readback_ok)),
        "capture_readback_mismatches": "; ".join(str(item) for item in capture_readback_mismatches),
        "capture_available_keys": "; ".join(str(item) for item in capture_available_keys),
        "stream_width_px": int(capture_values.get("stream_width_px", 0) or 0),
        "stream_height_px": int(capture_values.get("stream_height_px", 0) or 0),
        "requested_stream_width_px": int(
            capture_values.get("requested_stream_width_px", 0) or 0
        ),
        "requested_stream_height_px": int(
            capture_values.get("requested_stream_height_px", 0) or 0
        ),
        "stream_geometry_matches_request": int(
            bool(capture_values.get("stream_geometry_matches_request", False))
        ),
        "capture_pixel_format": str(capture_values.get("pixel_format", "") or ""),
        "capture_binning_h": int(capture_values.get("bin_h", 0) or 0),
        "capture_binning_v": int(capture_values.get("bin_v", 0) or 0),
        "capture_exposure_us": float(capture_values.get("exposure_time", 0.0) or 0.0),
        "capture_gain": float(capture_values.get("gain", 0.0) or 0.0),
        "source_encoding": str(image_encoding or ""),
        "selected_capture_mode": str(getattr(selected_result, "capture_mode", "") or ""),
        "selected_mtf_peak_raw": float(getattr(selected_result, "mtf_peak_raw", 0.0) or 0.0),
        "selected_mtf_peak_used": float(getattr(selected_result, "mtf_peak", 0.0) or 0.0),
        "selected_mtf_clipped": int(bool(getattr(selected_result, "mtf_clipped", False))),
        "selected_edge_angle_method": str(
            getattr(selected_result, "edge_angle_method", "") or ""
        ),
        **selected_sop_fields,
        "notes": str(measurement_metadata.get("notes", "") or ""),
    }


def write_summary_csv(run_dir: Path, rows: list[dict[str, object]]) -> Path:
    """Write one stable per-run summary table."""
    summary_path = run_dir / "summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in SUMMARY_FIELDNAMES})
    return summary_path


def write_context_csv(run_dir: Path, row: dict[str, object]) -> Path:
    """Write the canonical one-line run context CSV."""
    context_path = run_dir / "context.csv"
    with open(context_path, "w", newline="", encoding="utf-8") as context_file:
        writer = csv.DictWriter(context_file, fieldnames=CONTEXT_FIELDNAMES)
        writer.writeheader()
        writer.writerow({name: row.get(name, "") for name in CONTEXT_FIELDNAMES})
    return context_path


def write_selected_edge_marker(run_dir: Path, edge_label: str) -> Path:
    """Write the edge label that was returned through the service response."""
    selected_path = run_dir / "selected_edge.txt"
    selected_path.write_text(f"{edge_label}\n", encoding="utf-8")
    return selected_path
