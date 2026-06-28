# Quick Start

This page is the fastest accurate path from a fresh checkout to a running mock
system.

## 1. Understand The Layout

Expected workspace layout:

```text
<ros-workspace>/
  src/
    <this repository>
```

Repository root:

```text
<ros-workspace>/src
```

ROS workspace root:

```text
<ros-workspace>
```

The repository directory under `src/` should stay source-only. Do not keep
local `.venv`, IDE folders, agent scratch folders, or ROS `build/install/log`
outputs inside it.

## 2. Build The Workspace

From the repository root, the beginner path is:

```bash
source /opt/ros/humble/setup.bash
make build
source ../install/setup.bash
make start-mock
```

`make build` runs `colcon build --symlink-install` from the ROS workspace root,
outside this repository. That keeps `build/`, `install/`, and `log/` outside
the repository.

If your checkout is nested as `<ros-workspace>/src/<repo>`, use
`source ../../install/setup.bash` from the repository root.

Equivalent commands from the ROS workspace root:

```bash
source /opt/ros/humble/setup.bash
cd <ros-workspace>
colcon build --symlink-install
source install/setup.bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

This is the authoritative target workflow for Ubuntu 22.04, ROS 2 Humble, and
Python 3.10. Humble workspace build and test verification is recorded for the
current checked path in this repository.

## 3. Run Project Checks

From the repository root:

```bash
python3 setup/setup.py validate
```

To also rebuild the workspace and run `colcon test`:

```bash
python3 setup/setup.py validate --full
```

Default validate mode runs setup checks plus the maintained source-level test
set. Full mode also:

- rebuilds the workspace
- runs `colcon test`
- runs `colcon test-result --verbose`

Full mode does not command verified real hardware motion.

## 4. Start The Full Mock System

```bash
make start-mock
```

Equivalent ROS command:

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

`system_controller` defaults to `false`. Leave it off for the simplest device
bringup. Set `system_controller:=true` when you want the optional shared system
status plus `stop_all` and guarded `reset_stop` services.

The built launch interface also exposes `camera_type` through the included
camera launch when the camera component is enabled.

## 5. Start Partial Systems

Camera-only stack:

```bash
ros2 launch promoc_bringup camera.launch.py driver_mode:=mock
```

Only X axis:

```bash
ros2 launch promoc_bringup system.launch.py \
  driver_mode:=mock \
  camera:=false \
  z_axis:=false \
  planar_motor:=false
```

Only planar motor:

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
ros2 topic echo /promoc/camera/status --once
ros2 topic echo /promoc/camera/image_raw --once
```

Useful status topics:

- `/promoc/camera/status`
- `/promoc/linear_axis/lts300_x_axis/status`
- `/promoc/linear_axis/lts300_z_axis/status`
- `/promoc/mover/xbot_info`

## 7. Use `stop_all` And `reset_stop`

Start the optional supervisor first:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock system_controller:=true
```

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
make start-hardware
```

Equivalent ROS command:

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
