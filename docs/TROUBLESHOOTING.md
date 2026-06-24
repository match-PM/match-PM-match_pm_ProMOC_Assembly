# Troubleshooting

## `ros2` command not found

Source ROS 2 first:

```bash
source /opt/ros/humble/setup.bash
```

## `colcon` command not found

Install the ROS 2 colcon tooling for your machine, then verify:

```bash
colcon --help
```

## Package not found after build

You probably forgot to source the workspace:

```bash
source install/setup.bash
```

## Wrong ROS distribution

If you sourced a different ROS installation, clear that shell and source
Humble again:

```bash
source /opt/ros/humble/setup.bash
```

The authoritative target platform is ROS 2 Humble on Ubuntu 22.04. Newer
distributions may be used for local development, but they are not the primary
handover target.

## `check_project --full` cannot find the workspace root

Pass the real ROS workspace root explicitly:

```bash
python3 tools/check_project.py --full --workspace-root <ros-workspace>
```

The workspace root must contain `src/match-PM-match_pm_ProMOC_Assembly`.

## `check_project --full` should not write `build/`, `install/`, or `log/` into the workspace

Use an external artifact root:

```bash
python3 tools/check_project.py \
  --full \
  --workspace-root <ros-workspace> \
  --artifact-root <artifact-dir>
```

This keeps full-mode outputs outside the validated source workspace while still
running the same build, test, and mock-smoke checks.

## Quick check fails because the tree is dirty

Review the tracked changes first. Only use:

```bash
python3 tools/check_project.py --quick --allow-dirty
```

when you intentionally want a local development check on uncommitted work.

## Device status is missing or stale

Check:

- that the relevant node is running
- that the workspace is sourced
- that the expected topic exists
- that the system controller timeout is not being exceeded

Useful commands:

```bash
ros2 topic list
ros2 topic echo /promoc/system/status --once
```

## `reset_stop` is rejected

The controller rejects reset when required devices are missing, stale, busy, in
an error state, or otherwise not safe for reset. Inspect:

```bash
ros2 topic echo /promoc/system/status --once
ros2 topic echo /promoc/camera/status --once
ros2 topic echo /promoc/mover/xbot_info --once
```

## Hardware SDK or device dependency is unavailable

Hardware mode may start and then report device-specific failures. Verify:

- camera vendor dependencies
- axis connectivity and serial settings
- planar-motor dependencies and connectivity

If you are only trying to validate the stack, switch to:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

## External `match_pm_xBot` Gitlink is unavailable

The planar-motor area depends on the tracked external Gitlink at:

```text
planar_motor_nodes/planar_motor_nodes/drivers/match_pm_xBot
```

If the Gitlink content is missing, some hardware-oriented planar-motor work will
not be available. Do not rewrite around that dependency inside this repository.

## Mock mode was not actually selected

The current launch argument is `driver_mode`, not `runtime_mode`, `use_mock`, or
`use_simulator`:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

## No image topic appears

Check:

- `camera:=true`
- `driver_mode`
- the workspace is sourced
- camera-only bringup if you want to isolate the camera stack

```bash
ros2 launch promoc_bringup camera.launch.py driver_mode:=mock
```

## Axis movement is rejected because the axis is unhomed

Home the axis first through its namespace-specific service:

```bash
ros2 service call /promoc/linear_axis/lts300_x_axis/home \
  promoc_assembly_interfaces/srv/Home \
  "{}"
```

Use the correct X or Z namespace.

## A service reports `busy`

Wait for the device to finish or inspect its status topic. The runtime rejects
some commands while motion is already active.

## Stale `build/`, `install/`, or `log/`

Clean only the ROS workspace outputs for this workspace:

```bash
cd <ros-workspace>
rm -rf build install log
```

Then rebuild and re-source:

```bash
colcon build --symlink-install
source install/setup.bash
```

If you intentionally keep outputs outside the workspace, clean the external
artifact root you passed to `--artifact-root` instead.
