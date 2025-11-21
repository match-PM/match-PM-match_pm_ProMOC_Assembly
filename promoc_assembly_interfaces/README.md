# ProMOC Assembly Interfaces

This package contains the ROS2 interface definitions (Messages and Services) for the ProMOC Assembly system.

## 📦 Contents

### Messages (`msg/`)
- **`planar_motor/XBotInfo.msg`**: Status information for a planar motor mover.
- **`linear_axis/LinearAxisInfo.msg`**: Status information for a linear axis.

### Services (`srv/`)
- **`planar_motor/`**: Services for controlling planar motor movers (Activate, Move, Stop, etc.).
- **`linear_axis/`**: Services for controlling linear axes (Home, Move, Stop, etc.).
- **`camera/`**: Services for camera control (SetExposure, AutoFocus).

## ⚠️ Important Note
This package **only** contains interface definitions.
- Shared Python logic, error handling, and exceptions have been moved to **`promoc_core`**.
- If you are looking for `promoc_exceptions` or `error_handling`, please check the `promoc_core` package.

## 🔨 Build
This package uses `ament_cmake` and `rosidl_default_generators` to generate language-specific bindings.

```bash
colcon build --packages-select promoc_assembly_interfaces
```
