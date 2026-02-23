"""Utility helpers for MTF verification statistics and peak estimation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import numpy as np

try:
    from .statistics import calculate_statistics
except ImportError:  # pragma: no cover - fallback for direct file imports in tests
    import importlib.util
    from pathlib import Path

    _stats_path = Path(__file__).resolve().parent / "statistics.py"
    _stats_spec = importlib.util.spec_from_file_location("verification_statistics_fallback", _stats_path)
    _stats_module = importlib.util.module_from_spec(_stats_spec)
    _stats_spec.loader.exec_module(_stats_module)
    calculate_statistics = _stats_module.calculate_statistics


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str) and value.strip().lower() in {"", "nan", "n/a"}:
            return None
        parsed = float(value)
        if not np.isfinite(parsed):
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _row_is_valid(row: dict) -> bool:
    value = row.get("valid", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def extract_metric_values(rows: Iterable[dict], metric_key: str, valid_only: bool = True) -> list[float]:
    """Extract finite metric values from row dicts."""
    values: list[float] = []
    for row in rows:
        if valid_only and not _row_is_valid(row):
            continue
        value = _to_float(row.get(metric_key))
        if value is None:
            continue
        values.append(value)
    return values


def summarize_numeric_values(values: list[float]) -> dict:
    """Return descriptive stats for values. Uses 0 defaults for empty input."""
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "std": 0.0,
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "cv_percent": 0.0,
        }

    stats = calculate_statistics(values)
    return {
        "count": int(stats.n),
        "mean": float(stats.mean),
        "std": float(stats.std),
        "median": float(stats.median),
        "min": float(stats.min),
        "max": float(stats.max),
        "ci_lower": float(stats.ci_lower),
        "ci_upper": float(stats.ci_upper),
        "cv_percent": float(stats.cv_percent),
    }


def summarize_mtf_by_group(
    rows: Iterable[dict],
    group_keys: tuple[str, ...] = ("position", "edge"),
) -> list[dict]:
    """Aggregate valid MTF rows by group (default: position/edge)."""
    grouped: dict[tuple[Any, ...], list[dict]] = defaultdict(list)
    for row in rows:
        if not _row_is_valid(row):
            continue
        key = tuple(row.get(field, "unknown") for field in group_keys)
        grouped[key].append(row)

    metric_columns = (
        ("mtf50", "mtf50_lpmm"),
        ("mtf20", "mtf20_lpmm"),
        ("mtf10", "mtf10_lpmm"),
        ("angle", "edge_angle_deg"),
        ("contrast", "contrast"),
        ("axis_position", "axis_position_mm"),
    )

    stats_rows: list[dict] = []
    for key, items in grouped.items():
        row_stats = {field: value for field, value in zip(group_keys, key)}
        row_stats["count"] = len(items)
        for metric_name, column_name in metric_columns:
            summary = summarize_numeric_values(extract_metric_values(items, column_name, valid_only=False))
            row_stats[f"{metric_name}_mean"] = summary["mean"]
            row_stats[f"{metric_name}_std"] = summary["std"]
            row_stats[f"{metric_name}_ci_lower"] = summary["ci_lower"]
            row_stats[f"{metric_name}_ci_upper"] = summary["ci_upper"]
        stats_rows.append(row_stats)

    return stats_rows


def summarize_mtf_by_direction(rows: Iterable[dict]) -> list[dict]:
    """Aggregate valid rows by edge direction (vertical/horizontal)."""
    buckets: dict[str, list[dict]] = {
        "vertical": [],
        "horizontal": [],
    }

    for row in rows:
        if not _row_is_valid(row):
            continue
        edge = str(row.get("edge", "")).strip().lower()
        if edge in {"top", "bottom"}:
            buckets["vertical"].append(row)
        elif edge in {"left", "right"}:
            buckets["horizontal"].append(row)

    results: list[dict] = []
    for direction, items in buckets.items():
        if not items:
            continue
        mtf50_summary = summarize_numeric_values(extract_metric_values(items, "mtf50_lpmm", valid_only=False))
        mtf20_summary = summarize_numeric_values(extract_metric_values(items, "mtf20_lpmm", valid_only=False))
        mtf10_summary = summarize_numeric_values(extract_metric_values(items, "mtf10_lpmm", valid_only=False))
        axis_summary = summarize_numeric_values(extract_metric_values(items, "axis_position_mm", valid_only=False))
        results.append({
            "direction": direction,
            "count": len(items),
            "mtf50_mean": mtf50_summary["mean"],
            "mtf50_std": mtf50_summary["std"],
            "mtf50_ci_lower": mtf50_summary["ci_lower"],
            "mtf50_ci_upper": mtf50_summary["ci_upper"],
            "mtf20_mean": mtf20_summary["mean"],
            "mtf20_std": mtf20_summary["std"],
            "mtf20_ci_lower": mtf20_summary["ci_lower"],
            "mtf20_ci_upper": mtf20_summary["ci_upper"],
            "mtf10_mean": mtf10_summary["mean"],
            "mtf10_std": mtf10_summary["std"],
            "mtf10_ci_lower": mtf10_summary["ci_lower"],
            "mtf10_ci_upper": mtf10_summary["ci_upper"],
            "axis_position_mean": axis_summary["mean"],
            "axis_position_std": axis_summary["std"],
            "axis_position_ci_lower": axis_summary["ci_lower"],
            "axis_position_ci_upper": axis_summary["ci_upper"],
        })

    return results


def estimate_peak_position(
    rows: Iterable[dict],
    position_key: str,
    value_key: str,
) -> float | None:
    """Estimate peak position using local quadratic interpolation around the max."""
    pairs: list[tuple[float, float]] = []
    for row in rows:
        pos = _to_float(row.get(position_key))
        val = _to_float(row.get(value_key))
        if pos is None or val is None:
            continue
        pairs.append((pos, val))

    if not pairs:
        return None

    pairs.sort(key=lambda x: x[0])
    positions = [p[0] for p in pairs]
    values = [p[1] for p in pairs]

    best_idx = int(np.argmax(values))
    best_pos = positions[best_idx]

    if best_idx == 0 or best_idx == len(values) - 1:
        return float(best_pos)

    x1, y1 = positions[best_idx - 1], values[best_idx - 1]
    x2, y2 = positions[best_idx], values[best_idx]
    x3, y3 = positions[best_idx + 1], values[best_idx + 1]

    denominator = (x1 - x2) * (x1 - x3) * (x2 - x3)
    if abs(denominator) < 1e-12:
        return float(best_pos)

    a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denominator
    b = (x3**2 * (y1 - y2) + x2**2 * (y3 - y1) + x1**2 * (y2 - y3)) / denominator

    if a >= 0 or abs(a) < 1e-12:
        return float(best_pos)

    peak_pos = -b / (2.0 * a)
    if min(x1, x3) <= peak_pos <= max(x1, x3):
        return float(peak_pos)

    return float(best_pos)


def annotate_correlation_mtf_quality(
    rows: list[dict],
    *,
    position_key: str = "position_mm",
    mtf_key: str = "mtf50_lpmm",
    tenengrad_key: str = "tenengrad",
    valid_key: str = "valid",
) -> dict[str, float | int]:
    """Annotate rows with suspicious MTF diagnostics for correlation scans.

    Adds in-place keys per row:
    - mtf_quality_class: normal | suspicious | invalid
    - mtf_is_suspicious: bool
    - mtf_suspicion_score: float [0..1]
    - mtf_suspicion_reasons: semicolon-joined rule explanations
    - mtf_defocus_zone: bool (low Tenengrad region)
    - mtf50_robust_z: robust z-score vs all valid MTF points
    - mtf50_neighbor_median_lpmm: local median from adjacent valid points
    - mtf50_delta_neighbor_lpmm: mtf50 - local neighbor median
    - mtf50_ratio_neighbor: mtf50 / local neighbor median
    - mtf_exclude_from_peak_fit: bool, recommended filter flag
    - tenengrad_norm: normalized Tenengrad in [0..1]
    - mtf50_norm: normalized MTF50 in [0..1]
    """
    if not rows:
        return {
            "points_valid": 0,
            "points_suspicious": 0,
            "suspicious_ratio": 0.0,
            "reference_mtf50_median_lpmm": 0.0,
            "reference_mtf50_upper_lpmm": 0.0,
        }

    indexed: list[tuple[int, float, float, float]] = []
    for idx, row in enumerate(rows):
        pos = _to_float(row.get(position_key))
        mtf = _to_float(row.get(mtf_key))
        ten = _to_float(row.get(tenengrad_key))
        is_valid = _row_is_valid({"valid": row.get(valid_key, False)})
        if not is_valid or mtf is None or ten is None or mtf <= 0.0:
            row["mtf_quality_class"] = "invalid"
            row["mtf_is_suspicious"] = False
            row["mtf_suspicion_score"] = 0.0
            row["mtf_suspicion_reasons"] = ""
            row["mtf_defocus_zone"] = ""
            row["mtf50_robust_z"] = 0.0
            row["mtf50_neighbor_median_lpmm"] = ""
            row["mtf50_delta_neighbor_lpmm"] = ""
            row["mtf50_ratio_neighbor"] = ""
            row["mtf_exclude_from_peak_fit"] = True
            row["tenengrad_norm"] = ""
            row["mtf50_norm"] = ""
            continue

        if pos is None:
            pos = float(idx)
        indexed.append((idx, float(pos), float(mtf), float(ten)))

    if not indexed:
        return {
            "points_valid": 0,
            "points_suspicious": 0,
            "suspicious_ratio": 0.0,
            "reference_mtf50_median_lpmm": 0.0,
            "reference_mtf50_upper_lpmm": 0.0,
        }

    indexed.sort(key=lambda item: item[1])
    mtf_vals = np.array([item[2] for item in indexed], dtype=float)
    ten_vals = np.array([item[3] for item in indexed], dtype=float)

    mtf_min, mtf_max = float(np.min(mtf_vals)), float(np.max(mtf_vals))
    ten_min, ten_max = float(np.min(ten_vals)), float(np.max(ten_vals))
    mtf_span = max(mtf_max - mtf_min, 1e-12)
    ten_span = max(ten_max - ten_min, 1e-12)

    mtf_norm = (mtf_vals - mtf_min) / mtf_span
    ten_norm = (ten_vals - ten_min) / ten_span

    mtf_median = float(np.median(mtf_vals))
    mtf_mad = float(np.median(np.abs(mtf_vals - mtf_median)))

    reference_mask = ten_norm >= 0.7
    if int(np.sum(reference_mask)) < 3:
        reference_mask = ten_norm >= 0.5
    if int(np.sum(reference_mask)) < 2:
        threshold = float(np.percentile(ten_norm, 65.0))
        reference_mask = ten_norm >= threshold

    ref_values = mtf_vals[reference_mask] if np.any(reference_mask) else mtf_vals
    ref_median = float(np.median(ref_values)) if ref_values.size > 0 else 0.0
    ref_upper = (
        float(np.percentile(ref_values, 95.0))
        if ref_values.size > 0
        else 0.0
    )

    suspicious_count = 0
    for sorted_idx, (orig_idx, _, mtf, ten) in enumerate(indexed):
        row = rows[orig_idx]
        reasons: list[str] = []

        tn = float(ten_norm[sorted_idx])
        mn = float(mtf_norm[sorted_idx])

        if mtf_mad > 1e-12:
            robust_z = float(0.6745 * (mtf - mtf_median) / mtf_mad)
        else:
            robust_z = 0.0

        neighbor_candidates: list[float] = []
        if sorted_idx - 1 >= 0:
            neighbor_candidates.append(float(indexed[sorted_idx - 1][2]))
        if sorted_idx + 1 < len(indexed):
            neighbor_candidates.append(float(indexed[sorted_idx + 1][2]))
        if sorted_idx - 2 >= 0:
            neighbor_candidates.append(float(indexed[sorted_idx - 2][2]))
        if sorted_idx + 2 < len(indexed):
            neighbor_candidates.append(float(indexed[sorted_idx + 2][2]))

        local_median = float(np.median(neighbor_candidates)) if neighbor_candidates else 0.0
        is_defocus_zone = bool(tn < 0.35)
        delta_neighbor = float(mtf - local_median) if local_median > 0.0 else 0.0
        ratio_neighbor = float(mtf / local_median) if local_median > 0.0 else 0.0

        if tn < 0.25 and mn > 0.65:
            reasons.append(
                f"low_ten_high_mtf(ten_norm={tn:.2f},mtf_norm={mn:.2f})"
            )

        if local_median > 0.0 and mtf > (1.6 * local_median) and tn < 0.45:
            reasons.append(
                f"local_spike(mtf={mtf:.2f},neighbor_med={local_median:.2f})"
            )

        if robust_z > 3.5 and tn < 0.55:
            reasons.append(f"robust_outlier(z={robust_z:.2f})")

        if ref_upper > 0.0 and mtf > (1.25 * ref_upper) and tn < 0.55:
            reasons.append(
                f"above_sharp_reference(mtf={mtf:.2f},ref95={ref_upper:.2f})"
            )

        is_suspicious = len(reasons) > 0
        if is_suspicious:
            suspicious_count += 1

        row["mtf_quality_class"] = "suspicious" if is_suspicious else "normal"
        row["mtf_is_suspicious"] = bool(is_suspicious)
        row["mtf_suspicion_score"] = float(min(1.0, 0.35 * len(reasons)))
        row["mtf_suspicion_reasons"] = "; ".join(reasons)
        row["mtf_defocus_zone"] = bool(is_defocus_zone)
        row["mtf50_robust_z"] = float(robust_z)
        row["mtf50_neighbor_median_lpmm"] = float(local_median) if neighbor_candidates else ""
        row["mtf50_delta_neighbor_lpmm"] = float(delta_neighbor) if neighbor_candidates else ""
        row["mtf50_ratio_neighbor"] = float(ratio_neighbor) if neighbor_candidates else ""
        row["mtf_exclude_from_peak_fit"] = bool(is_suspicious)
        row["tenengrad_norm"] = float(tn)
        row["mtf50_norm"] = float(mn)

    points_valid = int(len(indexed))
    suspicious_ratio = float(suspicious_count / points_valid) if points_valid else 0.0
    return {
        "points_valid": points_valid,
        "points_suspicious": int(suspicious_count),
        "suspicious_ratio": suspicious_ratio,
        "reference_mtf50_median_lpmm": float(ref_median),
        "reference_mtf50_upper_lpmm": float(ref_upper),
    }


__all__ = [
    "annotate_correlation_mtf_quality",
    "estimate_peak_position",
    "extract_metric_values",
    "summarize_numeric_values",
    "summarize_mtf_by_direction",
    "summarize_mtf_by_group",
]
