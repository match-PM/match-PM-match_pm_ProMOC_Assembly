"""Tests for lazy PMCLib loading and hardware-driver lifecycle wiring."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("planar_motor_nodes", "promoc_core"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from promoc_core import error_codes
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    DriverNotAvailableError,
    HardwareError,
)

from planar_motor_nodes.drivers import hardware, pmclib_loader


def _clear_pmclib_modules() -> None:
    for name in list(sys.modules):
        if name == "pmclib" or name.startswith("pmclib."):
            sys.modules.pop(name, None)
    sys.path[:] = [
        path
        for path in sys.path
        if not ("/pytest-" in path and path.endswith("/drivers/vendor"))
    ]


def test_loader_imports_fake_pmclib_from_vendor_parent(tmp_path, monkeypatch):
    drivers_dir = tmp_path / "drivers"
    vendor_dir = drivers_dir / "vendor"
    pmclib_dir = vendor_dir / "pmclib"
    pmclib_dir.mkdir(parents=True)
    (pmclib_dir / "__init__.py").write_text("", encoding="utf-8")
    for module_name in ("system_commands", "xbot_commands"):
        (pmclib_dir / f"{module_name}.py").write_text(
            f"NAME = '{module_name}'\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(pmclib_loader, "VENDOR_DIR", vendor_dir)
    monkeypatch.setattr(pmclib_loader, "PMCLIB_DIR", pmclib_dir)
    monkeypatch.syspath_prepend(str(tmp_path / "unrelated"))
    _clear_pmclib_modules()

    system_commands, xbot_commands = pmclib_loader.load_pmclib()

    assert system_commands.NAME == "system_commands"
    assert xbot_commands.NAME == "xbot_commands"
    assert str(vendor_dir) in sys.path


def test_loader_reports_missing_pmclib_with_vendor_path(tmp_path, monkeypatch):
    drivers_dir = tmp_path / "drivers"
    vendor_dir = drivers_dir / "vendor"
    pmclib_dir = vendor_dir / "pmclib"
    drivers_dir.mkdir()
    monkeypatch.setattr(pmclib_loader, "VENDOR_DIR", vendor_dir)
    monkeypatch.setattr(pmclib_loader, "PMCLIB_DIR", pmclib_dir)
    _clear_pmclib_modules()

    with pytest.raises(ImportError) as excinfo:
        pmclib_loader.load_pmclib()

    message = str(excinfo.value)
    assert "drivers/vendor/pmclib" in message or "vendor/pmclib" in message
    assert "mock mode works without it" in message


def test_loader_reports_missing_clr_actionably(tmp_path, monkeypatch):
    drivers_dir = tmp_path / "drivers"
    vendor_dir = drivers_dir / "vendor"
    pmclib_dir = vendor_dir / "pmclib"
    pmclib_dir.mkdir(parents=True)
    (pmclib_dir / "__init__.py").write_text("import clr\n", encoding="utf-8")

    monkeypatch.setattr(pmclib_loader, "VENDOR_DIR", vendor_dir)
    monkeypatch.setattr(pmclib_loader, "PMCLIB_DIR", pmclib_dir)
    _clear_pmclib_modules()

    with pytest.raises(ImportError) as excinfo:
        pmclib_loader.load_pmclib()

    message = str(excinfo.value)
    assert "pythonnet/clr" in message
    assert "python3 -c 'import clr'" in message


def test_hardware_driver_wraps_pmclib_import_error(monkeypatch):
    def _missing_pmclib():
        raise ImportError("Planar-motor hardware mode requires local drivers/vendor/pmclib/")

    monkeypatch.setattr(hardware, "load_pmclib", _missing_pmclib)
    driver = hardware.HardwarePlanarMotorDriver(SimpleNamespace())

    with pytest.raises(DriverNotAvailableError) as excinfo:
        driver._load_backend()

    assert "drivers/vendor/pmclib" in str(excinfo.value)


def test_hardware_driver_connects_without_mastership_side_effects(monkeypatch):
    calls: list[str] = []

    class SystemCommands:
        @staticmethod
        def connect_to_pmc(controller_address):
            calls.append(f"connect:{controller_address}")
            return True

        @staticmethod
        def gain_mastership():  # pragma: no cover - must not be used
            raise AssertionError("gain_mastership must stay unused")

        @staticmethod
        def release_mastership():  # pragma: no cover - must not be used
            raise AssertionError("release_mastership must stay unused")

    monkeypatch.setattr(
        hardware,
        "load_pmclib",
        lambda: (SystemCommands, SimpleNamespace()),
    )

    driver = hardware.HardwarePlanarMotorDriver(SimpleNamespace())
    driver.connect("192.0.2.10")
    driver.disconnect()

    assert calls == ["connect:192.0.2.10"]


def test_hardware_driver_retries_pmc_connection_until_success(monkeypatch):
    calls: list[str] = []

    class SystemCommands:
        @staticmethod
        def connect_to_pmc(controller_address):
            calls.append(f"connect:{controller_address}")
            return len(calls) >= 3

        @staticmethod
        def auto_connect_to_pmc():  # pragma: no cover - must not be used
            raise AssertionError("auto_connect_to_pmc must stay unused")

    monkeypatch.setattr(
        hardware,
        "load_pmclib",
        lambda: (SystemCommands, SimpleNamespace()),
    )
    monkeypatch.setattr(hardware.time, "sleep", lambda _seconds: None)

    driver = hardware.HardwarePlanarMotorDriver(SimpleNamespace())
    driver.connect("192.0.2.10")

    assert calls == [
        "connect:192.0.2.10",
        "connect:192.0.2.10",
        "connect:192.0.2.10",
    ]


def _hardware_driver_with_xbots(monkeypatch, xbots):
    class SystemCommands:
        @staticmethod
        def connect_to_pmc(controller_address):
            _ = controller_address
            return True

    class XBotCommands:
        @staticmethod
        def get_all_xbot_info(group_id):
            _ = group_id
            return xbots

    monkeypatch.setattr(hardware, "load_pmclib", lambda: (SystemCommands, XBotCommands))
    driver = hardware.HardwarePlanarMotorDriver(SimpleNamespace())
    driver.connect("192.0.2.10")
    return driver


def test_hardware_driver_accepts_explicit_xbot_ids(monkeypatch):
    driver = _hardware_driver_with_xbots(
        monkeypatch,
        [SimpleNamespace(xbot_id=2), SimpleNamespace(xbot_id=0)],
    )

    assert driver.list_xbot_ids() == [0, 2]


def test_hardware_driver_rejects_missing_xbot_id(monkeypatch):
    driver = _hardware_driver_with_xbots(monkeypatch, [SimpleNamespace()])

    with pytest.raises(HardwareError) as excinfo:
        driver.list_xbot_ids()

    assert excinfo.value.error_code == error_codes.DRIVER_FAILURE
    assert "missing xbot_id" in str(excinfo.value)


def test_hardware_driver_rejects_duplicate_xbot_ids(monkeypatch):
    driver = _hardware_driver_with_xbots(
        monkeypatch,
        [SimpleNamespace(xbot_id=1), SimpleNamespace(xbot_id=1)],
    )

    with pytest.raises(HardwareError) as excinfo:
        driver.list_xbot_ids()

    assert excinfo.value.error_code == error_codes.DRIVER_FAILURE
    assert "Duplicate XBot IDs" in str(excinfo.value)


def test_hardware_driver_rejects_unknown_xbot_without_index_fallback(monkeypatch):
    driver = _hardware_driver_with_xbots(monkeypatch, [SimpleNamespace(xbot_id=2)])

    with pytest.raises(ConfigurationError) as excinfo:
        driver._read_xbot(0)

    assert excinfo.value.error_code == error_codes.XBOT_NOT_FOUND
