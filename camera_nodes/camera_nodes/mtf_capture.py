"""Capture-only persistence and offline MTF batch analysis helpers."""

from __future__ import annotations

import csv
from dataclasses import asdict, fields
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .algorithms.mtf import MTFAnalyzer, MTFConfig, MTFResult
from .algorithms.roi_detection import EdgeROI
from .services.mtf_export import (
    build_context_row,
    build_edge_summary_row,
    write_context_csv,
    write_selected_edge_marker,
    write_summary_csv,
)


CAPTURE_MANIFEST_NAME = "capture_manifest.json"
CAPTURE_INDEX_NAME = "capture_index.csv"


def _json_default(value: Any) -> Any:
    """Convert numpy-heavy metadata into JSON-safe values."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def config_to_manifest_dict(config: MTFConfig) -> dict[str, Any]:
    """Return a JSON-safe MTFConfig snapshot."""
    data = asdict(config)
    data["debug_export_dir"] = None
    return data


def config_from_manifest_dict(data: dict[str, Any], run_dir: Path) -> MTFConfig:
    """Rebuild an MTFConfig from a capture manifest."""
    field_names = {field.name for field in fields(MTFConfig)}
    kwargs = {
        key: value
        for key, value in dict(data or {}).items()
        if key in field_names
    }
    config = MTFConfig(**kwargs)
    config.debug_export_dir = str(run_dir)
    config.debug_export_csv = True
    config.debug_export_png = True
    return config


def write_capture_manifest(run_dir: Path, manifest: dict[str, Any]) -> Path:
    """Write one capture manifest JSON file."""
    path = run_dir / CAPTURE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return path


def read_capture_manifest(path: Path) -> dict[str, Any]:
    """Read a capture manifest from a file or run directory."""
    manifest_path = path / CAPTURE_MANIFEST_NAME if path.is_dir() else path
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def write_capture_index(run_dir: Path, edge_entries: list[dict[str, Any]]) -> Path:
    """Write a compact CSV index of stored ROI stacks."""
    path = run_dir / CAPTURE_INDEX_NAME
    fieldnames = [
        "edge_label",
        "edge_name",
        "edge_direction",
        "roi_bbox_x",
        "roi_bbox_y",
        "roi_bbox_w",
        "roi_bbox_h",
        "sample_count",
        "dtype",
        "stack_file",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for edge in edge_entries:
            bbox = edge.get("bbox", [0, 0, 0, 0])
            writer.writerow(
                {
                    "edge_label": edge.get("edge_label", ""),
                    "edge_name": edge.get("edge_name", ""),
                    "edge_direction": edge.get("edge_direction", ""),
                    "roi_bbox_x": int(bbox[0]),
                    "roi_bbox_y": int(bbox[1]),
                    "roi_bbox_w": int(bbox[2]),
                    "roi_bbox_h": int(bbox[3]),
                    "sample_count": int(edge.get("sample_count", 0) or 0),
                    "dtype": edge.get("dtype", ""),
                    "stack_file": edge.get("stack_file", ""),
                }
            )
    return path


def find_capture_manifests(input_path: Path, recursive: bool) -> list[Path]:
    """Find capture manifests below one file or directory."""
    input_path = input_path.resolve()
    if input_path.is_file():
        return [input_path] if input_path.name == CAPTURE_MANIFEST_NAME else []
    if not input_path.is_dir():
        return []
    direct = input_path / CAPTURE_MANIFEST_NAME
    if direct.exists():
        return [direct]
    pattern = f"**/{CAPTURE_MANIFEST_NAME}" if recursive else CAPTURE_MANIFEST_NAME
    return sorted(input_path.glob(pattern))


def edge_roi_from_manifest(edge_entry: dict[str, Any], image: np.ndarray) -> EdgeROI:
    """Rebuild an EdgeROI using manifest metadata and one sample image."""
    bbox = tuple(int(value) for value in edge_entry.get("bbox", [0, 0, 0, 0]))
    parent_center = tuple(
        int(value) for value in edge_entry.get("parent_center", [0, 0])
    )
    return EdgeROI(
        image=image,
        bbox=bbox,
        edge_direction=str(edge_entry.get("edge_direction", "") or ""),
        edge_name=str(edge_entry.get("edge_name", "") or ""),
        contrast=float(edge_entry.get("contrast", 0.0) or 0.0),
        parent_center=parent_center,
    )


def _annotate_result(result: MTFResult, edge_roi: EdgeROI) -> MTFResult:
    """Attach edge traceability to one analyzer result."""
    result.edge_name = edge_roi.edge_name
    result.edge_direction = edge_roi.edge_direction
    result.contrast = edge_roi.contrast
    result.roi_bounds = edge_roi.bbox
    return result


def _mean_result_attr(samples: list[MTFResult], attr_name: str) -> float:
    if not samples:
        return 0.0
    values = [
        float(getattr(sample, attr_name, 0.0) or 0.0)
        for sample in samples
    ]
    return float(np.mean(values))


def analyze_capture_manifest(
    manifest_path: Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Analyze one capture-only run and rewrite final MTF exports."""
    manifest_path = manifest_path.resolve()
    run_dir = manifest_path.parent
    manifest = read_capture_manifest(manifest_path)
    if not overwrite and (run_dir / "selected_edge.txt").exists():
        return {"run_dir": run_dir, "skipped": True, "reason": "already analyzed"}

    edge_rows: list[dict[str, object]] = []
    selected_edge_label = ""
    selected_result: MTFResult | None = None
    selected_samples: list[MTFResult] = []
    selected_avg_angle: float | None = None
    last_error = ""

    for edge_entry in manifest.get("edges", []):
        stack_path = run_dir / str(edge_entry.get("stack_file", ""))
        stack = np.load(stack_path)
        if stack.ndim < 3 or stack.shape[0] == 0:
            last_error = f"empty ROI stack for {edge_entry.get('edge_label', '')}"
            continue

        edge_label = str(edge_entry.get("edge_label", "") or "edge")
        config = config_from_manifest_dict(edge_entry.get("mtf_config", {}), run_dir)
        config.debug_export_prefix = str(manifest.get("run_id", "") or "mtf")
        analyzer = MTFAnalyzer(config)
        valid_samples: list[MTFResult] = []
        row_result: MTFResult | None = None
        debug_exported = False

        for sample_index, sample in enumerate(stack):
            edge_roi = edge_roi_from_manifest(edge_entry, sample)
            analyzer.config.debug_export_dir = (
                str(run_dir) if not debug_exported else None
            )
            analyzer.config.debug_export_csv = not debug_exported
            analyzer.config.debug_export_png = not debug_exported
            result = analyzer.compute_mtf(
                sample,
                roi_origin=edge_roi.bbox[:2],
                debug_label=edge_label,
            )
            _annotate_result(result, edge_roi)
            if row_result is None:
                row_result = result
            if result.valid:
                valid_samples.append(result)
                if not debug_exported:
                    row_result = result
                    debug_exported = True
            elif result.error_msg:
                last_error = str(result.error_msg)

            if sample_index == 0 and not result.valid and not result.error_msg:
                last_error = f"invalid first sample for {edge_label}"

        if row_result is None:
            edge_roi = edge_roi_from_manifest(edge_entry, stack[0])
            row_result = _annotate_result(
                MTFResult(valid=False, error_msg="empty ROI stack"),
                edge_roi,
            )

        edge_roi = edge_roi_from_manifest(edge_entry, stack[0])
        row = build_edge_summary_row(
            run_id=str(manifest.get("run_id", "")),
            edge_label=edge_label,
            edge_roi=edge_roi,
            result=row_result,
            valid_samples=valid_samples,
            selected_for_response=False,
        )
        edge_rows.append(row)

        if valid_samples and not selected_edge_label:
            selected_edge_label = edge_label
            selected_result = row_result
            selected_samples = valid_samples
            selected_avg_angle = _mean_result_attr(valid_samples, "edge_angle")

    for row in edge_rows:
        row["selected_for_response"] = int(row["edge_label"] == selected_edge_label)

    summary_csv = write_summary_csv(run_dir, edge_rows)
    measurement_metadata = dict(manifest.get("measurement_metadata", {}))
    capture_values = dict(manifest.get("capture_values", {}))
    valid_edge_count = sum(int(bool(row["valid"])) for row in edge_rows)
    context_csv = write_context_csv(
        run_dir,
        build_context_row(
            run_id=str(manifest.get("run_id", "")),
            timestamp=str(manifest.get("timestamp", "")),
            measurement_metadata=measurement_metadata,
            roi_mode=str(manifest.get("roi_mode", "")),
            focus_position_mm=manifest.get("focus_position_mm"),
            capture_values=capture_values,
            capture_available_keys=list(manifest.get("capture_available_keys", [])),
            capture_readback_mismatches=list(manifest.get("capture_mismatches", [])),
            capture_readback_ok=not bool(manifest.get("capture_mismatches", [])),
            image_encoding=str(manifest.get("image_encoding", "")),
            edge_count=len(edge_rows),
            valid_edge_count=valid_edge_count,
            selected_edge_label=selected_edge_label,
            selected_result=selected_result,
            selected_edge_angle_deg=selected_avg_angle,
            selected_sample_count=len(selected_samples),
            measurement_success=bool(selected_edge_label),
            measurement_error="" if selected_edge_label else last_error,
        ),
    )
    if selected_edge_label:
        write_selected_edge_marker(run_dir, selected_edge_label)

    return {
        "run_dir": run_dir,
        "summary_csv": summary_csv,
        "context_csv": context_csv,
        "selected_edge_label": selected_edge_label,
        "valid_edge_count": valid_edge_count,
        "edge_count": len(edge_rows),
        "skipped": False,
    }


def write_preview_png(path: Path, image: np.ndarray) -> None:
    """Best-effort preview image write."""
    try:
        cv2.imwrite(str(path), image)
    except Exception:
        return
