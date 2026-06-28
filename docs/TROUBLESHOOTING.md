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

## `setup/setup.py validate --full` uses the wrong workspace

Run it from a normal ROS workspace checkout:

```text
<ros-workspace>/
  src/
    <this repository>
```

`validate --full` builds and tests the workspace root inferred from that layout.
If the checkout is elsewhere, move it under `src/` or run the plain ROS commands
from the workspace root: `colcon build`, `colcon test`, and
`colcon test-result --verbose`.

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

## Linear axis hardware does not connect

Hardware mode needs `pylablib` in the active ROS Python environment:

```bash
python3 -c 'from pylablib.devices import Thorlabs'
```

For the normal setup, leave `serial_port` empty and keep the correct
`serial_number` in `x_axis.yaml` or `z_axis.yaml`. The driver scans
`/dev/ttyUSB*` and `/dev/ttyACM*`, reads each detected Thorlabs serial number,
and uses the device matching the config.

Check:

- the USB device is visible, for example with `ls /dev/ttyUSB*`
- the configured serial number matches the label/device info
- the current user has permission to access the serial device
- no other process has the Kinesis device open

Set `serial_port` only when you intentionally want to force one path.

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

## Planar motor should not activate after hardware startup

Hardware startup defaults to `auto_activate` true. Set `auto_activate` false in
the planar-motor config or launch parameters when activation should remain a
separate operator step. Check `/promoc/mover/xbot_info` before sending motion
commands.

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

If you intentionally keep outputs elsewhere, clean that custom output directory
as well.

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
