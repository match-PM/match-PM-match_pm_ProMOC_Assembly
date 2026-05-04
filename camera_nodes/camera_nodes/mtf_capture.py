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
        "stack_origin_x",
        "stack_origin_y",
        "stack_bbox_w",
        "stack_bbox_h",
        "sample_count",
        "dtype",
        "stack_file",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for edge in edge_entries:
            bbox = edge.get("bbox", [0, 0, 0, 0])
            stack_bbox = edge.get("stack_bbox", bbox)
            writer.writerow(
                {
                    "edge_label": edge.get("edge_label", ""),
                    "edge_name": edge.get("edge_name", ""),
                    "edge_direction": edge.get("edge_direction", ""),
                    "roi_bbox_x": int(bbox[0]),
                    "roi_bbox_y": int(bbox[1]),
                    "roi_bbox_w": int(bbox[2]),
                    "roi_bbox_h": int(bbox[3]),
                    "stack_origin_x": int(stack_bbox[0]),
                    "stack_origin_y": int(stack_bbox[1]),
                    "stack_bbox_w": int(stack_bbox[2]),
                    "stack_bbox_h": int(stack_bbox[3]),
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


def _stack_origin_from_manifest(edge_entry: dict[str, Any]) -> tuple[int, int] | None:
    """Return absolute origin of a stored context stack when available."""
    stack_origin = edge_entry.get("stack_origin")
    if isinstance(stack_origin, (list, tuple)) and len(stack_origin) >= 2:
        return int(stack_origin[0]), int(stack_origin[1])
    stack_bbox = edge_entry.get("stack_bbox")
    if isinstance(stack_bbox, (list, tuple)) and len(stack_bbox) >= 2:
        return int(stack_bbox[0]), int(stack_bbox[1])
    return None


def _bbox_from_manifest(
    edge_entry: dict[str, Any],
    key: str,
    fallback: list[int] | tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    values = edge_entry.get(key, fallback)
    if not isinstance(values, (list, tuple)) or len(values) < 4:
        values = fallback
    return tuple(int(value) for value in values[:4])


def _preview_from_raw(image: np.ndarray) -> np.ndarray:
    """Return a readable BGR preview for raw/grayscale stack samples."""
    if image.ndim == 3:
        preview = image.copy()
    else:
        normalized = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
        preview = cv2.cvtColor(normalized.astype(np.uint8), cv2.COLOR_GRAY2BGR)
    return preview


def _scale_preview_for_review(
    preview: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    *,
    min_width: int = 720,
    min_height: int = 420,
) -> tuple[np.ndarray, list[tuple[int, int, int, int]], float]:
    """Upscale small ROI previews so labels and edge boxes are inspectable."""
    height, width = preview.shape[:2]
    scale = max(1.0, min_width / max(1, width), min_height / max(1, height))
    if scale <= 1.0:
        return preview, boxes, 1.0

    scaled = cv2.resize(
        preview,
        (int(round(width * scale)), int(round(height * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    scaled_boxes = [
        (
            int(round(x * scale)),
            int(round(y * scale)),
            int(round(w * scale)),
            int(round(h * scale)),
        )
        for x, y, w, h in boxes
    ]
    return scaled, scaled_boxes, scale


def _draw_review_label(
    image: np.ndarray,
    lines: list[str],
    *,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw compact high-contrast review text in the top-left corner."""
    if not lines:
        return
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness = 1
    line_height = 22
    width = 0
    for line in lines:
        size, _baseline = cv2.getTextSize(line, font, font_scale, thickness)
        width = max(width, int(size[0]))
    height = line_height * len(lines) + 10
    cv2.rectangle(image, (0, 0), (width + 14, height), (0, 0, 0), -1)
    for index, line in enumerate(lines):
        cv2.putText(
            image,
            line,
            (7, 18 + index * line_height),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )


def _write_offline_roi_review_png(
    run_dir: Path,
    edge_label: str,
    sample: np.ndarray,
    edge_entry: dict[str, Any],
    row: dict[str, object],
) -> None:
    """Overwrite per-edge ROI PNG with a readable offline review preview."""
    try:
        preview = _preview_from_raw(sample)
        edge_bbox = _bbox_from_manifest(edge_entry, "bbox", [0, 0, sample.shape[1], sample.shape[0]])
        analysis_bounds = (
            int(row.get("analysis_roi_x", 0) or 0),
            int(row.get("analysis_roi_y", 0) or 0),
            int(row.get("analysis_roi_w", 0) or 0),
            int(row.get("analysis_roi_h", 0) or 0),
        )
        stack_origin = _stack_origin_from_manifest(edge_entry) or edge_bbox[:2]
        analysis_local = (
            analysis_bounds[0] - stack_origin[0],
            analysis_bounds[1] - stack_origin[1],
            analysis_bounds[2],
            analysis_bounds[3],
        )
        if analysis_local[2] <= 0 or analysis_local[3] <= 0:
            analysis_local = _bbox_from_manifest(
                edge_entry,
                "edge_bbox_in_stack",
                [0, 0, edge_bbox[2], edge_bbox[3]],
            )

        boxes = [analysis_local]
        preview, boxes, _scale = _scale_preview_for_review(preview, boxes)
        box_color = (255, 180, 0) if int(row.get("valid", 0) or 0) else (0, 0, 255)
        ax, ay, aw, ah = boxes[0]
        cv2.rectangle(preview, (ax, ay), (ax + aw, ay + ah), box_color, 2)

        valid_samples = int(row.get("valid_sample_count", row.get("sample_count", 0)) or 0)
        stored_samples = int(row.get("stored_sample_count", valid_samples) or 0)
        status = "valid" if int(row.get("valid", 0) or 0) else "invalid"
        lines = [
            f"{edge_label}  {status}  samples={valid_samples}/{stored_samples}",
            f"angle={float(row.get('edge_angle_deg', 0.0) or 0.0):.2f}deg  "
            f"MTF50={float(row.get('mtf50_lpmm', 0.0) or 0.0):.2f}",
        ]
        reason = str(row.get("official_sop_reason", "") or row.get("error_msg", "") or "")
        if reason:
            lines.append(reason[:90])
        _draw_review_label(preview, lines)
        cv2.imwrite(str(run_dir / f"{edge_label}_roi.png"), preview)
    except Exception:
        return


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


def _edge_matches_target(edge_entry: dict[str, Any], target_edge: str) -> bool:
    """Return true when a manifest edge matches a requested target edge label."""
    target = str(target_edge or "").strip().lower()
    if not target or target in {"any", "first-valid", "first_valid"}:
        return True

    labels = {
        str(edge_entry.get("edge_label", "") or "").strip().lower(),
        str(edge_entry.get("edge_name", "") or "").strip().lower(),
        str(edge_entry.get("edge_direction", "") or "").strip().lower(),
    }
    labels.update(label.split("_")[-1] for label in list(labels) if label)
    return target in labels


def analyze_capture_manifest(
    manifest_path: Path,
    *,
    overwrite: bool = False,
    target_edge: str = "",
    min_valid_edges: int = 1,
    analysis_max_edge_angle: float = 11.0,
) -> dict[str, Any]:
    """Analyze one capture-only run and rewrite final MTF exports."""
    manifest_path = manifest_path.resolve()
    run_dir = manifest_path.parent
    manifest = read_capture_manifest(manifest_path)
    if not overwrite and (run_dir / "selected_edge.txt").exists():
        return {"run_dir": run_dir, "skipped": True, "reason": "already analyzed"}
    if overwrite:
        selected_marker = run_dir / "selected_edge.txt"
        if selected_marker.exists():
            selected_marker.unlink()

    edge_rows: list[dict[str, object]] = []
    selected_edge_label = ""
    selected_result: MTFResult | None = None
    selected_samples: list[MTFResult] = []
    selected_avg_angle: float | None = None
    last_error = ""
    target_edge = str(target_edge or "").strip()
    min_valid_edges = max(1, int(min_valid_edges))
    analysis_max_edge_angle = float(analysis_max_edge_angle)

    for edge_entry in manifest.get("edges", []):
        stack_path = run_dir / str(edge_entry.get("stack_file", ""))
        stack = np.load(stack_path)
        if stack.ndim < 3 or stack.shape[0] == 0:
            last_error = f"empty ROI stack for {edge_entry.get('edge_label', '')}"
            continue

        edge_label = str(edge_entry.get("edge_label", "") or "edge")
        stored_sample_count = int(edge_entry.get("sample_count", 0) or stack.shape[0])
        config = config_from_manifest_dict(edge_entry.get("mtf_config", {}), run_dir)
        config.max_edge_angle = max(float(config.max_edge_angle), analysis_max_edge_angle)
        config.debug_export_prefix = str(manifest.get("run_id", "") or "mtf")
        analyzer = MTFAnalyzer(config)
        valid_samples: list[MTFResult] = []
        row_result: MTFResult | None = None
        debug_exported = False
        stack_origin = _stack_origin_from_manifest(edge_entry)

        for sample_index, sample in enumerate(stack):
            edge_roi = edge_roi_from_manifest(edge_entry, sample)
            analyzer.config.debug_export_dir = (
                str(run_dir) if not debug_exported else None
            )
            analyzer.config.debug_export_csv = not debug_exported
            analyzer.config.debug_export_png = not debug_exported
            result = analyzer.compute_mtf(
                sample,
                roi_origin=(
                    stack_origin if stack_origin is not None else edge_roi.bbox[:2]
                ),
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
            stored_sample_count=stored_sample_count,
        )
        _write_offline_roi_review_png(
            run_dir,
            edge_label,
            stack[0],
            edge_entry,
            row,
        )
        edge_rows.append(row)

        if (
            valid_samples
            and not selected_edge_label
            and _edge_matches_target(edge_entry, target_edge)
        ):
            selected_edge_label = edge_label
            selected_result = row_result
            selected_samples = valid_samples
            selected_avg_angle = _mean_result_attr(valid_samples, "edge_angle")

    valid_edge_count = sum(int(bool(row["valid"])) for row in edge_rows)
    measurement_success = bool(selected_edge_label) and valid_edge_count >= min_valid_edges
    if not measurement_success and selected_edge_label:
        last_error = (
            f"only {valid_edge_count}/{len(edge_rows)} valid edges; "
            f"minimum required is {min_valid_edges}"
        )
    elif not measurement_success and target_edge:
        last_error = f"target edge '{target_edge}' has no valid samples"

    for row in edge_rows:
        row["selected_for_response"] = int(
            measurement_success and row["edge_label"] == selected_edge_label
        )

    summary_csv = write_summary_csv(run_dir, edge_rows)
    measurement_metadata = dict(manifest.get("measurement_metadata", {}))
    capture_values = dict(manifest.get("capture_values", {}))
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
            measurement_success=measurement_success,
            measurement_error="" if measurement_success else last_error,
        ),
    )
    if measurement_success:
        write_selected_edge_marker(run_dir, selected_edge_label)

    selected_row = next(
        (row for row in edge_rows if row["edge_label"] == selected_edge_label),
        {},
    )

    return {
        "run_dir": run_dir,
        "summary_csv": summary_csv,
        "context_csv": context_csv,
        "selected_edge_label": selected_edge_label if measurement_success else "",
        "selected_mtf50_lpmm": selected_row.get("mtf50_lpmm", ""),
        "selected_mtf20_lpmm": selected_row.get("mtf20_lpmm", ""),
        "selected_mtf10_lpmm": selected_row.get("mtf10_lpmm", ""),
        "selected_sample_count": len(selected_samples) if measurement_success else 0,
        "valid_edge_count": valid_edge_count,
        "edge_count": len(edge_rows),
        "measurement_success": measurement_success,
        "measurement_error": "" if measurement_success else last_error,
        "skipped": False,
    }


def write_preview_png(path: Path, image: np.ndarray) -> None:
    """Best-effort preview image write."""
    try:
        cv2.imwrite(str(path), image)
    except Exception:
        return
