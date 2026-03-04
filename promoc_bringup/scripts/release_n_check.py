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
    present = [needle for needle in needles if needle in content]
    ok = len(present) == 0
    detail = "" if ok else f"{rel_path}: unexpected {present}"
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
            "camera_nodes/camera_nodes/camera_node.py",
            ["from .helpers.image_processing import CameraImageProcessing"],
            "camera node imports image processing from helpers package",
        )
    )
    results.append(
        _check_contains(
            root,
            "camera_nodes/setup.py",
            ["camera_simulator = camera_nodes.nodes.camera_simulator:main"],
            "camera simulator entrypoint uses nodes subpackage",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "camera_nodes/setup.py",
            ["camera_watchdog"],
            "camera watchdog entrypoint removed from package setup",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/launch/camera.launch.py",
            ['executable="camera_simulator"'],
            "camera launch includes simulator node",
        )
    )
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
            "camera_nodes/camera_nodes/helpers/mtf_param_mapping.py",
            "camera helpers package contains centralized mtf parameter mapping",
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
    results.append(
        _check_file_absent(
            root,
            "camera_nodes/camera_nodes/handlers/__init__.py",
            "legacy handlers compatibility package removed",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "camera_nodes/camera_nodes/support/__init__.py",
            "legacy support compatibility package removed",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "camera_nodes/camera_nodes/algorithms/synthetic_targets.py",
            "synthetic mtf fixtures removed from runtime algorithms package",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "camera_nodes/camera_nodes/algorithms/mtf_analysis.py",
            "legacy mtf_analysis wrapper removed from algorithms package",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "camera_nodes/camera_nodes/algorithms/autofocus_algo.py",
            "legacy autofocus_algo shim removed from algorithms package",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "camera_nodes/camera_nodes/algorithms/test_mspr.py",
            "legacy standalone mspr test script removed from algorithms package",
        )
    )
    results.append(
        _check_not_contains(
            root,
            "promoc_bringup/launch/camera.launch.py",
            ["camera_watchdog"],
            "camera launch no longer starts watchdog node",
        )
    )
    results.append(
        _check_contains(
            root,
            "linear_axis_nodes/linear_axis_nodes/lts300_node.py",
            [
                "/promoc/linear_axis/",
                "legacy_path = f",
                "register_service_alias_pair",
                "from .helpers.lts300_interface import Lts300Interface",
                "from .services.callbacks import ServiceCallbacks",
            ],
            "linear-axis services expose canonical + legacy paths",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "linear_axis_nodes/linear_axis_nodes/services/callbacks.py",
            "linear-axis services package contains callback implementation",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "linear_axis_nodes/linear_axis_nodes/helpers/lts300_interface.py",
            "linear-axis helpers package contains lts300 interface",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "linear_axis_nodes/linear_axis_nodes/lts300_service_callbacks.py",
            "legacy flat lts300_service_callbacks module removed",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "linear_axis_nodes/linear_axis_nodes/lts300_interface.py",
            "legacy flat lts300_interface module removed",
        )
    )
    results.append(
        _check_contains(
            root,
            "planar_motor_nodes/planar_motor_nodes/mover_node.py",
            [
                "/promoc/mover/",
                "legacy_path = f",
                "register_service_alias_pair",
                "from .helpers.pmc_interface import PmcInterface",
                "from .helpers.mover_utils import MoverUtils",
                "from .services import ServiceCallbacks",
            ],
            "mover services expose canonical + legacy paths",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "planar_motor_nodes/planar_motor_nodes/services/motion.py",
            "mover services package contains motion callback implementation",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "planar_motor_nodes/planar_motor_nodes/services/control.py",
            "mover services package contains control callback implementation",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "planar_motor_nodes/planar_motor_nodes/helpers/pmc_interface.py",
            "mover helpers package contains pmc interface",
        )
    )
    results.append(
        _check_file_exists(
            root,
            "planar_motor_nodes/planar_motor_nodes/helpers/mover_utils.py",
            "mover helpers package contains runtime motion utilities",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "planar_motor_nodes/planar_motor_nodes/mover_pmc_interface.py",
            "legacy flat mover_pmc_interface module removed",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "planar_motor_nodes/planar_motor_nodes/mover_utils.py",
            "legacy flat mover_utils module removed",
        )
    )
    results.append(
        _check_file_absent(
            root,
            "planar_motor_nodes/planar_motor_nodes/callbacks/__init__.py",
            "legacy callbacks package removed in favor of services package",
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
            "pytest.ini",
            ["[pytest]", "-p no:cacheprovider"],
            "pytest config disables cacheprovider for stable Windows runs",
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
            "docs/PROJECT_STRUCTURE.md",
            ["Task-Oriented Entry Points", "Dependency Direction"],
            "project structure guide exists with task-oriented navigation",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_bringup/README.md",
            [
                "## Purpose",
                "## How To Run / Build",
                "## Where To Edit",
                "## Verify Changes",
            ],
            "bringup README follows unified package template",
        )
    )
    results.append(
        _check_contains(
            root,
            "camera_nodes/README.md",
            [
                "## Purpose",
                "## How To Run / Build",
                "## Where To Edit",
                "## Verify Changes",
            ],
            "camera README follows unified package template",
        )
    )
    results.append(
        _check_contains(
            root,
            "linear_axis_nodes/README.md",
            [
                "## Purpose",
                "## How To Run / Build",
                "## Where To Edit",
                "## Verify Changes",
            ],
            "linear-axis README follows unified package template",
        )
    )
    results.append(
        _check_contains(
            root,
            "planar_motor_nodes/README.md",
            [
                "## Purpose",
                "## How To Run / Build",
                "## Where To Edit",
                "## Verify Changes",
            ],
            "planar-motor README follows unified package template",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_assembly_interfaces/README.md",
            [
                "## Purpose",
                "## How To Run / Build",
                "## Where To Edit",
                "## Verify Changes",
            ],
            "interfaces README follows unified package template",
        )
    )
    results.append(
        _check_contains(
            root,
            "promoc_core/README.md",
            [
                "## Purpose",
                "## How To Run / Build",
                "## Where To Edit",
                "## Verify Changes",
            ],
            "promoc_core README follows unified package template",
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
