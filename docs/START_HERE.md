# Quick Start

This page is the fastest accurate path from a fresh checkout to a running mock
system.

## 1. Understand The Layout

Expected workspace layout:

```text
<ros-workspace>/
  src/
    match-PM-match_pm_ProMOC_Assembly/
```

Repository root:

```text
<ros-workspace>/src/match-PM-match_pm_ProMOC_Assembly
```

ROS workspace root:

```text
<ros-workspace>
```

The full project check needs the real ROS workspace root, not just the Git
repository root.

## 2. Build The Workspace

```bash
source /opt/ros/humble/setup.bash
cd <ros-workspace>
colcon build --symlink-install
source install/setup.bash
```

This is the authoritative target workflow for Ubuntu 22.04, ROS 2 Humble, and
Python 3.10. Humble workspace build and test verification is recorded for the
current checked path in this repository.

## 3. Run Project Checks

From the repository root:

```bash
python3 tools/check_project.py --quick
```

```bash
python3 tools/check_project.py \
  --full \
  --workspace-root <ros-workspace>
```

For a read-only source checkout or to keep `build/`, `install/`, and `log/`
outside the repository workspace, add:

```bash
python3 tools/check_project.py \
  --full \
  --workspace-root <ros-workspace> \
  --artifact-root <artifact-dir>
```

Quick mode is source and repository validation only. Full mode also:

- cleans prior build/test outputs in the active full-mode artifact layout
- rebuilds the workspace
- runs `colcon test`
- runs `colcon test-result --verbose`
- starts full and partial mock-system smoke checks
- verifies that those mock processes terminate

Without `--artifact-root`, the active full-mode artifact layout is the
workspace-local `build/`, `install/`, and `log/` directories.

Full mode uses mock ROS processes. It does not command verified real hardware
motion during the smoke checks.

## 4. Start The Full Mock System

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

Available launch arguments:

- `driver_mode:=hardware|mock`
- `camera:=true|false`
- `x_axis:=true|false`
- `z_axis:=true|false`
- `planar_motor:=true|false`
- `system_controller:=true|false`

The built launch interface also exposes `camera_type` through the included
camera launch when the camera component is enabled.

## 5. Start Partial Systems

Camera-only stack:

```bash
ros2 launch promoc_bringup camera.launch.py driver_mode:=mock
```

Only X axis plus system controller:

```bash
ros2 launch promoc_bringup system.launch.py \
  driver_mode:=mock \
  camera:=false \
  z_axis:=false \
  planar_motor:=false
```

Only planar motor plus system controller:

```bash
ros2 launch promoc_bringup system.launch.py \
  driver_mode:=mock \
  camera:=false \
  x_axis:=false \
  z_axis:=false
```

## 6. Inspect Topics, Services, And Status

```bash
ros2 topic list
ros2 service list
ros2 topic echo /promoc/system/status --once
ros2 topic echo /promoc/camera/status --once
ros2 topic echo /promoc/camera/image_raw --once
```

Useful status topics:

- `/promoc/system/status`
- `/promoc/camera/status`
- `/promoc/linear_axis/lts300_x_axis/status`
- `/promoc/linear_axis/lts300_z_axis/status`
- `/promoc/mover/xbot_info`

## 7. Use `stop_all` And `reset_stop`

```bash
ros2 service call /promoc/system/stop_all \
  promoc_assembly_interfaces/srv/Stop \
  "{}"
```

```bash
ros2 service call /promoc/system/reset_stop \
  promoc_assembly_interfaces/srv/Stop \
  "{}"
```

Both services return:

- `success`
- `error_code`
- `status_message`

`reset_stop` is guarded. It is rejected if required device status is missing,
stale, busy, in an error state, or otherwise not considered safe for reset.

## 8. Switch To Hardware Carefully

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=hardware
```

Hardware mode requires real device connectivity, vendor dependencies, and valid
configuration. It may start even if one device later reports an error. Use it
only if you know the setup and the risks.

## 9. Read Next

- [`INSTALLATION.md`](INSTALLATION.md)
- [`INTERFACES.md`](INTERFACES.md)
- [`CONFIGURATION.md`](CONFIGURATION.md)
- [`SAFETY.md`](SAFETY.md)
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
