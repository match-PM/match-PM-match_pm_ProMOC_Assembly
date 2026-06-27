# promoc_bringup

## Purpose

`promoc_bringup` owns launch composition and configuration wiring for the
current maintained startup paths.

## Main Launch Files

Maintained runtime entry points:

- `launch/system.launch.py`
- `launch/camera.launch.py`

`system.launch.py` is the canonical full-system entry point.

The launch file is intentionally flat: launch arguments and `Node(...)` actions
are named explicitly instead of being hidden behind helper factories.

## `system.launch.py` Arguments

- `driver_mode:=hardware|mock`
- `camera:=true|false`
- `x_axis:=true|false`
- `z_axis:=true|false`
- `planar_motor:=true|false`
- `system_controller:=true|false`

Because `system.launch.py` includes `camera.launch.py`, the built launch
interface also exposes `camera_type` when the camera component is enabled.

## Common Commands

Full mock system:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

Camera-only stack:

```bash
ros2 launch promoc_bringup camera.launch.py driver_mode:=mock
```

## Configuration Ownership

This package owns:

- `config/system.reference.yaml`
- `config/cameras/*.yaml`

Current source state:

- `system.launch.py` loads package-specific YAML directly
- `config/system.reference.yaml` is documentation only; it is not parsed by the
  main launch file

## Current Limitations

- hardware mode depends on vendor/device availability
- real hardware verification is not yet complete for the current simplified
  runtime

## Related Docs

- [`../docs/START_HERE.md`](../docs/START_HERE.md)
- [`../docs/CONFIGURATION.md`](../docs/CONFIGURATION.md)
- [`../docs/INTERFACES.md`](../docs/INTERFACES.md)
- [`config/README.md`](config/README.md)
