# ruff: noqa: E402
"""Import-safety tests for vendor-free mock operation."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("planar_motor_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

pkg = sys.modules.setdefault(
    "promoc_assembly_interfaces",
    types.ModuleType("promoc_assembly_interfaces"),
)
msg_mod = sys.modules.setdefault(
    "promoc_assembly_interfaces.msg",
    types.ModuleType("promoc_assembly_interfaces.msg"),
)
srv_mod = sys.modules.setdefault(
    "promoc_assembly_interfaces.srv",
    types.ModuleType("promoc_assembly_interfaces.srv"),
)

msg_mod.DeviceStatus = getattr(msg_mod, "DeviceStatus", type("DeviceStatus", (), {}))
msg_mod.XBotInfo = getattr(msg_mod, "XBotInfo", type("XBotInfo", (), {}))
for name in (
    "ActivateXbots",
    "ArcMotionSi",
    "GetXBotStatus",
    "LevitationXbots",
    "LinearMotionSi",
    "RotaryMotion",
    "RotaryMotionSi",
    "SetVelocityAcceleration",
    "SixDofMotion",
    "StopMotion",
):
    if not hasattr(srv_mod, name):
        setattr(srv_mod, name, type(name, (), {}))

pkg.msg = msg_mod
pkg.srv = srv_mod


def _clear_vendor_modules() -> None:
    for name in list(sys.modules):
        if (
            name == "pmclib"
            or name.startswith("pmclib.")
            or name.startswith("planar_motor_nodes.drivers.vendor.pmclib")
        ):
            sys.modules.pop(name, None)


def test_package_import_succeeds_without_vendor_modules():
    _clear_vendor_modules()
    module = importlib.import_module("planar_motor_nodes.node")
    assert hasattr(module, "MoverServiceNode")
    assert "pmclib" not in sys.modules


def test_hardware_driver_import_is_lazy():
    _clear_vendor_modules()
    module = importlib.import_module("planar_motor_nodes.drivers.hardware")
    assert hasattr(module, "HardwarePlanarMotorDriver")
    assert "pmclib" not in sys.modules
