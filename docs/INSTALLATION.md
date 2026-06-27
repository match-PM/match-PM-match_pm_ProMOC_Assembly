# Installation

## Authoritative Target Platform

This repository is maintained against:

- Ubuntu 22.04
- ROS 2 Humble
- Python 3.10

Humble workspace build and test verification is recorded for this repository's
current checked path. Some contributors may use newer Ubuntu or ROS 2
distributions locally, but those are secondary convenience environments, not
the authoritative target.

## Required Prerequisites

Before building this repository, make sure the machine already has:

- ROS 2 Humble installed
- `colcon` available
- `ros2` available
- Python 3 available

Useful quick checks:

```bash
ros2 --help
colcon --help
python3 --version
```

## Workspace Layout

Use a normal ROS workspace:

```text
<ros-workspace>/
  src/
    <this repository>
```

## Build

From the repository root:

```bash
source /opt/ros/humble/setup.bash
make build
source ../install/setup.bash
make start-mock
```

If your checkout is nested as `<ros-workspace>/src/<repo>`, source
`../../install/setup.bash` from the repository root instead.

Equivalent commands from the ROS workspace root:

```bash
source /opt/ros/humble/setup.bash
cd <ros-workspace>
colcon build --symlink-install
source install/setup.bash
```

## Planar-Motor Hardware Vendor Library

Mock mode does not require PMCLib.

Planar-motor hardware mode requires the proprietary vendor package locally at:

```text
planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib/
```

That folder is local-only and must not be committed. Python must see the parent
directory `drivers/vendor/` on `sys.path`; the runtime loader handles that when
hardware mode reaches the planar-motor driver.

If the vendor package uses .NET interop, install `pythonnet` and verify:

```bash
python3 -c 'import clr'
```

Hardware planar-motor startup does not activate XBots by default. Keep
`auto_activate` false for first hardware checks and activate explicitly only
after the status topic is healthy.

## Tests

```bash
colcon test
colcon test-result --verbose
```

## Project Checks

From the repository root:

```bash
python3 tools/check_project.py --quick
python3 tools/check_project.py --full --workspace-root <ros-workspace>
```

Optional external artifact root for read-only source workspaces:

```bash
python3 tools/check_project.py \
  --full \
  --workspace-root <ros-workspace> \
  --artifact-root <artifact-dir>
```

## About `setup/`

The [`../setup/`](../setup/) directory still contains helper scripts, but the
canonical target path for this milestone is the manual Humble workspace build
shown above. Treat the helper scripts as secondary machine-setup utilities,
not as the primary handover path.
