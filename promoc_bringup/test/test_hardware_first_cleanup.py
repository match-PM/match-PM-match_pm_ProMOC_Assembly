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
        ROOT / "promoc_assembly_interfaces" / "srv" / "camera" / "VerifyCorrelation.srv",
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


def test_start_here_is_hardware_first():
    start_here = ROOT / "START_HERE.md"
    content = start_here.read_text(encoding="utf-8", errors="ignore")
    assert "make doctor-hw" in content
    assert "make hw" in content
    assert "make camera-hw" in content


def test_docs_no_legacy_launch_names():
    docs = [
        ROOT / "README_ENG.md",
        ROOT / "README_GER.md",
        ROOT / "setup" / "README.md",
        ROOT / "setup" / "QUICKSTART.md",
        ROOT / "promoc_bringup" / "README.md",
    ]
    legacy = ("promoc_assembly_launch.py", "promoc_assembly_demo_launch.py")
    for path in docs:
        content = path.read_text(encoding="utf-8", errors="ignore")
        for name in legacy:
            assert name not in content
