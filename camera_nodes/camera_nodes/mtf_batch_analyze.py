"""Command line entry point for offline MTF analysis of capture-only runs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

from .mtf_capture import analyze_capture_manifest, find_capture_manifests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze MTF capture-only run folders without a live ROS camera.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Capture run folder, capture_manifest.json, or parent folder.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search recursively for capture_manifest.json files below --input.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recompute runs that already contain selected_edge.txt.",
    )
    parser.add_argument(
        "--target-edge",
        default="",
        help="Select this edge when valid, e.g. top/right/bottom/left.",
    )
    parser.add_argument(
        "--min-valid-edges",
        type=int,
        default=1,
        help="Minimum valid edges required for a run to count as successful.",
    )
    parser.add_argument(
        "--analysis-max-edge-angle",
        type=float,
        default=11.0,
        help="Technical analyzer max angle; SOP reporting still uses 10 deg.",
    )
    parser.add_argument(
        "--batch-summary",
        default="",
        help="Optional CSV path for a cross-run batch summary.",
    )
    return parser


def _default_batch_summary_path(input_path: Path) -> Path:
    if input_path.is_file():
        return input_path.parent / "batch_summary.csv"
    return input_path / "batch_summary.csv"


def _write_batch_summary(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "run_dir",
        "status",
        "selected_edge_label",
        "valid_edge_count",
        "edge_count",
        "selected_sample_count",
        "selected_mtf50_lpmm",
        "selected_mtf20_lpmm",
        "selected_mtf10_lpmm",
        "summary_csv",
        "error",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    manifests = find_capture_manifests(input_path, recursive=bool(args.recursive))
    if not manifests:
        parser.error(f"no capture manifests found below {input_path}")

    exit_code = 0
    batch_rows: list[dict[str, object]] = []
    for manifest_path in manifests:
        try:
            result = analyze_capture_manifest(
                manifest_path,
                overwrite=bool(args.overwrite),
                target_edge=str(args.target_edge or ""),
                min_valid_edges=int(args.min_valid_edges),
                analysis_max_edge_angle=float(args.analysis_max_edge_angle),
            )
        except Exception as exc:
            exit_code = 1
            print(f"FAILED {manifest_path}: {exc}", file=sys.stderr)
            batch_rows.append(
                {
                    "run_dir": manifest_path.parent,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            continue

        if result.get("skipped"):
            print(f"SKIP {result['run_dir']}: {result.get('reason', '')}")
            batch_rows.append(
                {
                    "run_dir": result["run_dir"],
                    "status": "skipped",
                    "error": result.get("reason", ""),
                }
            )
            continue
        if not result.get("measurement_success", True):
            exit_code = 1
            print(
                "PARTIAL "
                f"{result['run_dir']}: "
                f"valid_edges={result['valid_edge_count']}/{result['edge_count']}, "
                f"error={result.get('measurement_error', '')}, "
                f"summary={result['summary_csv']}"
            )
            status = "partial"
        else:
            print(
                "OK "
                f"{result['run_dir']}: "
                f"valid_edges={result['valid_edge_count']}/{result['edge_count']}, "
                f"selected={result.get('selected_edge_label', '') or 'none'}, "
                f"samples={result.get('selected_sample_count', 0)}, "
                f"mtf50={result.get('selected_mtf50_lpmm', '')}, "
                f"summary={result['summary_csv']}"
            )
            status = "ok"
        batch_rows.append(
            {
                "run_dir": result["run_dir"],
                "status": status,
                "selected_edge_label": result.get("selected_edge_label", ""),
                "valid_edge_count": result.get("valid_edge_count", ""),
                "edge_count": result.get("edge_count", ""),
                "selected_sample_count": result.get("selected_sample_count", ""),
                "selected_mtf50_lpmm": result.get("selected_mtf50_lpmm", ""),
                "selected_mtf20_lpmm": result.get("selected_mtf20_lpmm", ""),
                "selected_mtf10_lpmm": result.get("selected_mtf10_lpmm", ""),
                "summary_csv": result.get("summary_csv", ""),
                "error": result.get("measurement_error", ""),
            }
        )
    if batch_rows:
        summary_path = (
            Path(args.batch_summary)
            if str(args.batch_summary or "").strip()
            else _default_batch_summary_path(input_path)
        )
        _write_batch_summary(summary_path, batch_rows)
        print(f"BATCH summary={summary_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
