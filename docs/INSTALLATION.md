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

## Linear-Axis Hardware Dependency

Mock mode does not require Thorlabs hardware dependencies.

Linear-axis hardware mode uses `pylablib` and the Thorlabs Kinesis motor API.
Verify the Python package in the active ROS environment:

```bash
python3 -c 'from pylablib.devices import Thorlabs'
```

The normal axis configs keep `serial_port` empty and select the physical axis
by `serial_number`. Hardware startup scans `/dev/ttyUSB*` and `/dev/ttyACM*`
and connects to the device whose serial number matches the X or Z config.

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

Hardware planar-motor startup activates the configured XBot by default after
the explicit PMC connection succeeds. Set `auto_activate` false for first
hardware checks when activation should remain a separate operator step.

## Tests

```bash
colcon test
colcon test-result --verbose
```

## Project Checks

From the repository root:

```bash
python3 setup/setup.py validate
```

To also rebuild the workspace and run `colcon test`:

```bash
python3 setup/setup.py validate --full
```

## About `setup/`

The [`../setup/`](../setup/) directory contains one helper CLI:

```bash
python3 setup/setup.py check
python3 setup/setup.py install --all
python3 setup/setup.py validate
python3 setup/setup.py repair
```

Treat it as a secondary machine-setup utility, not as the primary handover
path. The canonical target path for this milestone is still the manual Humble
workspace build shown above.
