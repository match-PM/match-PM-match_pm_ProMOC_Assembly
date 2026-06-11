# ruff: noqa: E402
"""Import-safety tests for vendor-free camera operation."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("camera_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))


def _clear_optional_modules() -> None:
    for name in list(sys.modules):
        if name.startswith("pm_genicam_controller_interfaces") or name == "cv2":
            sys.modules.pop(name, None)


def test_package_import_succeeds_without_optional_camera_modules():
    _clear_optional_modules()
    module = importlib.import_module("camera_nodes.node")
    assert hasattr(module, "CameraNode")
    assert "pm_genicam_controller_interfaces" not in sys.modules
    assert "cv2" not in sys.modules


def test_hardware_driver_import_is_lazy():
    _clear_optional_modules()
    module = importlib.import_module("camera_nodes.drivers.hardware")
    assert hasattr(module, "HardwareCameraDriver")
    assert "pm_genicam_controller_interfaces" not in sys.modules
