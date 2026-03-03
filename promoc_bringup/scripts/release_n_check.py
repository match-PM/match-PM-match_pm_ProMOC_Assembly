#!/usr/bin/env python3
"""Automated acceptance checks for Release N migration state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import sys


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _read_text(root: Path, rel_path: str) -> str:
    path = root / rel_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _contains_all(content: str, needles: list[str]) -> tuple[bool, list[str]]:
    missing = [needle for needle in needles if needle not in content]
    return len(missing) == 0, missing


def _check_file_exists(root: Path, rel_path: str, name: str) -> CheckResult:
    exists = (root / rel_path).exists()
    return CheckResult(name=name, ok=exists, detail=rel_path if not exists else "")


def _check_contains(
    root: Path, rel_path: str, needles: list[str], name: str
) -> CheckResult:
    content = _read_text(root, rel_path)
    ok, missing = _contains_all(content, needles)
    detail = "" if ok else f"{rel_path}: missing {missing}"
    return CheckResult(name=name, ok=ok, detail=detail)


def _evaluate(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    # Launch/API
    results.append(
        _check_contains(
            root,
            "promoc_bringup/launch/system.launch.py",
            ["runtime_mode", "sim_mode", "Deprecated launch argument"],
            "system.launch supports runtime_mode + legacy sim_mode",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/launch/camera.launch.py",
            ["runtime_mode", "sim_mode", "use_simulator", "Deprecated launch argument"],
            "camera.launch supports runtime_mode + legacy aliases",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/launch/optical_measurement_system.launch.py",
            ["runtime_mode", "sim_mode", "use_simulator", "Deprecated launch argument"],
            "optical_measurement_system.launch supports runtime_mode + legacy aliases",
        )
    )

    # Canonical/legacy services
    results.append(
        _check_contains(
            root,
            "camera_nodes/camera_nodes/camera_node.py",
            [
                "/promoc/camera/autofocus",
                "/promoc/camera/measure_mtf",
                "/promoc/camera/detect_rois",
                "/promoc/camera_node/autofocus",
                "/promoc/camera_node/measure_mtf",
                "/promoc/camera_node/detect_rois",
            ],
            "camera services expose canonical + legacy paths",
        )
    )
    results.append(
        _check_contains(
            root,
            "linear_axis_nodes/linear_axis_nodes/lts300_node.py",
            ["/promoc/linear_axis/", "legacy_path = f", "register_service_alias_pair"],
            "linear-axis services expose canonical + legacy paths",
        )
    )
    results.append(
        _check_contains(
            root,
            "planar_motor_nodes/planar_motor_nodes/mover_node.py",
            ["/promoc/mover/", "legacy_path = f", "register_service_alias_pair"],
            "mover services expose canonical + legacy paths",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_core/promoc_core/service_alias.py",
            ["register_service_alias_pair", "Deprecated service"],
            "shared service alias helper provides legacy deprecation warning",
        )
    )

    # Config compatibility
    results.append(
        _check_file_exists(
            root,
            "promoc_bringup/config/user_config.v2.example.yaml",
            "user config v2 example exists",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/promoc_bringup/launch_utils.py",
            [
                "runtime.mode",
                "measurement.operator",
                "measurement.base_path",
                "legacy key 'user.*'",
                "camera.mtf_csv_path",
            ],
            "launch_utils supports canonical + legacy config schema",
        )
    )

    # Tooling + quality wiring
    results.append(
        _check_contains(
            root,
            "requirements-dev.txt",
            ["pytest", "ruff", "mypy"],
            "requirements-dev includes lint/test tooling",
        )
    )
    results.append(
        _check_contains(
            root,
            "Makefile",
            ["release-n-check", "check: lint test-unit release-n-check"],
            "Makefile wires release-n-check into make check",
        )
    )
    results.append(
        _check_contains(
            root,
            ".github/workflows/check.yml",
            ["ros_distro: [humble, jazzy]", "make check"],
            "CI matrix includes humble + jazzy and runs make check",
        )
    )

    # Documentation
    results.append(
        _check_contains(
            root,
            "START_HERE.md",
            ["make hw", "make sim", "runtime_mode:=hardware|sim"],
            "START_HERE documents hardware-first and sim-first flows",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "docs/learning_path_de.md",
            "DE learning path exists",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "docs/learning_path_en.md",
            "EN learning path exists",
        )
    )
    results.append(
        _check_contains(
            root,
            "camera_nodes/docs/callbacks_user_guide_de.md",
            ["/promoc/camera/autofocus", "/promoc/camera/measure_mtf"],
            "DE callback guide uses canonical camera services",
        )
    )
    results.append(
        _check_contains(
            root,
            "camera_nodes/docs/callbacks_user_guide_en.md",
            ["/promoc/camera/autofocus", "/promoc/camera/measure_mtf"],
            "EN callback guide uses canonical camera services",
        )
    )
    results.append(
        _check_contains(
            root,
            "MIGRATION_NOTES.md",
            ["Launch Arguments", "Service Namespaces", "Config Schema", "Release N+1"],
            "migration notes include key migration sections",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/scripts/release_n_smoke.py",
            ["SMOKE_PATHS", "sim", "hardware", "/promoc/camera/autofocus"],
            "release-n smoke script exists for sim and hardware paths",
        )
    )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run automated Release N acceptance checks."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print summary and failed checks.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    results = _evaluate(root)

    passed = [result for result in results if result.ok]
    failed = [result for result in results if not result.ok]

    if not args.quiet:
        for result in results:
            prefix = "PASS" if result.ok else "FAIL"
            print(f"[{prefix}] {result.name}")
            if result.detail and not result.ok:
                print(f"       {result.detail}")
    else:
        for result in failed:
            print(f"[FAIL] {result.name}")
            if result.detail:
                print(f"       {result.detail}")

    print(f"Release N check summary: {len(passed)} passed, {len(failed)} failed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
