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


__all__ = [
    "estimate_peak_position",
    "extract_metric_values",
    "summarize_numeric_values",
    "summarize_mtf_by_direction",
    "summarize_mtf_by_group",
]
