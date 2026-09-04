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


def analyze_run(run_path):
    from .algorithms.mtf import MTFAnalyzer, MTFConfig
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
            result = analyzer.compute_mtf(image[y:y+h,x:x+w], roi_origin=(origin[0]+x,origin[1]+y))
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
    args = parser.parse_args(argv)
    if args.run:
        print(analyze_run(args.run))
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
