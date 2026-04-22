#!/usr/bin/env python3
"""Basic local sanity checks for the ProMOC Assembly repository."""

from __future__ import annotations

from pathlib import Path
import sys


SETUP_DIR = Path(__file__).resolve().parent
REPO_ROOT = SETUP_DIR.parent


def _log(status: str, message: str) -> None:
    print(f"[{status}] {message}")


def _add_local_source_paths() -> None:
    """Allow direct source imports without requiring colcon install."""
    package_roots = [
        REPO_ROOT / "planar_motor_nodes",
        REPO_ROOT / "linear_axis_nodes",
        REPO_ROOT / "camera_nodes",
        REPO_ROOT / "promoc_core",
    ]
    for package_root in package_roots:
        if package_root.exists():
            sys.path.insert(0, str(package_root))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_interface_definitions() -> bool:
    """Check that required service definition files exist."""
    _log("INFO", "Checking interface definition files...")

    required = [
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "planar_motor" / "ActivateXbots.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "planar_motor" / "LinearMotionSi.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "planar_motor" / "SixDofMotion.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "planar_motor" / "ArcMotionSi.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "linear_axis" / "MoveAbsolute.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "linear_axis" / "MoveRelative.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "linear_axis" / "Home.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "linear_axis" / "ShutdownLinearAxis.srv",
    ]

    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.exists()]
    if missing:
        _log("FAIL", f"Missing service definition files: {missing}")
        return False

    _log("PASS", "All required service definition files are present.")
    return True


def test_response_contracts() -> bool:
    """Check that key services expose success + status_message in response part."""
    _log("INFO", "Checking response field contract in .srv files...")

    services = [
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "planar_motor" / "ActivateXbots.srv",
        REPO_ROOT / "promoc_assembly_interfaces" / "srv" / "linear_axis" / "MoveAbsolute.srv",
    ]

    failures: list[str] = []
    for service_path in services:
        if not service_path.exists():
            failures.append(f"{service_path.name}: file missing")
            continue

        content = _read_text(service_path)
        if "---" not in content:
            failures.append(f"{service_path.name}: missing request/response separator")
            continue

        response_section = content.split("---", 1)[1]
        if "success" not in response_section or "status_message" not in response_section:
            failures.append(
                f"{service_path.name}: response must contain success + status_message"
            )

    if failures:
        _log("FAIL", "; ".join(failures))
        return False

    _log("PASS", "Service response contracts look correct.")
    return True


def test_mock_pmclib_import() -> bool:
    """Ensure mock PMCLib module can be imported from local source tree."""
    _log("INFO", "Checking local mock PMCLib import...")

    try:
        _add_local_source_paths()
        from planar_motor_nodes.drivers.mock_pmclib import MockPMCLib  # type: ignore

        _ = MockPMCLib()
        _log("PASS", "MockPMCLib import and instantiation successful.")
        return True
    except Exception as exc:  # pragma: no cover - diagnostic script
        _log("FAIL", f"MockPMCLib import failed: {exc}")
        return False


def test_camera_checkout() -> bool:
    """Check whether external camera_aravis2 checkout exists (optional)."""
    _log("INFO", "Checking optional camera_aravis2 checkout...")

    camera_repo_candidates = [
        Path.home() / "ros2_ws" / "src" / "camera_aravis2",
        REPO_ROOT / "camera_nodes" / "camera_nodes" / "drivers" / "camera_aravis2",
    ]

    for candidate in camera_repo_candidates:
        if candidate.exists():
            _log("PASS", f"camera_aravis2 repository found: {candidate}")
            return True

    _log(
        "WARN",
        "camera_aravis2 checkout not found (only required for hardware camera driver).",
    )
    return True


def main() -> int:
    print("ProMOC Assembly - Basic Local Sanity Check")
    print("=" * 52)

    checks = [
        test_interface_definitions,
        test_response_contracts,
        test_mock_pmclib_import,
        test_camera_checkout,
    ]

    passed = 0
    for check in checks:
        if check():
            passed += 1
        print()

    total = len(checks)
    print("=" * 52)
    print(f"Result: {passed}/{total} checks passed")

    if passed == total:
        _log("PASS", "Sanity checks passed.")
        return 0

    _log("FAIL", "Some sanity checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
