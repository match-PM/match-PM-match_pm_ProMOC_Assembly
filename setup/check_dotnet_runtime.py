#!/usr/bin/env python3
"""Detect available .NET runtimes for PMCLib/pythonnet."""

from __future__ import annotations

import subprocess


def check_dotnet() -> tuple[bool, str | None]:
    """Return whether dotnet is available and its version."""
    try:
        result = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        result = None

    if result and result.returncode == 0:
        version = result.stdout.strip()
        print(f"[PASS] .NET Core/SDK found: {version}")
        return True, version

    print("[FAIL] .NET Core/SDK not available")
    return False, None


def check_mono() -> tuple[bool, str | None]:
    """Return whether mono is available and its version line."""
    try:
        result = subprocess.run(
            ["mono", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        result = None

    if result and result.returncode == 0:
        version_line = result.stdout.splitlines()[0]
        print(f"[PASS] Mono runtime found: {version_line}")
        return True, version_line

    print("[FAIL] Mono runtime not available")
    return False, None


def test_pythonnet_runtime(runtime_name: str) -> bool:
    """Try loading pythonnet with a specific runtime backend."""
    print(f"\nTesting pythonnet with {runtime_name}...")
    try:
        from pythonnet import load

        if runtime_name not in {"coreclr", "mono"}:
            print(f"[FAIL] Unknown runtime: {runtime_name}")
            return False

        load(runtime_name)
        import clr  # noqa: F401

        print(f"[PASS] pythonnet loaded with {runtime_name}")
        return True
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"[FAIL] pythonnet failed with {runtime_name}: {exc}")
        return False


def main() -> int:
    print("ProMOC Assembly .NET Runtime Detection")
    print("=" * 40)

    dotnet_available, _ = check_dotnet()
    mono_available, _ = check_mono()

    if not dotnet_available and not mono_available:
        print("\n[FAIL] No .NET runtime found.")
        print("Install one of the following:")
        print("  - .NET SDK: sudo apt-get install dotnet-sdk-8.0")
        print("  - Mono: sudo apt-get install mono-complete")
        return 1

    print("\n" + "=" * 40)
    print("Testing pythonnet compatibility...")

    successful_runtimes: list[str] = []
    if dotnet_available and test_pythonnet_runtime("coreclr"):
        successful_runtimes.append("coreclr (.NET Core)")
    if mono_available and test_pythonnet_runtime("mono"):
        successful_runtimes.append("mono")

    if not successful_runtimes:
        print("\n[FAIL] pythonnet failed with all available runtimes.")
        print("Try reinstalling pythonnet: pip install --force-reinstall pythonnet")
        return 1

    print(f"\n[PASS] pythonnet compatible with: {', '.join(successful_runtimes)}")

    print("\n" + "=" * 40)
    print("[PASS] .NET runtime check completed")
    print("\nNext steps:")
    print("  1. Place PMCLib at planar_motor_nodes/.../drivers/vendor/pmclib/")
    print("  2. Test .NET interop if needed: python3 -c 'import clr'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
