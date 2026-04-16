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


def test_root_readme_is_canonical_hardware_doc():
    content = (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    assert "colcon build --symlink-install" in content
    assert "ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware" in content
    assert "ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware" in content
    assert "/promoc/camera/set_exposure" in content
    assert "lts300_x_axis" in content
    assert "make doctor-hw" not in content
    assert "make build" not in content
    assert "make hw" not in content
    assert "make camera-hw" not in content
    assert "install_all.sh" not in content
    assert "docs/START_HERE.md" not in content


def test_split_docs_and_setup_are_removed():
    removed = [
        ROOT / "setup",
        ROOT / "docs",
        ROOT / "camera_nodes" / "docs",
        ROOT / "promoc_core" / "docs",
        ROOT / "promoc_core" / "ERROR_HANDLING.md",
        ROOT / "promoc_core" / "QUICK_REFERENCE.md",
    ]
    for path in removed:
        assert not path.exists()


def test_promoc_core_is_trimmed_to_supported_modules():
    removed = [
        ROOT / "promoc_core" / "promoc_core" / "conversions.py",
        ROOT / "promoc_core" / "promoc_core" / "motion.py",
        ROOT / "promoc_core" / "promoc_core" / "motion_interface.py",
        ROOT / "promoc_core" / "test" / "test_conversions.py",
        ROOT / "promoc_core" / "test" / "test_motion_interface.py",
    ]
    for path in removed:
        assert not path.exists()

    init_content = (
        ROOT / "promoc_core" / "promoc_core" / "__init__.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "motion_interface" not in init_content
    assert "conversions" not in init_content


def test_docs_no_legacy_launch_names():
    docs = [
        ROOT / "README.md",
        ROOT / "camera_nodes" / "README.md",
        ROOT / "linear_axis_nodes" / "README.md",
        ROOT / "promoc_bringup" / "README.md",
    ]
    legacy = ("promoc_assembly_launch.py", "promoc_assembly_demo_launch.py")
    for path in docs:
        content = path.read_text(encoding="utf-8", errors="ignore")
        for name in legacy:
            assert name not in content
