# promoc_simulation

## Purpose

`promoc_simulation` currently stores RViz and URDF assets for visualization and
future richer simulation work.

## Current Scope

Tracked contents include:

- `launch/display.launch.py`
- `urdf/promoc.xacro`
- meshes and RViz support files

## Important Limitation

The validated mock bringup used by `tools/check_project.py --full` does not come
from this package. Mock device behavior currently lives in the runtime packages
behind `driver_mode:=mock`.

Use this package for visualization and future simulation extensions, not as the
source of truth for the checked mock system.

## Related Docs

- [`../docs/MOCK_MODE.md`](../docs/MOCK_MODE.md)
- [`../docs/EXTENDING_THE_SYSTEM.md`](../docs/EXTENDING_THE_SYSTEM.md)
