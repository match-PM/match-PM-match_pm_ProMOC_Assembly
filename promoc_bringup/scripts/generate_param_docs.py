#!/usr/bin/env python3
"""Generate camera parameter documentation from `camera_nodes.config`."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
CAMERA_PKG = ROOT / "camera_nodes"
if str(CAMERA_PKG) not in sys.path:
    sys.path.insert(0, str(CAMERA_PKG))

from camera_nodes.config import (  # noqa: E402
    ACTIVE_PARAM_VALUES,
)


ESSENTIAL_PREFIXES = (
    "pixel_size_um",
    "measurement.",
    "autofocus.refinement_",
    "autofocus.min_step_mm",
    "mtf.profile",
    "mtf.use_full_frame",
    "exposure.",
)


def is_essential(param_name: str) -> bool:
    return any(param_name.startswith(prefix) for prefix in ESSENTIAL_PREFIXES)


def render_table(rows: list[tuple[str, object]]) -> str:
    lines = ["| Parameter | Default |", "|---|---|"]
    for name, default in rows:
        lines.append(f"| `{name}` | `{default}` |")
    return "\n".join(lines)


def main() -> int:
    essential = []
    advanced = []
    for name, default in ACTIVE_PARAM_VALUES:
        if is_essential(name):
            essential.append((name, default))
        else:
            advanced.append((name, default))

    doc = [
        "# Camera Parameter Reference",
        "",
        "Generated from `camera_nodes/camera_nodes/config.py`.",
        "",
        "## Minimal Required / Frequently Used",
        "",
        render_table(essential),
        "",
        "## Advanced Tuning",
        "",
        render_table(advanced),
        "",
    ]

    output_path = ROOT / "promoc_bringup" / "config" / "cameras" / "CAMERA_PARAMETERS.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(doc), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
