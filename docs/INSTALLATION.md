# Installation

## Verified Environment

The currently verified development environment is:

- Ubuntu 24.04
- ROS 2 Jazzy
- Linux native

The intended later target is:

- Ubuntu 22.04
- ROS 2 Humble
- Python 3.10

Humble is a target, not a completed compatibility claim.

## Required Prerequisites

Before building this repository, make sure the machine already has:

- ROS 2 Jazzy installed
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
    match-PM-match_pm_ProMOC_Assembly/
```

## Build

```bash
source /opt/ros/jazzy/setup.bash
cd <ros-workspace>
colcon build --symlink-install
source install/setup.bash
```

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

## About `setup/`

The [`../setup/`](../setup/) directory still contains helper scripts, but the
canonical verified path for this milestone is the manual Jazzy workspace build
shown above. Treat the helper scripts as secondary utilities, not as the
primary handover path.
