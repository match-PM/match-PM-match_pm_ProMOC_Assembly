# ProMOC Assembly

ROS 2 workspace repository for the ProMOC CS setup. The current maintained path
is a small hardware-control stack with:

- one camera node that republishes raw images and status
- two linear-axis nodes for the X and Z axes
- one planar-motor node
- one system controller that monitors device status and exposes `stop_all` and
  guarded `reset_stop`

Authoritative target platform:

- Ubuntu 22.04
- ROS 2 Humble
- Python 3.10

The recorded handover baseline includes Humble and Jazzy build/test checks plus
mock-runtime checks. See [`docs/HANDOVER_STATUS.md`](docs/HANDOVER_STATUS.md)
for the exact verification status.

## Quick Start

Expected layout:

```text
<ros-workspace>/
  src/
    match-PM-match_pm_ProMOC_Assembly/
```

Build from the ROS workspace root:

```bash
source /opt/ros/humble/setup.bash
cd <ros-workspace>
colcon build --symlink-install
source install/setup.bash
```

Keep this repository as a clean ROS 2 source checkout under `src/`. Local
virtual environments, IDE folders, agent scratch folders, and ROS build outputs
do not belong in this repository directory. Normal ROS outputs live at the
workspace root as `build/`, `install/`, and `log/`.

Convenience build from this repository root delegates the actual `colcon build`
to the workspace root:

```bash
make build
source install/setup.bash
```

## Start The Complete System

Mock bringup (no hardware needed):

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

Hardware-oriented bringup:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=hardware
```

Launch arguments:

- `camera`
- `x_axis`
- `z_axis`
- `planar_motor`
- `system_controller`
- `driver_mode`

When the camera component is enabled, the built launch interface also exposes
`camera_type` from `camera.launch.py`.

Partial example:

```bash
ros2 launch promoc_bringup system.launch.py \
  driver_mode:=mock \
  camera:=false \
  planar_motor:=false
```

## Start Individual Subsystems

Camera-only launch:

```bash
ros2 launch promoc_bringup camera.launch.py driver_mode:=mock
```

Single-device work is usually done by disabling the other components in
`system.launch.py` rather than by inventing new launch files. See
[`docs/START_HERE.md`](docs/START_HERE.md) for examples.

## Important Interfaces

- Camera topics:
  `/promoc/camera/image_raw`, `/promoc/camera/status`
- System controller:
  `/promoc/system/status`, `/promoc/system/stop_all`, `/promoc/system/reset_stop`
- Linear axes:
  `/promoc/linear_axis/lts300_x_axis/...`,
  `/promoc/linear_axis/lts300_z_axis/...`
- Planar motor:
  `/promoc/mover/xbot_info`, `/promoc/mover/...`

## Safety Note

`stop_all` and `reset_stop` are software coordination features. They are not a
hardware-certified emergency stop, do not guarantee collision avoidance, and do
not replace operator knowledge of the real setup.

## Documentation Index

- [docs/README.md](docs/README.md) -- docs index and read order
- [docs/START_HERE.md](docs/START_HERE.md) -- first build, first launch
- [docs/PACKAGES.md](docs/PACKAGES.md) -- package ownership and where to edit
- [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) -- architecture and conventions
- [setup/README.md](setup/README.md) -- installation and hardware setup
