#!/usr/bin/env python3
"""Automated acceptance checks for the messstand branch contract."""

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


def _declares_launch_argument(content: str, arg_name: str) -> bool:
    pattern = rf"DeclareLaunchArgument\(\s*\"{re.escape(arg_name)}\""
    return re.search(pattern, content) is not None


def _check_exists(root: Path, rel_path: str, name: str) -> CheckResult:
    exists = (root / rel_path).exists()
    return CheckResult(name=name, ok=exists, detail="" if exists else rel_path)


def _check_absent(root: Path, rel_path: str, name: str) -> CheckResult:
    exists = (root / rel_path).exists()
    detail = f"{rel_path}: should be absent" if exists else ""
    return CheckResult(name=name, ok=not exists, detail=detail)


def _check_contains(root: Path, rel_path: str, needles: list[str], name: str) -> CheckResult:
    content = _read_text(root, rel_path)
    missing = [needle for needle in needles if needle not in content]
    return CheckResult(
        name=name,
        ok=not missing,
        detail="" if not missing else f"{rel_path}: missing {missing}",
    )


def _check_not_contains(
    root: Path, rel_path: str, needles: list[str], name: str
) -> CheckResult:
    content = _read_text(root, rel_path)
    present = [needle for needle in needles if needle in content]
    return CheckResult(
        name=name,
        ok=not present,
        detail="" if not present else f"{rel_path}: unexpected {present}",
    )


def _check_no_launch_arg(root: Path, rel_path: str, arg_name: str, name: str) -> CheckResult:
    content = _read_text(root, rel_path)
    ok = not _declares_launch_argument(content, arg_name)
    detail = "" if ok else f"{rel_path}: still declares launch arg '{arg_name}'"
    return CheckResult(name=name, ok=ok, detail=detail)


def _evaluate(root: Path) -> list[CheckResult]:
    return [
        _check_exists(
            root,
            "camera_nodes/package.xml",
            "camera runtime package is present",
        ),
        _check_exists(
            root,
            "linear_axis_nodes/package.xml",
            "linear-axis runtime package is present",
        ),
        _check_exists(
            root,
            "promoc_bringup/launch/system.launch.py",
            "system launch is present",
        ),
        _check_absent(
            root,
            "planar_motor_nodes",
            "planar motor package removed from messstand branch",
        ),
        _check_absent(
            root,
            "promoc_bringup/launch/planar_motor_demo.launch.py",
            "planar motor demo launch removed",
        ),
        _check_absent(
            root,
            "promoc_bringup/launch/promoc_assembly_demo.launch.py",
            "promo assembly demo launch removed",
        ),
        _check_absent(
            root,
            "promoc_bringup/promoc_bringup/unified_demo.py",
            "unified demo runner removed",
        ),
        _check_absent(
            root,
            "camera_nodes/camera_nodes/sim_node.py",
            "camera simulator node removed",
        ),
        _check_absent(
            root,
            "camera_nodes/camera_nodes/drivers/sim.py",
            "camera simulator driver removed",
        ),
        _check_absent(
            root,
            "promoc_bringup/config/mover_node_params.yaml",
            "mover config removed",
        ),
        _check_absent(
            root,
            "promoc_assembly_interfaces/srv/planar_motor",
            "planar motor services removed from interface package",
        ),
        _check_absent(
            root,
            "promoc_assembly_interfaces/msg/planar_motor",
            "planar motor messages removed from interface package",
        ),
        _check_contains(
            root,
            "promoc_bringup/launch/system.launch.py",
            ["camera.launch.py", "linear_axis_nodes", "runtime_mode"],
            "system launch starts camera stack and axes",
        ),
        _check_not_contains(
            root,
            "promoc_bringup/launch/system.launch.py",
            ["planar_motor_nodes", "mover_node", "mover_node_params.yaml"],
            "system launch no longer starts mover stack",
        ),
        _check_contains(
            root,
            "promoc_bringup/launch/camera.launch.py",
            ["runtime_mode"],
            "camera launch keeps canonical runtime_mode contract",
        ),
        _check_no_launch_arg(
            root,
            "promoc_bringup/launch/camera.launch.py",
            "sim_mode",
            "camera launch no longer exposes sim_mode",
        ),
        _check_no_launch_arg(
            root,
            "promoc_bringup/launch/camera.launch.py",
            "use_simulator",
            "camera launch no longer exposes use_simulator launch arg",
        ),
        _check_contains(
            root,
            "promoc_bringup/launch/optical_measurement_system.launch.py",
            ["runtime_mode", "camera_nodes", "linear_axis_nodes", "camera_type"],
            "optical measurement launch matches messstand shape",
        ),
        _check_contains(
            root,
            "camera_nodes/camera_nodes/node.py",
            [
                "/promoc/camera/autofocus",
                "/promoc/camera/measure_mtf",
                "/promoc/camera/detect_rois",
            ],
            "camera node exposes canonical services",
        ),
        _check_not_contains(
            root,
            "camera_nodes/camera_nodes/node.py",
            ["use_simulator", "x_axis_node_name", "SimulatedCameraDriver"],
            "camera node is hardware-only with fixed X-axis wiring",
        ),
        _check_contains(
            root,
            "linear_axis_nodes/linear_axis_nodes/node.py",
            ["/promoc/linear_axis/"],
            "linear-axis node uses canonical namespace",
        ),
        _check_not_contains(
            root,
            "README.md",
            ["planar_motor_nodes"],
            "root README no longer advertises planar motor package",
        ),
        _check_not_contains(
            root,
            "README.md",
            [
                "make build",
                "make hw",
                "make camera-hw",
                "make lint",
                "make test-unit",
                "make release-n1-check",
                "make smoke-hw",
                "make sim",
                "runtime_mode:=hardware|sim",
                "docs/START_HERE.md",
                "docs/PACKAGES.md",
                "docs/SYSTEM_OVERVIEW.md",
                "install_all.sh",
                "make doctor-hw",
            ],
            "root README no longer advertises simulation mode",
        ),
        _check_contains(
            root,
            "README.md",
            [
                "colcon build --symlink-install",
                "ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware",
                "ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware",
                "/promoc/camera/set_exposure",
                "lts300_x_axis",
                "promoc_core.logging",
            ],
            "root README is the canonical messstand doc",
        ),
        _check_absent(
            root,
            "setup",
            "repo setup directory removed",
        ),
        _check_absent(
            root,
            "docs",
            "split top-level docs removed",
        ),
        _check_absent(
            root,
            "camera_nodes/docs",
            "camera package docs directory removed",
        ),
        _check_absent(
            root,
            "promoc_core/docs",
            "promoc_core docs directory removed",
        ),
        _check_absent(
            root,
            "promoc_core/ERROR_HANDLING.md",
            "promoc_core error-handling guide removed",
        ),
        _check_absent(
            root,
            "promoc_core/QUICK_REFERENCE.md",
            "promoc_core quick reference removed",
        ),
        _check_absent(
            root,
            "promoc_core/promoc_core/conversions.py",
            "promoc_core conversions module removed",
        ),
        _check_absent(
            root,
            "promoc_core/promoc_core/motion.py",
            "promoc_core motion module removed",
        ),
        _check_absent(
            root,
            "promoc_core/promoc_core/motion_interface.py",
            "promoc_core motion interface removed",
        ),
        _check_absent(
            root,
            "promoc_core/test/test_conversions.py",
            "promoc_core conversions tests removed",
        ),
        _check_absent(
            root,
            "promoc_core/test/test_motion_interface.py",
            "promoc_core motion-interface tests removed",
        ),
        _check_not_contains(
            root,
            "promoc_core/promoc_core/__init__.py",
            ["conversions", "motion", "motion_interface"],
            "promoc_core exports only supported shared modules",
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run automated messstand-branch acceptance checks."
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
            status = "PASS" if result.ok else "FAIL"
            detail = f" - {result.detail}" if result.detail else ""
            print(f"[{status}] {result.name}{detail}")

    print(
        f"Acceptance summary: {len(passed)} passed, {len(failed)} failed, {len(results)} total."
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
