# ProMOC Setup

Single canonical installation guide for this repository.

## Expected Checkout Layout

The installer assumes the repository lives inside a ROS2 workspace, for example:

```text
<workspace>/
  src/
    promoc_assembly/
```

`install_all.sh` installs dependencies from the repository, then builds the parent workspace.

## What This Folder Contains

Main scripts:

- `install_all.sh`: full install for a fresh machine
- `install_system_deps.sh`: system packages, build tools, permissions
- `install_python_deps.sh`: Python environment and Python packages
- `install_camera_aravis2.sh`: optional camera driver install
- `check_installation.sh`: quick install status check
- `validate_setup_enhanced.sh`: deeper validation and diagnostics
- `repair.sh`: rebuild or repair the Python environment

Support files:

- `dependencies.txt`: pinned Python dependency list used by the installer
- `check_dotnet_runtime.py`: .NET runtime check helper
- `test_basic_functionality.py`: basic runtime sanity checks

## Supported Base Systems

The setup scripts target:

- Ubuntu 22.04 with ROS2 Humble
- Ubuntu 24.04 with ROS2 Jazzy

## Official Install Path

From the repository root:

```bash
cd setup
./install_all.sh
```

What this does:

- checks the ROS2 environment
- installs system dependencies
- installs Python dependencies
- installs optional camera support when enabled
- runs `rosdep`
- builds the workspace
- runs validation

## After Installation

If you are back in the repository root after running `./install_all.sh`, source the parent workspace:

```bash
source ../install/setup.bash
```

Recommended first checks:

```bash
make doctor-hw
make hw
```

Optional simulation path:

```bash
make sim
```

For day-to-day development directly from the repository root, you can also use the repo-local workflow:

```bash
make build
source install/setup.bash
```

## Manual Install Path

Use this only if you need step-by-step control:

```bash
cd setup
./install_system_deps.sh
./install_python_deps.sh
./install_camera_aravis2.sh   # optional, IDS camera only
cd ..
rosdep install --from-paths . --ignore-src -y
cd ..
colcon build --symlink-install
source install/setup.bash
cd src/promoc_assembly/setup
./validate_setup_enhanced.sh
```

## Hardware-Specific Notes

### Planar Motor / PMCLib

Real planar-motor hardware needs a PMCLib wheel provided separately.

Typical install:

```bash
pip install /path/to/pmclib-*.whl
```

If PMCLib is not available, use simulation or mock-based development instead.

### Camera Driver

`install_camera_aravis2.sh` is only needed for camera hardware setups that use `camera_aravis2`.

### Permissions

Some hardware access requires group or udev changes.
If the installer changes group membership, log out and log back in before testing hardware.

## Validation And Repair

Quick status check:

```bash
cd setup
./check_installation.sh
```

Full validation:

```bash
cd setup
./validate_setup_enhanced.sh
```

Repair Python environment:

```bash
cd setup
./repair.sh
```

Force full rebuild of the Python environment:

```bash
cd setup
./repair.sh --force
```

## Common Problems

ROS2 not sourced:

```bash
source /opt/ros/jazzy/setup.bash
```

or

```bash
source /opt/ros/humble/setup.bash
```

Build tools missing:

```bash
sudo apt install python3-colcon-common-extensions
```

Permissions not applied yet:

- log out and log back in
- then rerun `./check_installation.sh`

Python environment broken:

```bash
cd setup
./repair.sh
```

## What To Read Next

- root overview: [`../README.md`](../README.md)
- docs index: [`../docs/README.md`](../docs/README.md)
- onboarding: [`../docs/START_HERE.md`](../docs/START_HERE.md)
- bringup and runtime behavior: [`../promoc_bringup/README.md`](../promoc_bringup/README.md)
