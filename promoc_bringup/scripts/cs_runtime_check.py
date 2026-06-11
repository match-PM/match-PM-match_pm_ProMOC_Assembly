#!/usr/bin/env python3
"""Automated acceptance checks for the reduced CS camera runtime."""

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
    results.append(
        _check_contains(
            "promoc_bringup/launch/camera.launch.py",
            ["runtime_mode", 'executable="camera_node"'],
            "camera.launch keeps runtime_mode and camera_node",
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
        _check_not_contains(
            "promoc_bringup/launch/camera.launch.py",
            ["camera_simulator", "pm_genicam_controller"],
            "camera.launch excludes simulator and controller sidecars",
        )
    )
    results.append(
        _check_contains(
            "camera_nodes/camera_nodes/config.py",
            ["/promoc/camera/image_raw", "/promoc/camera/status"],
            "camera node publishes image and status",
        )
    )
    results.append(
        _check_not_contains(
            "camera_nodes/camera_nodes/node.py",
            [
                "/promoc/camera/autofocus",
                "/promoc/camera/set_exposure",
                "cv_bridge",
                "services.autofocus",
                "services.exposure",
            ],
            "camera node has no autofocus or exposure runtime wiring",
        )
    )
    results.append(
        _check_contains(
            "promoc_bringup/promoc_bringup/camera_launch_builder.py",
            ["source_image_topic", "image_topic", "status_topic"],
            "camera launch builder maps reduced camera parameters",
        )
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run automated CS runtime checks.")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print failed checks and summary.",
    )
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
