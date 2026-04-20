"""Tests for the standalone validator entrypoint."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]


def test_standalone_validator_main_delegates_to_repo_shared_main(monkeypatch):
    module_path = ROOT / "mtf_synthetic_validation.py"
    spec = importlib.util.spec_from_file_location("mtf_synthetic_validation_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None

    fake_repo = types.SimpleNamespace(main=lambda: 7)
    monkeypatch.setitem(sys.modules, "mtf_validation_repo", fake_repo)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)

    assert module.main() == 7


def test_quick_validator_writes_shared_curve_and_run_exports():
    sys.path.insert(0, str(ROOT))
    try:
        import mtf_validation_repo
    finally:
        sys.path.pop(0)

    output_dir = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "validator_quick"
    output_dir.mkdir(parents=True, exist_ok=True)

    args = SimpleNamespace(
        profile="quick",
        mode="both",
        output_dir=str(output_dir),
        report_json=None,
        pixel_size_um=2.4,
        angle_deg=5.0,
        blur_sigma=1.0,
        image_size=240,
        roi_size=200,
        no_png=True,
    )

    checks, report = mtf_validation_repo.quick(args, output_dir)

    assert all(item["passed"] for item in checks)
    assert report["profile"] == "quick"
    expected = {
        "context.csv",
        "summary.csv",
        "dense_esf.csv",
        "dense_lsf.csv",
        "dense_mtf.csv",
        "raw_esf.csv",
        "raw_lsf.csv",
        "raw_mtf.csv",
    }
    assert expected.issubset({path.name for path in output_dir.iterdir()})
    context_text = (output_dir / "context.csv").read_text(encoding="utf-8")
    assert "official_window_deg=3.0..10.0" in context_text
    assert "official_selected_acceptance=accepted" in context_text


def test_reference_target_validator_writes_shared_curve_and_run_exports():
    sys.path.insert(0, str(ROOT))
    try:
        import mtf_validation_repo
    finally:
        sys.path.pop(0)

    output_dir = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "validator_reference"
    output_dir.mkdir(parents=True, exist_ok=True)

    args = SimpleNamespace(
        profile="reference-target",
        mode="both",
        output_dir=str(output_dir),
        report_json=None,
        pixel_size_um=2.4,
        angle_deg=5.0,
        blur_sigma=1.0,
        image_size=240,
        roi_size=200,
        no_png=True,
    )

    checks, report = mtf_validation_repo.reference_target(args, output_dir)

    assert report["profile"] == "reference-target"
    assert {item["name"] for item in checks} == {
        "Reference Target",
        "Dense vs Reference",
        "Raw vs Reference",
        "Official Angle Window",
    }
    expected = {
        "context.csv",
        "summary.csv",
        "dense_esf.csv",
        "dense_lsf.csv",
        "dense_mtf.csv",
        "raw_esf.csv",
        "raw_lsf.csv",
        "raw_mtf.csv",
    }
    assert expected.issubset({path.name for path in output_dir.iterdir()})
    context_text = (output_dir / "context.csv").read_text(encoding="utf-8")
    assert "official_window_deg=3.0..10.0" in context_text
    assert "official_selected_acceptance=accepted" in context_text


def test_quick_validator_rejects_angle_below_official_window_even_if_node_is_valid():
    sys.path.insert(0, str(ROOT))
    try:
        import mtf_validation_repo
    finally:
        sys.path.pop(0)

    output_dir = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "validator_quick_low_angle"
    output_dir.mkdir(parents=True, exist_ok=True)

    args = SimpleNamespace(
        profile="quick",
        mode="both",
        output_dir=str(output_dir),
        report_json=None,
        pixel_size_um=2.4,
        angle_deg=2.5,
        blur_sigma=1.0,
        image_size=240,
        roi_size=200,
        no_png=True,
    )

    checks, report = mtf_validation_repo.quick(args, output_dir)

    official_check = next(item for item in checks if item["name"] == "Official Angle Window")
    assert official_check["passed"] is False
    assert official_check["metrics"]["node_valid"] is True
    assert official_check["metrics"]["official_sop_accepted"] is False
    assert report["official_angle_window_deg"]["recommended_min_edge_angle_deg"] == 3.0
    context_text = (output_dir / "context.csv").read_text(encoding="utf-8")
    assert "official_selected_acceptance=rejected" in context_text


def test_scientific_validator_reports_boundary_window_cases():
    sys.path.insert(0, str(ROOT))
    try:
        import mtf_validation_repo
    finally:
        sys.path.pop(0)

    output_dir = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "validator_scientific_boundary"
    output_dir.mkdir(parents=True, exist_ok=True)

    args = SimpleNamespace(
        profile="scientific",
        mode="both",
        output_dir=str(output_dir),
        report_json=None,
        pixel_size_um=2.4,
        angle_deg=5.0,
        blur_sigma=1.0,
        image_size=240,
        roi_size=200,
        no_png=True,
    )

    checks, report = mtf_validation_repo.scientific(args, output_dir)

    boundary_check = next(item for item in checks if item["name"] == "Official Boundary Window")
    assert boundary_check["passed"] is True
    boundary_cases = {item["requested_angle_deg"]: item for item in report["boundary_cases"]}
    assert boundary_cases[2.5]["node_valid"] is True
    assert boundary_cases[2.5]["official_sop_accepted"] is False
    assert boundary_cases[3.0]["official_sop_accepted"] is True
    assert boundary_cases[10.0]["official_sop_accepted"] is True
    assert boundary_cases[10.5]["official_sop_accepted"] is False
    assert boundary_cases[10.5]["node_valid"] is False
