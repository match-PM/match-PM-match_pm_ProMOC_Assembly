# ProMOC Assembly Interfaces

This package contains ROS2 interface definitions (`msg` and `srv`) used by ProMOC nodes.

## Scope

- Interface contracts only (no node runtime logic).
- Shared Python utility logic lives in `promoc_core`.
- Interface generation is handled by `rosidl_default_generators`.

## Current Internal Structure

```text
promoc_assembly_interfaces/
  msg/
    linear_axis/LinearAxisInfo.msg
    planar_motor/XBotInfo.msg
  srv/
    camera/*.srv
    linear_axis/*.srv
    planar_motor/*.srv
  CMakeLists.txt
  package.xml
```

## Interface Domains

- `srv/camera/*`: camera services (autofocus, MTF, ROI detection, exposure)
- `srv/linear_axis/*`: LTS300 axis services (move, home, stop, status)
- `srv/planar_motor/*`: mover services (activation, motion, stop, velocity)
- `msg/linear_axis/*`, `msg/planar_motor/*`: runtime status messages

## Change Guide (First Files To Open)

| You want to change... | Start here | Then check |
|---|---|---|
| Add a new service | `promoc_assembly_interfaces/srv/<domain>/<Name>.srv` | `promoc_assembly_interfaces/CMakeLists.txt` (`INTERFACE_FILES`) |
| Add a new message | `promoc_assembly_interfaces/msg/<domain>/<Name>.msg` | `promoc_assembly_interfaces/CMakeLists.txt` (`INTERFACE_FILES`) |
| Remove or rename an interface | corresponding `msg/` or `srv/` file | downstream node usages in `camera_nodes`, `linear_axis_nodes`, `planar_motor_nodes` |
| Fix build/generation issues | `promoc_assembly_interfaces/CMakeLists.txt` | `promoc_assembly_interfaces/package.xml` |
| Adjust ROS distro compatibility dependencies | `promoc_assembly_interfaces/CMakeLists.txt` (ROS_DISTRO condition) | CI workflow and target distro matrix |

## Build

```bash
colcon build --packages-select promoc_assembly_interfaces
```

## Quick Checks

```bash
ros2 interface list
```

```bash
ros2 interface show promoc_assembly_interfaces/srv/AutoFocus
```
