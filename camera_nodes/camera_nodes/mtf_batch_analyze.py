"""Command line entry point for offline MTF analysis of capture-only runs."""

from __future__ import annotations

import argparse
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    manifests = find_capture_manifests(input_path, recursive=bool(args.recursive))
    if not manifests:
        parser.error(f"no capture manifests found below {input_path}")

    exit_code = 0
    for manifest_path in manifests:
        try:
            result = analyze_capture_manifest(
                manifest_path,
                overwrite=bool(args.overwrite),
            )
        except Exception as exc:
            exit_code = 1
            print(f"FAILED {manifest_path}: {exc}", file=sys.stderr)
            continue

        if result.get("skipped"):
            print(f"SKIP {result['run_dir']}: {result.get('reason', '')}")
            continue
        print(
            "OK "
            f"{result['run_dir']}: "
            f"valid_edges={result['valid_edge_count']}/{result['edge_count']}, "
            f"selected={result.get('selected_edge_label', '') or 'none'}, "
            f"summary={result['summary_csv']}"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
