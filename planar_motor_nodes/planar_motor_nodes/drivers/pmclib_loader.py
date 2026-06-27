"""Lazy PMCLib loader for planar-motor hardware mode."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from types import ModuleType


@dataclass(frozen=True)
class PMCLibModules:
    """Loaded PMCLib modules plus a diagnostic source string."""

    pmc_types: ModuleType
    system_commands: ModuleType
    xbot_commands: ModuleType
    source: str


def _vendor_parent() -> Path:
    return Path(__file__).resolve().with_name("vendor")


def _ensure_vendor_parent_on_path(vendor_parent: Path) -> None:
    vendor_parent_text = str(vendor_parent)
    if vendor_parent.exists() and vendor_parent_text not in sys.path:
        sys.path.insert(0, vendor_parent_text)


def load_pmclib() -> PMCLibModules:
    """Load PMCLib only when hardware mode actually needs it.

    The local proprietary checkout is expected at ``drivers/vendor/pmclib``.
    Python must see ``drivers/vendor`` on ``sys.path`` because PMCLib imports
    itself as ``pmclib`` internally.
    """

    vendor_parent = _vendor_parent()
    local_pmclib = vendor_parent / "pmclib"
    _ensure_vendor_parent_on_path(vendor_parent)

    try:
        from pmclib import pmc_types, system_commands, xbot_commands
    except ModuleNotFoundError as exc:
        missing_name = exc.name or ""
        if missing_name in {"clr", "pythonnet"}:
            raise ImportError(
                "Planar-motor hardware mode requires pythonnet/clr for PMCLib. "
                "Install pythonnet in the ROS environment and verify "
                "`python3 -c 'import clr'` succeeds."
            ) from exc
        if missing_name == "pmclib":
            raise ImportError(
                "Planar-motor hardware mode requires the local PMCLib checkout at "
                f"{local_pmclib}. Place the proprietary vendor package there; "
                "mock mode works without it."
            ) from exc
        raise ImportError(
            f"PMCLib import failed because Python module '{missing_name}' is missing."
        ) from exc

    source = str(local_pmclib) if local_pmclib.exists() else "installed pmclib"
    return PMCLibModules(
        pmc_types=pmc_types,
        system_commands=system_commands,
        xbot_commands=xbot_commands,
        source=source,
    )
