# ProMOC Assembly Interfaces

## Purpose

`promoc_assembly_interfaces` contains the shared ROS 2 messages and services
used by the current ProMOC assembly packages. It should contain interface
definitions only, not runtime node logic.

## Build And Inspect

```bash
colcon build --packages-select promoc_assembly_interfaces
source install/setup.bash
ros2 interface show promoc_assembly_interfaces/msg/SystemStatus
ros2 interface show promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute
```

## Current Interface Groups

- `msg/DeviceStatus.msg` and `msg/SystemStatus.msg` for common device and
  controller state.
- `msg/linear_axis/LinearAxisInfo.msg` and `msg/planar_motor/XBotInfo.msg` for
  package-specific status payloads.
- `srv/linear_axis/*` for homing, motion, stop, and parameter services.
- `srv/planar_motor/*` for activation, levitation, movement, rotation, and
  stop services.
- `srv/camera/AutoFocus.srv` and `srv/camera/SetExposure.srv` are still
  generated for compatibility, but they are not part of the current verified
  runtime path.

## Editing Guidance

When you add, remove, or rename an interface:

1. update the `.msg` or `.srv` file;
2. update `promoc_assembly_interfaces/CMakeLists.txt`;
3. rebuild the workspace;
4. review every downstream package that imports or advertises that contract.

Treat interface removals as public API changes. If an interface might still be
used by external tooling, defer deletion until that compatibility is reviewed.

## Related Docs

- [`../docs/INTERFACES.md`](../docs/INTERFACES.md)
- [`../docs/PACKAGES.md`](../docs/PACKAGES.md)
- [`../docs/START_HERE.md`](../docs/START_HERE.md)
