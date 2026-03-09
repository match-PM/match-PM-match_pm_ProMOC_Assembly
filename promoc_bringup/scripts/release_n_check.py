#!/usr/bin/env python3
"""Automated acceptance checks for Release N+1 canonical contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
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


def _contains_none(content: str, needles: list[str]) -> tuple[bool, list[str]]:
    present = [needle for needle in needles if needle in content]
    return len(present) == 0, present


def _check_file_exists(root: Path, rel_path: str, name: str) -> CheckResult:
    exists = (root / rel_path).exists()
    return CheckResult(name=name, ok=exists, detail=rel_path if not exists else "")


def _check_file_absent(root: Path, rel_path: str, name: str) -> CheckResult:
    exists = (root / rel_path).exists()
    detail = "" if not exists else f"{rel_path}: should be removed"
    return CheckResult(name=name, ok=not exists, detail=detail)


def _check_contains(
    root: Path, rel_path: str, needles: list[str], name: str
) -> CheckResult:
    content = _read_text(root, rel_path)
    ok, missing = _contains_all(content, needles)
    detail = "" if ok else f"{rel_path}: missing {missing}"
    return CheckResult(name=name, ok=ok, detail=detail)


def _check_not_contains(
    root: Path, rel_path: str, needles: list[str], name: str
) -> CheckResult:
    content = _read_text(root, rel_path)
    ok, present = _contains_none(content, needles)
    detail = "" if ok else f"{rel_path}: unexpected {present}"
    return CheckResult(name=name, ok=ok, detail=detail)


def _declares_launch_argument(content: str, arg_name: str) -> bool:
    pattern = rf"DeclareLaunchArgument\(\s*\"{re.escape(arg_name)}\""
    return re.search(pattern, content) is not None


def _check_no_launch_arg(
    root: Path, rel_path: str, arg_name: str, name: str
) -> CheckResult:
    content = _read_text(root, rel_path)
    ok = not _declares_launch_argument(content, arg_name)
    detail = "" if ok else f"{rel_path}: still declares launch arg '{arg_name}'"
    return CheckResult(name=name, ok=ok, detail=detail)


def _evaluate(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    # Launch API: runtime_mode only
    results.append(
        _check_contains(
            root,
            "promoc_bringup/launch/system.launch.py",
            ["runtime_mode"],
            "system.launch declares runtime_mode",
        )
    )
    results.append(
        _check_no_launch_arg(
            root,
            "promoc_bringup/launch/system.launch.py",
            "sim_mode",
            "system.launch no longer exposes sim_mode",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/launch/camera.launch.py",
            ["runtime_mode"],
            "camera.launch declares runtime_mode",
        )
    )
    results.append(
        _check_no_launch_arg(
            root,
            "promoc_bringup/launch/camera.launch.py",
            "sim_mode",
            "camera.launch no longer exposes sim_mode",
        )
    )
    results.append(
        _check_no_launch_arg(
            root,
            "promoc_bringup/launch/camera.launch.py",
            "use_simulator",
            "camera.launch no longer exposes use_simulator launch arg",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/launch/optical_measurement_system.launch.py",
            ["runtime_mode"],
            "optical launch declares runtime_mode",
        )
    )
    results.append(
        _check_no_launch_arg(
            root,
            "promoc_bringup/launch/optical_measurement_system.launch.py",
            "sim_mode",
            "optical launch no longer exposes sim_mode",
        )
    )
    results.append(
        _check_no_launch_arg(
            root,
            "promoc_bringup/launch/optical_measurement_system.launch.py",
            "use_simulator",
            "optical launch no longer exposes use_simulator launch arg",
        )
    )

    # Launch helper compatibility removal
    results.append(
        _check_not_contains(
            root,
            "promoc_bringup/promoc_bringup/launch_utils.py",
            ["legacy_arg_names", "legacy key 'user.*'", "camera.mtf_csv_path"],
            "launch_utils no longer contains legacy launch/config compatibility",
        )
    )

    # Canonical camera API only
    results.append(
        _check_contains(
            root,
            "camera_nodes/camera_nodes/node.py",
            [
                "/promoc/camera/autofocus",
                "/promoc/camera/measure_mtf",
                "/promoc/camera/detect_rois",
            ],
            "camera node exposes canonical camera services",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "camera_nodes/camera_nodes/node.py",
            [
                "/promoc/camera_node/",
                "/promoc_assembly/",
                "register_service_alias_pair",
                "axis_position_callback_legacy",
            ],
            "camera node removed legacy service/topic alias wiring",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "camera_nodes/camera_nodes/sim_node.py",
            ["/promoc_assembly/lts300_x_axis/position", "position_callback_legacy"],
            "camera simulator removed legacy axis topic",
        )
    )

    # Canonical linear-axis API only
    results.append(
        _check_contains(
            root,
            "linear_axis_nodes/linear_axis_nodes/node.py",
            ["/promoc/linear_axis/"],
            "linear-axis node uses canonical namespace",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "linear_axis_nodes/linear_axis_nodes/node.py",
            [
                "register_service_alias_pair",
                "other_axis_position_callback_legacy",
                "self.config.namespace",
            ],
            "linear-axis node removed legacy service/topic alias wiring",
        )
    )

    # Canonical mover API only
    results.append(
        _check_contains(
            root,
            "planar_motor_nodes/planar_motor_nodes/node.py",
            ["/promoc/mover/"],
            "mover node uses canonical namespace",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "planar_motor_nodes/planar_motor_nodes/node.py",
            ["register_service_alias_pair", 'XBotInfo, "xbot_info", 10'],
            "mover node removed legacy service/topic alias wiring",
        )
    )

    # Compatibility layer removed
    results.append(
        _check_file_absent(
            root,
            "promoc_core/promoc_core/service_alias.py",
            "service_alias compatibility module removed",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "promoc_core/promoc_core/__init__.py",
            ["service_alias"],
            "promoc_core no longer exports service_alias",
        )
    )

    # Camera deprecated parameter compatibility removed
    results.append(
        _check_not_contains(
            root,
            "camera_nodes/camera_nodes/config.py",
            [
                "mtf_csv_path",
                "DEPRECATED_PARAMETER_REPLACEMENTS",
                "warn_on_deprecated_parameter_overrides",
            ],
            "camera config removed deprecated parameter compatibility layer",
        )
    )

    # Canonical docs
    results.append(
        _check_contains(
            root,
            "docs/START_HERE.md",
            ["runtime_mode:=hardware|sim"],
            "START_HERE documents canonical launch API",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "docs/START_HERE.md",
            ["sim_mode", "use_simulator", "/promoc/camera_node/"],
            "START_HERE no longer documents legacy launch/service paths",
        )
    )
    results.append(
        _check_contains(
            root,
            "docs/MIGRATION_NOTES.md",
            ["Release N+1"],
            "migration notes describe Release N+1 canonical-only contract",
        )
    )

    # Preserve prior structural checks introduced in Release N
    results.append(
        _check_file_exists(
            root,
            "camera_nodes/test/fixtures/synthetic_targets.py",
            "camera test fixtures contain synthetic mtf target helpers",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "camera_nodes/camera_nodes/services/mtf_params.py",
            "camera adapters package contains centralized mtf parameter mapping",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "camera_nodes/camera_nodes/services/registry.py",
            "camera services package contains service composition registry",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "camera_nodes/camera_nodes/services.py",
            "legacy flat services.py module removed in favor of services package",
        )
    )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run automated Release N+1 acceptance checks."
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

    print(f"Release N+1 check summary: {len(passed)} passed, {len(failed)} failed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

