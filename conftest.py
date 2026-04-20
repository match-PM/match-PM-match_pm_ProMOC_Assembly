"""Repository-wide test bootstrap for local package imports."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOTS = {
    "promoc_core": ROOT / "promoc_core" / "promoc_core",
    "camera_nodes": ROOT / "camera_nodes" / "camera_nodes",
    "linear_axis_nodes": ROOT / "linear_axis_nodes" / "linear_axis_nodes",
    "promoc_bringup": ROOT / "promoc_bringup" / "promoc_bringup",
}


def _force_local_package(package_name: str, package_root: Path) -> None:
    """Load the concrete inner package to avoid namespace-package ambiguity."""
    parent = package_root.parent
    parent_str = str(parent)
    if parent_str not in sys.path:
        sys.path.insert(0, parent_str)

    init_file = package_root / "__init__.py"
    current = sys.modules.get(package_name)
    if current is not None and getattr(current, "__file__", None) == str(init_file):
        return

    spec = importlib.util.spec_from_file_location(
        package_name,
        init_file,
        submodule_search_locations=[str(package_root)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create import spec for {package_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)


for name, root in PACKAGE_ROOTS.items():
    _force_local_package(name, root)
