"""Unit tests for mtf_verification_stats helpers."""

import importlib.util
from pathlib import Path

import pytest


parent_dir = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location(
    "mtf_verification_stats",
    parent_dir / "verification" / "algorithms" / "mtf_verification_stats.py"
)
stats_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats_module)

estimate_peak_position = stats_module.estimate_peak_position
extract_metric_values = stats_module.extract_metric_values
summarize_numeric_values = stats_module.summarize_numeric_values
summarize_mtf_by_group = stats_module.summarize_mtf_by_group
summarize_mtf_by_direction = stats_module.summarize_mtf_by_direction
annotate_correlation_mtf_quality = stats_module.annotate_correlation_mtf_quality


def test_extract_metric_values_valid_only():
    rows = [
        {"valid": "true", "mtf50_lpmm": "42.0"},
        {"valid": "false", "mtf50_lpmm": "99.0"},
        {"valid": True, "mtf50_lpmm": 43.5},
    ]
    values = extract_metric_values(rows, "mtf50_lpmm")
    assert values == [42.0, 43.5]


def test_summarize_numeric_values_non_empty():
    summary = summarize_numeric_values([1.0, 2.0, 3.0, 4.0])
    assert summary["count"] == 4
    assert summary["mean"] == pytest.approx(2.5)
    assert summary["std"] > 0
    assert summary["ci_lower"] <= summary["mean"] <= summary["ci_upper"]


def test_summarize_mtf_by_group():
    rows = [
        {"valid": "true", "position": "center", "edge": "left",
         "mtf50_lpmm": "40", "mtf20_lpmm": "60", "mtf10_lpmm": "70",
         "edge_angle_deg": "5", "contrast": "0.45", "axis_position_mm": "277.90"},
        {"valid": "true", "position": "center", "edge": "left",
         "mtf50_lpmm": "44", "mtf20_lpmm": "62", "mtf10_lpmm": "72",
         "edge_angle_deg": "6", "contrast": "0.50", "axis_position_mm": "277.95"},
        {"valid": "false", "position": "center", "edge": "left",
         "mtf50_lpmm": "100", "mtf20_lpmm": "100", "mtf10_lpmm": "100",
         "edge_angle_deg": "0", "contrast": "0.1", "axis_position_mm": "278.50"},
        {"valid": "true", "position": "top_left", "edge": "top",
         "mtf50_lpmm": "30", "mtf20_lpmm": "50", "mtf10_lpmm": "65",
         "edge_angle_deg": "4", "contrast": "0.40", "axis_position_mm": "278.10"},
    ]
    summary_rows = summarize_mtf_by_group(rows)
    assert len(summary_rows) == 2
    center_left = next(r for r in summary_rows if r["position"] == "center" and r["edge"] == "left")
    assert center_left["count"] == 2
    assert center_left["mtf50_mean"] == pytest.approx(42.0)
    assert center_left["axis_position_mean"] == pytest.approx(277.925)


def test_summarize_mtf_by_direction():
    rows = [
        {"valid": "true", "edge": "top", "mtf50_lpmm": "30", "mtf20_lpmm": "45", "mtf10_lpmm": "55", "axis_position_mm": "278.00"},
        {"valid": "true", "edge": "bottom", "mtf50_lpmm": "32", "mtf20_lpmm": "47", "mtf10_lpmm": "57", "axis_position_mm": "278.02"},
        {"valid": "true", "edge": "left", "mtf50_lpmm": "40", "mtf20_lpmm": "55", "mtf10_lpmm": "65", "axis_position_mm": "277.95"},
        {"valid": "false", "edge": "right", "mtf50_lpmm": "100", "mtf20_lpmm": "100", "mtf10_lpmm": "100", "axis_position_mm": "279.00"},
    ]
    direction_rows = summarize_mtf_by_direction(rows)
    assert len(direction_rows) == 2
    vertical = next(r for r in direction_rows if r["direction"] == "vertical")
    horizontal = next(r for r in direction_rows if r["direction"] == "horizontal")
    assert vertical["count"] == 2
    assert vertical["mtf50_mean"] == pytest.approx(31.0)
    assert vertical["axis_position_mean"] == pytest.approx(278.01)
    assert horizontal["count"] == 1
    assert horizontal["mtf50_mean"] == pytest.approx(40.0)


def test_estimate_peak_position_quadratic_fit():
    rows = []
    true_peak = 2.2
    for x in [0.0, 1.0, 2.0, 3.0, 4.0]:
        value = -((x - true_peak) ** 2) + 10.0
        rows.append({"position_mm": x, "tenengrad": value})

    peak = estimate_peak_position(rows, position_key="position_mm", value_key="tenengrad")
    assert peak is not None
    assert peak == pytest.approx(true_peak, abs=0.05)


def test_estimate_peak_position_boundary_fallback():
    rows = [
        {"position_mm": 0.0, "tenengrad": 10.0},
        {"position_mm": 1.0, "tenengrad": 8.0},
        {"position_mm": 2.0, "tenengrad": 6.0},
    ]
    peak = estimate_peak_position(rows, position_key="position_mm", value_key="tenengrad")
    assert peak == pytest.approx(0.0)


def test_annotate_correlation_mtf_quality_flags_suspicious_low_tenengrad_spike():
    rows = [
        {"position_mm": 0.0, "tenengrad": 95.0, "mtf50_lpmm": 35.0, "valid": True},
        {"position_mm": 1.0, "tenengrad": 88.0, "mtf50_lpmm": 34.0, "valid": True},
        {"position_mm": 2.0, "tenengrad": 12.0, "mtf50_lpmm": 82.0, "valid": True},
        {"position_mm": 3.0, "tenengrad": 80.0, "mtf50_lpmm": 33.0, "valid": True},
        {"position_mm": 4.0, "tenengrad": 92.0, "mtf50_lpmm": 34.0, "valid": True},
    ]

    summary = annotate_correlation_mtf_quality(rows)

    suspicious = [r for r in rows if r.get("mtf_is_suspicious")]
    assert summary["points_valid"] == 5
    assert summary["points_suspicious"] >= 1
    assert len(suspicious) >= 1
    assert any("low_ten_high_mtf" in r.get("mtf_suspicion_reasons", "") for r in suspicious)
    assert any(bool(r.get("mtf_defocus_zone")) for r in suspicious)
    assert any(bool(r.get("mtf_exclude_from_peak_fit")) for r in suspicious)
    assert any(float(r.get("mtf50_ratio_neighbor", 0.0) or 0.0) > 1.0 for r in suspicious)


def test_annotate_correlation_mtf_quality_marks_invalid_rows():
    rows = [
        {"position_mm": 0.0, "tenengrad": 10.0, "mtf50_lpmm": 0.0, "valid": False},
        {"position_mm": 1.0, "tenengrad": 20.0, "mtf50_lpmm": 25.0, "valid": True},
        {"position_mm": 2.0, "tenengrad": 25.0, "mtf50_lpmm": 27.0, "valid": True},
    ]

    summary = annotate_correlation_mtf_quality(rows)

    assert summary["points_valid"] == 2
    assert rows[0]["mtf_quality_class"] == "invalid"
    assert rows[0]["mtf_suspicion_reasons"] == ""
