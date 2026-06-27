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

The workspace root must contain this repository under `src/`.

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

## Planar-motor PMCLib checkout is unavailable

Planar-motor hardware mode depends on the proprietary PMCLib package at:

```text
planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib/
```

This directory is intentionally ignored by git because only authorized users can
place the vendor package there. Mock mode and source-level tests should work
without it.

If the error mentions `clr` or `pythonnet`, install `pythonnet` in the active
ROS environment and verify:

```bash
python3 -c 'import clr'
```

Missing PMCLib, missing `clr`, or controller connection failures should appear
on `/promoc/mover/xbot_info` as an `ERROR` device status while the node remains
alive.

## Planar motor does not activate after hardware startup

That is the safe default. Hardware startup keeps `auto_activate` false so no
activation command is sent implicitly. Check `/promoc/mover/xbot_info` first,
then call `/promoc/mover/activate_xbots` only when activation is intended.

## `z_max_accel` is accepted but not applied in hardware mode

The public service keeps `z_max_accel` for compatibility. The current PMCLib
hardware call does not expose a separate Z-acceleration parameter, so a
non-default hardware value is accepted, stored, and reported with a warning
message, but not applied to the vendor motion call.

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

## Agent, IDE, Or Virtualenv Folders Appeared In `src`

The ROS source checkout should not contain local tool folders such as:

- `.agent-local`
- `.agents`
- `.codex`
- `.venv`
- `.idea`
- `.vscode`

Remove local folders that are not active tool mountpoints. If `.agents` or
`.codex` are active mountpoints from an agent session, stop that session first;
they are not normal repository content.
