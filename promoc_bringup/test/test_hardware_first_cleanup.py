"""Repo-level guards for the hardware-first simplification."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_verification_package_removed():
    assert not (ROOT / "verification").exists()


def test_verification_interfaces_removed():
    removed = [
        ROOT / "promoc_assembly_interfaces" / "srv" / "camera" / "VerifyAutofocus.srv",
        ROOT / "promoc_assembly_interfaces" / "srv" / "camera" / "VerifyMTF.srv",
        ROOT
        / "promoc_assembly_interfaces"
        / "srv"
        / "camera"
        / "VerifyCorrelation.srv",
        ROOT / "promoc_assembly_interfaces" / "srv" / "camera" / "RunVerification.srv",
    ]
    for path in removed:
        assert not path.exists()


def test_interface_cmake_has_no_verification_services():
    cmake_path = ROOT / "promoc_assembly_interfaces" / "CMakeLists.txt"
    content = cmake_path.read_text(encoding="utf-8", errors="ignore")
    assert "VerifyAutofocus.srv" not in content
    assert "VerifyMTF.srv" not in content
    assert "VerifyCorrelation.srv" not in content
    assert "RunVerification.srv" not in content


def test_measurement_runtime_launch_removed():
    assert not (ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py").exists()
