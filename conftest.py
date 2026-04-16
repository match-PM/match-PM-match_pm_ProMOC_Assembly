"""Repository-wide test bootstrap for local package imports."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOTS = (
    ROOT / "promoc_core",
    ROOT / "camera_nodes",
    ROOT / "linear_axis_nodes",
    ROOT / "promoc_bringup",
)

for package_root in PACKAGE_ROOTS:
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)
