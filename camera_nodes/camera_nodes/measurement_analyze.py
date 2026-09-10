"""Versioned offline MTF analysis; never rewrites acquisition files."""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import uuid

import numpy as np
import yaml

from .measurement_store import atomic_json, atomic_text, csv_text, digest, utc_now, verify_capture


def _as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes"}


def _as_float(value, default=None):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_online_summary(run_path):
    """Load the worker-owned online summary without touching raw captures."""
    run = Path(run_path).resolve()
    summary_path = run / "summary.csv"
    if not summary_path.is_file():
        raise ValueError(f"Online summary not found: {summary_path}")
    with summary_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Online summary is empty: {summary_path}")
    context_path = run / "resolved_condition.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8")) if context_path.is_file() else {}
    return run, context, rows


def _run_report(run, context, rows):
    mtf = [_as_float(row.get("mtf50_lp_mm_mean")) for row in rows]
    mtf = [value for value in mtf if value is not None]
    exposures = [_as_float(row.get("exposure_us")) for row in rows]
    exposures = [value for value in exposures if value is not None]
    white = [_as_float(row.get("white_level_norm")) for row in rows]
    white = [value for value in white if value is not None]
    focus = [_as_float(row.get("focus_position_mm")) for row in rows]
    focus = [value for value in focus if value is not None]
    def median_column(name):
        values = [_as_float(row.get(name)) for row in rows]
        values = [value for value in values if value is not None]
        return float(np.median(values)) if values else None

    return {
        "run_id": rows[0].get("run_id") or context.get("run_id", run.name),
        "run_directory": str(run),
        "condition_id": rows[0].get("condition_id") or context.get("condition_id", ""),
        "measurements": len(rows),
        "valid_measurements": sum(_as_bool(row.get("valid")) for row in rows),
        "mtf50_lp_mm_mean": float(np.mean(mtf)) if mtf else None,
        "mtf50_lp_mm_max": float(np.max(mtf)) if mtf else None,
        "focus_position_mm": float(np.median(focus)) if focus else None,
        "exposure_us_median": float(np.median(exposures)) if exposures else None,
        "white_level_norm_median": float(np.median(white)) if white else None,
        "black_level_norm_median": median_column("black_level_norm"),
        "p95_norm_median": median_column("p95_norm"),
        "p99_9_norm_median": median_column("p99_9_norm"),
        "saturation_fraction_median": median_column("saturation_fraction"),
        "relative_transmission": None,
        "transmission_rejection_reason": "",
    }


def _same_text(reference, comparison, keys):
    return all(str(reference.get(key, "")) == str(comparison.get(key, "")) for key in keys)


def _transmission_eligibility(reference, comparison):
    ref_context, ref_rows = reference
    cmp_context, cmp_rows = comparison
    if not all(_as_bool(row.get("auto_exposure_success")) for row in ref_rows + cmp_rows):
        return False, "auto exposure was not successful for every point"
    if not _same_text(ref_context, cmp_context, ("camera_profile", "camera_serial")):
        return False, "camera differs"
    if not _same_text(ref_context, cmp_context, (
        "objective_id", "objective_family", "magnification_x",
    )):
        return False, "objective differs"
    if not _same_text(ref_context, cmp_context, (
        "illumination_voltage_v", "illumination_color", "illumination_reference_voltage_v",
    )):
        return False, "illumination differs"

    ref_first, cmp_first = ref_rows[0], cmp_rows[0]
    if not _same_text(ref_first, cmp_first, (
        "roi_x", "roi_y", "roi_width", "roi_height", "exposure_target", "exposure_tolerance",
    )):
        return False, "ROI or AE target/tolerance differs"
    ref_gain = np.median([_as_float(row.get("gain"), np.nan) for row in ref_rows])
    cmp_gain = np.median([_as_float(row.get("gain"), np.nan) for row in cmp_rows])
    if not np.isfinite(ref_gain) or not np.isfinite(cmp_gain) or not np.isclose(ref_gain, cmp_gain):
        return False, "gain differs"

    target = _as_float(ref_first.get("exposure_target"))
    tolerance = _as_float(ref_first.get("exposure_tolerance"))
    ref_white = np.median([_as_float(row.get("white_level_norm"), np.nan) for row in ref_rows])
    cmp_white = np.median([_as_float(row.get("white_level_norm"), np.nan) for row in cmp_rows])
    if target is None or tolerance is None or not np.isfinite(ref_white) or not np.isfinite(cmp_white):
        return False, "AE white-level metadata is incomplete"
    if (abs(ref_white-target) > tolerance or abs(cmp_white-target) > tolerance
            or abs(ref_white-cmp_white) > tolerance):
        return False, "achieved white levels are outside the AE tolerance"
    return True, ""


def report_online_runs(run_paths, output_dir=None, show=False):
    """Create one report for one or more online summaries (first is reference)."""
    loaded = [load_online_summary(path) for path in run_paths]
    if output_dir:
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
    elif len(loaded) == 1:
        output = loaded[0][0] / "analysis" / f"online-report-{uuid.uuid4().hex}"
        output.mkdir(parents=True, exist_ok=False)
    else:
        output = Path.cwd() / f"measurement-comparison-{uuid.uuid4().hex}"
        output.mkdir(parents=True, exist_ok=False)

    reports = [_run_report(run, context, rows) for run, context, rows in loaded]
    ref_exposure = reports[0]["exposure_us_median"]
    if len(reports) > 1:
        ref_eligible, ref_reason = _transmission_eligibility(
            (loaded[0][1], loaded[0][2]), (loaded[0][1], loaded[0][2])
        )
        if ref_eligible and ref_exposure:
            reports[0]["relative_transmission"] = 1.0
            reports[0]["transmission_rejection_reason"] = "reference run"
        else:
            reports[0]["transmission_rejection_reason"] = ref_reason or "exposure metadata is incomplete"
    for index in range(1, len(reports)):
        eligible, reason = _transmission_eligibility(
            (loaded[0][1], loaded[0][2]), (loaded[index][1], loaded[index][2])
        )
        comparison_exposure = reports[index]["exposure_us_median"]
        if eligible and ref_exposure and comparison_exposure:
            reports[index]["relative_transmission"] = ref_exposure / comparison_exposure
        else:
            reports[index]["transmission_rejection_reason"] = reason or "exposure metadata is incomplete"

    atomic_text(output / "run_report.csv", csv_text(reports))
    atomic_json(output / "run_report.json", {
        "schema_version": 1,
        "created_utc": utc_now(),
        "reference_run_id": reports[0]["run_id"],
        "runs": reports,
    })

    import matplotlib

    if not show:
        matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for report, (_, _, rows) in zip(reports, loaded):
        label = str(report["run_id"])
        index = np.asarray([int(row["measurement_index"]) for row in rows])
        mtf = np.asarray([_as_float(row.get("mtf50_lp_mm_mean"), np.nan) for row in rows])
        std = np.asarray([_as_float(row.get("mtf50_lp_mm_std"), 0.0) for row in rows])
        axes[0, 0].errorbar(index, mtf, yerr=std, marker="o", capsize=2, label=label)
        axes[0, 1].plot(index, [_as_float(row.get("exposure_us"), np.nan) for row in rows],
                        marker="o", label=label)
        axes[1, 0].plot(index, [_as_float(row.get("white_level_norm"), np.nan) for row in rows],
                        marker="o", label=f"{label} white")
        axes[1, 0].plot(index, [_as_float(row.get("black_level_norm"), np.nan) for row in rows],
                        linestyle="--", label=f"{label} black")
        axes[1, 1].plot(index, [_as_float(row.get("p99_9_norm"), np.nan) for row in rows],
                        marker="o", label=f"{label} P99.9")
        axes[1, 1].plot(index, [_as_float(row.get("saturation_fraction"), np.nan) for row in rows],
                        linestyle="--", label=f"{label} saturation")
    for axis, title, ylabel in (
        (axes[0, 0], "MTF50 over measurement", "MTF50 (lp/mm)"),
        (axes[0, 1], "Exposure", "Exposure (µs)"),
        (axes[1, 0], "White / black levels", "Normalized level"),
        (axes[1, 1], "Clipping diagnostics", "Normalized / fraction"),
    ):
        axis.set_title(title)
        axis.set_xlabel("Measurement index")
        axis.set_ylabel(ylabel)
        axis.grid(True, alpha=0.3)
        axis.legend(fontsize="small")
    figure.savefig(output / "measurement_report.png", dpi=150)
    if show:
        plt.show()
    plt.close(figure)
    return output


def analyze_run(run_path):
    from .algorithms.mtf import MTFAnalyzer, MTFConfig, MTFResult
    run = Path(run_path).resolve()
    context = yaml.safe_load((run/"resolved_condition.yaml").read_text())
    prep = json.loads((run/"preparation.json").read_text())
    base = {key:context[key] for key in ("campaign_id", "condition_id", "experiment_id", "plan_row_number",
            "setup_id", "setup_repeat", "camera_profile", "camera_serial", "objective_id", "objective_family",
            "magnification_x", "component_id", "beam_angle_deg", "target_position", "illumination_voltage_v")}
    base.update(exposure_us=prep["exposure_us"], focus_position_mm=prep["focus_position_mm"], focus_policy="local_best")
    output = run/"analysis"/uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    (output/"curves").mkdir()
    frame_rows, movement_rows = [], []
    manifests = [p for p in sorted((run/"measurements").glob("m*/attempt_*/capture_manifest.json"))
                 if not p.parent.name.endswith(".pending")]
    if not manifests:
        raise ValueError("No committed captures")
    sources = {}
    seen_indices = set()
    seen_timestamps = set()
    for path in manifests:
        manifest = verify_capture(path, context["frames_per_measurement"])
        index = manifest["measurement_index"]
        if index in seen_indices or not 1 <= index <= context["measurement_count"]:
            raise ValueError("Duplicate or out-of-range measurement index")
        seen_indices.add(index)
        sources[str(path.relative_to(run))] = digest(path)
        if manifest["condition_hash"] != context["condition_hash"]:
            raise ValueError("Condition hash mismatch")
        stack = np.load(path.parent/manifest["raw_stack"], mmap_mode="r", allow_pickle=False)
        config = MTFConfig(**manifest["analysis_config"])
        config.debug_export_dir = None
        config.debug_export_csv = config.debug_export_png = False
        analyzer = MTFAnalyzer(config)
        x,y,w,h = manifest["edge_bbox_in_stack"]
        origin = manifest["stack_origin"]
        valid = []
        curves = {}
        with (path.parent/"frames.csv").open() as handle:
            timestamps = list(csv.DictReader(handle))
        current_timestamps = {int(row["source_timestamp_ns"]) for row in timestamps}
        if seen_timestamps & current_timestamps:
            raise ValueError("Duplicate source timestamps across measurements")
        seen_timestamps.update(current_timestamps)
        for i,image in enumerate(stack):
            if manifest.get("mtf_roi_mode") == "roi_search_square4":
                recorded = manifest.get("frame_analysis", [])
                edge_defs = recorded[i].get("edges", []) if i < len(recorded) else []
                edge_results = []
                for edge_index, edge in enumerate(edge_defs):
                    gx, gy, ew, eh = [int(value) for value in edge.get("bbox", ())]
                    lx, ly = gx - int(origin[0]), gy - int(origin[1])
                    edge_result = analyzer.compute_mtf(
                        image[ly:ly+eh, lx:lx+ew], roi_origin=(gx, gy)
                    )
                    edge_results.append(edge_result)
                    edge_name = str(edge.get("edge_name", f"edge_{edge_index + 1}"))
                    for key in ("frequencies", "mtf_values", "mtf_raw", "esf_raw", "esf", "lsf",
                                "frequencies_alt", "mtf_raw_alt", "mtf_used_alt"):
                        curves[f"frame_{i+1:03d}_{edge_name}_{key}"] = np.asarray(
                            getattr(edge_result, key)
                        )
                valid_edges = [edge for edge in edge_results if edge.valid]

                def edge_mean(name):
                    values = [float(getattr(edge, name)) for edge in valid_edges]
                    return float(np.mean(values)) if values else 0.0

                frame_valid = len(edge_results) == 4 and len(valid_edges) == 4
                result = MTFResult(
                    valid=frame_valid,
                    mtf50=edge_mean("mtf50"), mtf20=edge_mean("mtf20"),
                    mtf10=edge_mean("mtf10"), edge_angle=edge_mean("edge_angle"),
                    contrast=edge_mean("contrast"), mtf_peak_raw=edge_mean("mtf_peak_raw"),
                    g1_mtf50=edge_mean("g1_mtf50"), g2_mtf50=edge_mean("g2_mtf50"),
                    g1_g2_delta_pct=edge_mean("g1_g2_delta_pct"),
                    warning_msg="; ".join(
                        edge.warning_msg for edge in edge_results if edge.warning_msg
                    ),
                    error_msg=(
                        "" if frame_valid else
                        f"offline measure_mtf_roi valid edges {len(valid_edges)}/{len(edge_results)} (expected 4/4)"
                    ),
                )
                edges_valid = len(valid_edges)
                edges_total = len(edge_results)
            else:
                result = analyzer.compute_mtf(
                    image[y:y+h,x:x+w], roi_origin=(origin[0]+x,origin[1]+y)
                )
                edges_valid = int(bool(result.valid))
                edges_total = 1
                for key in ("frequencies","mtf_values","mtf_raw","esf_raw","esf","lsf",
                            "frequencies_alt","mtf_raw_alt","mtf_used_alt"):
                    curves[f"frame_{i+1:03d}_{key}"] = np.asarray(getattr(result,key))
            row = {**base, "run_id": context["run_id"], "condition_id": context["condition_id"],
                   "setup_id": context["setup_id"], "measurement_index": manifest["measurement_index"],
                   "attempt_index": manifest["attempt_index"], "frame_index": i+1,
                   "valid": bool(result.valid), "mtf50_image_lpmm": float(result.mtf50) if result.valid else "",
                   "mtf20_image_lpmm": float(result.mtf20) if result.valid else "",
                   "mtf10_image_lpmm": float(result.mtf10) if result.valid else "",
                   "source_timestamp_ns": timestamps[i]["source_timestamp_ns"],
                   "edge_angle_deg": float(result.edge_angle), "error": result.error_msg or "",
                   "sop_angle_3_to_10_ok": bool(result.valid and 3 <= abs(result.edge_angle) <= 10),
                   "warning": result.warning_msg or "",
                   "contrast": float(result.contrast), "mtf_peak_raw":float(result.mtf_peak_raw),
                   "g1_mtf50_image_lpmm":float(result.g1_mtf50),
                   "g2_mtf50_image_lpmm":float(result.g2_mtf50),
                   "g1_g2_delta_pct":float(result.g1_g2_delta_pct),
                   "edges_valid": edges_valid, "edges_total": edges_total,
                   "mtf_roi_mode": manifest.get("mtf_roi_mode", "legacy_direct"),
                   "quality_flags": ";".join(manifest["quality_flags"])}
            frame_rows.append(row)
            if result.valid:
                valid.append(result)
        np.savez_compressed(output/"curves"/f"m{index:03d}.npz",**curves)
        statistics = {}
        for metric in ("mtf50", "mtf20", "mtf10"):
            values = [float(getattr(result,metric)) for result in valid]
            statistics[f"{metric}_image_lpmm_median"] = float(np.median(values)) if values else ""
            statistics[f"{metric}_image_lpmm_std"] = float(np.std(values,ddof=1)) if len(values)>1 else ""
        movement_rows.append({**base, "run_id": context["run_id"], "condition_id": context["condition_id"],
                              "measurement_index": manifest["measurement_index"], "valid_frames": len(valid),
                              "stored_frames": len(stack),
                              **statistics,
                              "quality_flags": ";".join(manifest["quality_flags"])})
    atomic_text(output/"frame_results.csv", csv_text(frame_rows))
    atomic_text(output/"measurement_results.csv", csv_text(movement_rows))
    medians = [row["mtf50_image_lpmm_median"] for row in movement_rows if row["valid_frames"]]
    summary = {**base, "run_id": context["run_id"], "condition_id": context["condition_id"],
               "completed_measurements": len(movement_rows), "planned_measurements": context["measurement_count"],
               "valid_measurements": len(medians), "stored_frames": len(frame_rows),
               "valid_frames": sum(r["valid"] for r in frame_rows),
               "mtf50_image_lpmm_mean_of_measurement_medians": float(np.mean(medians)) if medians else None,
               "mtf50_image_lpmm_between_measurement_std": float(np.std(medians,ddof=1)) if len(medians)>1 else None,
               "quality_flagged_measurements": sum(bool(r["quality_flags"]) for r in movement_rows)}
    for metric in ("mtf20", "mtf10"):
        values = [r[f"{metric}_image_lpmm_median"] for r in movement_rows if r["valid_frames"]]
        summary[f"{metric}_image_lpmm_mean_of_measurement_medians"] = float(np.mean(values)) if values else None
        summary[f"{metric}_image_lpmm_between_measurement_std"] = float(np.std(values,ddof=1)) if len(values)>1 else None
    atomic_text(output/"series_summary.csv", csv_text([summary]))
    atomic_json(output/"analysis_manifest.json", {"schema_version":1, "timestamp_utc":utc_now(),
        "analysis_id":output.name, "capture_manifests_sha256": sources,
        "analysis_config": asdict(config), "condition_hash":context["condition_hash"],
        "method":"per-frame MTF; median per axis repetition; no best-frame selection",
        "frequency_space":"image", "magnification_x_nominal":context["magnification_x"],
        "analyzer_source_sha256": {p.name:digest(p) for p in (Path(__file__).parent/"algorithms"/"mtf").glob("*.py")},
        "numpy_version":np.__version__, "summary":summary})
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run")
    group.add_argument("--campaign", help="Analyze every prepared run and write a versioned campaign index")
    group.add_argument("--summary", help="Report an existing online summary without raw reanalysis")
    group.add_argument("--compare", nargs="+", metavar="PATH",
                       help="Compare online summaries; the first run is the reference")
    parser.add_argument("--output-dir", help="Report output directory for --summary/--compare")
    parser.add_argument("--show", action="store_true", help="Show the generated report interactively")
    args = parser.parse_args(argv)
    if args.run:
        print(analyze_run(args.run))
    elif args.summary:
        print(report_online_runs([args.summary], args.output_dir, args.show))
    elif args.compare:
        print(report_online_runs(args.compare, args.output_dir, args.show))
    else:
        campaign = Path(args.campaign)
        output = campaign/"analysis"/uuid.uuid4().hex
        output.mkdir(parents=True, exist_ok=False)
        rows, errors = [], []
        for path in sorted((campaign/"runs").glob("*/resolved_condition.yaml")):
            try:
                analysis = analyze_run(path.parent)
                with (analysis/"series_summary.csv").open() as handle:
                    for row in csv.DictReader(handle):
                        rows.append({**row,"analysis_directory":str(analysis)})
            except Exception as exc:
                errors.append({"run":str(path.parent),"error":str(exc)})
        atomic_text(output/"campaign_summary.csv",csv_text(rows))
        atomic_json(output/"errors.json",errors)
        print(output)
        if errors or not rows:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
