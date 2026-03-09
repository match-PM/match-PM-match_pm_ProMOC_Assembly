# ProMOC Assembly Interfaces

## Purpose

`promoc_assembly_interfaces` defines shared ROS2 contracts (`srv`, `msg`) used by
camera, linear-axis, and mover nodes.

This package should contain contracts only, no runtime node logic.

## How To Run / Build

Build only this package:

```bash
colcon build --packages-select promoc_assembly_interfaces
```

Inspect generated interfaces:

```bash
ros2 interface list
ros2 interface show promoc_assembly_interfaces/srv/AutoFocus
```

## Key APIs

Interface groups:

- `srv/camera/*` (autofocus, MTF, ROI, exposure)
- `srv/linear_axis/*` (move, home, stop, status)
- `srv/planar_motor/*` (activation, motion, stop, velocity)
- `msg/linear_axis/*`, `msg/planar_motor/*` (runtime state topics)

## Where To Edit

| Goal | Start Here | Then Check |
|---|---|---|
| Add or modify a service | `promoc_assembly_interfaces/srv/<domain>/<Name>.srv` | `promoc_assembly_interfaces/CMakeLists.txt` |
| Add or modify a message | `promoc_assembly_interfaces/msg/<domain>/<Name>.msg` | `promoc_assembly_interfaces/CMakeLists.txt` |
| Fix generation or dependency wiring | `promoc_assembly_interfaces/CMakeLists.txt` | `promoc_assembly_interfaces/package.xml` |
| Roll out a contract change | changed `.srv`/`.msg` file | downstream nodes in `camera_nodes`, `linear_axis_nodes`, `planar_motor_nodes` |

## Verify Changes

```bash
colcon build --packages-select promoc_assembly_interfaces
make release-n1-check
```

## Related Docs

- Root onboarding: [`../docs/START_HERE.md`](../docs/START_HERE.md)
- Project map: [`docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- Architecture boundaries: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
