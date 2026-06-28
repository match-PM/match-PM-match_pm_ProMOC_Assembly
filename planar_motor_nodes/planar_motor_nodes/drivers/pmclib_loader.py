"""Load the local PMCLib vendor package."""

from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType


VENDOR_DIR = Path(__file__).resolve().with_name("vendor")
PMCLIB_DIR = VENDOR_DIR / "pmclib"


def load_pmclib() -> tuple[ModuleType, ModuleType]:
    """Return ``(system_commands, xbot_commands)`` from ``drivers/vendor/pmclib``."""
    if not PMCLIB_DIR.exists():
        raise ImportError(
            "Planar-motor hardware mode requires PMCLib at "
            f"{PMCLIB_DIR}. Place the proprietary vendor package there; "
            "mock mode works without it."
        )
    vendor_text = str(VENDOR_DIR)
    if vendor_text not in sys.path:
        sys.path.insert(0, vendor_text)

    try:
        from pmclib import system_commands, xbot_commands
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
                "Planar-motor hardware mode requires PMCLib at "
                f"{PMCLIB_DIR}. Place the proprietary vendor package there; "
                "mock mode works without it."
            ) from exc
        raise ImportError(
            f"PMCLib import failed because Python module '{missing_name}' is missing."
        ) from exc

    return system_commands, xbot_commands
