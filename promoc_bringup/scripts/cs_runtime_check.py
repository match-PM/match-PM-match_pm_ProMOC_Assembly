#!/usr/bin/env python3
"""Automated acceptance checks for the CS runtime contract."""

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


ROOT = Path(__file__).resolve().parents[2]


def _read_text(rel_path: str) -> str:
    path = ROOT / rel_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _contains_all(content: str, needles: list[str]) -> tuple[bool, list[str]]:
    missing = [needle for needle in needles if needle not in content]
    return len(missing) == 0, missing


def _contains_none(content: str, needles: list[str]) -> tuple[bool, list[str]]:
    present = [needle for needle in needles if needle in content]
    return len(present) == 0, present


def _check_file_exists(rel_path: str, name: str) -> CheckResult:
    exists = (ROOT / rel_path).exists()
    return CheckResult(name=name, ok=exists, detail=rel_path if not exists else "")


def _check_file_absent(rel_path: str, name: str) -> CheckResult:
    exists = (ROOT / rel_path).exists()
    detail = "" if not exists else f"{rel_path}: should be removed"
    return CheckResult(name=name, ok=not exists, detail=detail)


def _check_contains(rel_path: str, needles: list[str], name: str) -> CheckResult:
    content = _read_text(rel_path)
    ok, missing = _contains_all(content, needles)
    detail = "" if ok else f"{rel_path}: missing {missing}"
    return CheckResult(name=name, ok=ok, detail=detail)


def _check_not_contains(rel_path: str, needles: list[str], name: str) -> CheckResult:
    content = _read_text(rel_path)
    ok, present = _contains_none(content, needles)
    detail = "" if ok else f"{rel_path}: unexpected {present}"
    return CheckResult(name=name, ok=ok, detail=detail)


def _declares_launch_argument(content: str, arg_name: str) -> bool:
    pattern = rf"DeclareLaunchArgument\(\s*\"{re.escape(arg_name)}\""
    return re.search(pattern, content) is not None


def _check_no_launch_arg(rel_path: str, arg_name: str, name: str) -> CheckResult:
    content = _read_text(rel_path)
    ok = not _declares_launch_argument(content, arg_name)
    detail = "" if ok else f"{rel_path}: still declares launch arg '{arg_name}'"
    return CheckResult(name=name, ok=ok, detail=detail)


def _evaluate() -> list[CheckResult]:
    results: list[CheckResult] = []

    results.append(_check_file_exists("README.md", "root README exists"))
    results.append(_check_file_exists("docs/START_HERE.md", "onboarding doc exists"))
    results.append(_check_file_exists("docs/PACKAGES.md", "package guide exists"))
    results.append(_check_file_exists("docs/SYSTEM_OVERVIEW.md", "system overview exists"))

    results.append(
        _check_contains(
            "promoc_bringup/launch/system.launch.py",
            ["runtime_mode", 'namespace="promoc/linear_axis"', 'name="mover"'],
            "system.launch uses canonical runtime mode and namespaces",
        )
    )
    results.append(
        _check_no_launch_arg(
            "promoc_bringup/launch/system.launch.py",
            "sim_mode",
            "system.launch no longer exposes sim_mode",
        )
    )
    results.append(
        _check_contains(
            "promoc_bringup/launch/camera.launch.py",
            ["runtime_mode"],
            "camera.launch uses runtime_mode",
        )
    )
    results.append(
        _check_no_launch_arg(
            "promoc_bringup/launch/camera.launch.py",
            "sim_mode",
            "camera.launch no longer exposes sim_mode",
        )
    )
    results.append(
        _check_file_absent(
            "promoc_bringup/launch/optical_measurement_system.launch.py",
            "optical measurement launch removed",
        )
    )

    results.append(
        _check_contains(
            "camera_nodes/camera_nodes/node.py",
            ["/promoc/camera/autofocus", "/promoc/camera/set_exposure"],
            "camera node exposes only the CS camera services",
        )
    )
    results.append(
        _check_not_contains(
            "camera_nodes/camera_nodes/node.py",
            [
                "/promoc/camera/measure_mtf",
                "/promoc/camera/detect_rois",
                "/promoc/camera/select_roi",
                "/promoc/camera/autofocus_comparison",
            ],
            "camera node no longer wires MTF or comparison services",
        )
    )
    results.append(
        _check_contains(
            "camera_nodes/camera_nodes/services/autofocus.py",
            ["Four-Step", "using Four-Step."],
            "autofocus handler documents Four-Step as the maintained path",
        )
    )

    results.append(
        _check_contains(
            "promoc_assembly_interfaces/CMakeLists.txt",
            ['"srv/camera/SetExposure.srv"', '"srv/camera/AutoFocus.srv"'],
            "camera interface build only keeps autofocus and exposure",
        )
    )
    results.append(
        _check_not_contains(
            "promoc_assembly_interfaces/CMakeLists.txt",
            [
                "MeasureMTF.srv",
                "DetectRois.srv",
                "FlyOverAutofocus.srv",
                "VerifyAutofocus.srv",
                "VerifyMTF.srv",
                "VerifyCorrelation.srv",
                "RunVerification.srv",
            ],
            "camera CMake no longer lists removed interfaces",
        )
    )

    for rel_path in [
        "promoc_bringup/launch/optical_measurement_system.launch.py",
        "camera_nodes/camera_nodes/services/mtf.py",
        "camera_nodes/camera_nodes/services/camera_format.py",
        "camera_nodes/camera_nodes/algorithms/mtf",
        "camera_nodes/camera_nodes/algorithms/field_curvature.py",
        "camera_nodes/camera_nodes/algorithms/roi_detection.py",
        "camera_nodes/scripts/reproduce_mtf.py",
        "camera_nodes/test/test_camera_mtf_config_mapping.py",
        "verification",
        "promoc_assembly_interfaces/srv/camera/MeasureMTF.srv",
        "promoc_assembly_interfaces/srv/camera/DetectRois.srv",
        "promoc_assembly_interfaces/srv/camera/FlyOverAutofocus.srv",
        "promoc_assembly_interfaces/srv/camera/VerifyAutofocus.srv",
        "promoc_assembly_interfaces/srv/camera/VerifyMTF.srv",
        "promoc_assembly_interfaces/srv/camera/VerifyCorrelation.srv",
        "promoc_assembly_interfaces/srv/camera/RunVerification.srv",
        "promoc_bringup/scripts/release_n_check.py",
        "promoc_bringup/scripts/release_n_smoke.py",
        "promoc_bringup/scripts/generate_param_docs.py",
    ]:
        results.append(_check_file_absent(rel_path, f"removed: {rel_path}"))
    results.append(
        _check_not_contains(
            "promoc_bringup/config/user_config.example.yaml",
            ["measurement_base_path", "save_debug_images", "autofocus_profiles", "mtf"],
            "user config example stays on the CS minimum",
        )
    )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run automated CS runtime checks.")
    parser.add_argument("--quiet", action="store_true", help="Only print failed checks and summary.")
    args = parser.parse_args(argv)

    results = _evaluate()
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

    print(f"CS runtime check summary: {len(passed)} passed, {len(failed)} failed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
