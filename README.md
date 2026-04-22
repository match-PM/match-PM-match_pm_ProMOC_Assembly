<<<<<<< HEAD
# ProMOC CS Runtime

Specialized ROS2 runtime branch for the CS setup.

The official runtime core is:

- `system.launch.py`
- camera
- two linear axes
- planar motor
- future runtime nodes that plug into the same bringup structure

This branch deliberately does **not** carry the optical measurement stack from the
messstand branch. MTF services, ROI-driven MTF helpers, and the old autofocus
comparison path are not part of the maintained CS runtime.

## Explain It In Two Minutes

If you need to explain the branch quickly to a supervisor or teammate, this is
the short version:

- `promoc_bringup` starts and wires the runtime
- `camera_nodes` owns exposure control and Four-Step autofocus
- `linear_axis_nodes` owns the two Thorlabs linear axes
- `planar_motor_nodes` owns the mover and its motion services
- `promoc_assembly_interfaces` contains ROS contracts only
- `promoc_core` contains shared helper logic only

The branch is intentionally specialized. It keeps the runtime pieces needed for
the CS setup and removes the optical-measurement stack that belongs to the
messstand branch.

## Start Here

If you are new to this branch, open these pages in order:
=======
# ProMOC Assembly ROS2 System

Hardware-first ROS2 repository for precision assembly with camera services, linear axes, planar motor control, and shared bringup wiring.

## Start Here

If you are completely new to the repository, read only these two pages first:

1. [`docs/START_HERE.md`](docs/START_HERE.md)
2. [`docs/PACKAGES.md`](docs/PACKAGES.md)

That is enough for initial orientation.

If you want the fuller order after that, use this:
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

1. [`docs/START_HERE.md`](docs/START_HERE.md)
2. [`docs/PACKAGES.md`](docs/PACKAGES.md)
3. the README of the package you want to change
4. [`docs/SYSTEM_OVERVIEW.md`](docs/SYSTEM_OVERVIEW.md)

<<<<<<< HEAD
## Official Runtime Path

- hardware is the official runtime path
- simulation stays available as a secondary development path
- canonical launch argument: `runtime_mode:=hardware|sim`
- single official main start: `ros2 launch promoc_bringup system.launch.py`

## Quick Start

Build once from the repository root:
=======
If you want the full docs map first, open [`docs/README.md`](docs/README.md).

## Official Runtime Stance

- hardware is the official release path
- simulation exists for learning, debugging, and isolated development
- canonical launch argument: `runtime_mode:=hardware|sim`

## Quick Start

```bash
cd ~/ros2_ws/src
git clone <repository-url> promoc_assembly
cd promoc_assembly/setup
./install_all.sh
cd ..
source ../install/setup.bash
make doctor-hw
make hw
```

Daily repo-local workflow from the repository root:
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

```bash
make build
source install/setup.bash
```

<<<<<<< HEAD
Official hardware startup:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
```

Optional simulation startup:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=sim
```

Common camera commands:

```bash
ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure "{exposure_time: 12000.0}"
ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus "{start_position: 260.0, end_position: 290.0, focus_mode: 0, skip_flyover: false}"
```

## Runtime Architecture

`system.launch.py -> runtime nodes -> services under /promoc/...`

- `promoc_bringup` starts the runtime composition
- `camera_nodes` owns Four-Step autofocus and exposure
- `linear_axis_nodes` owns both linear axes
- `planar_motor_nodes` owns mover control and motion services
- `promoc_assembly_interfaces` contains ROS contracts only
- `promoc_core` contains shared helpers with no hardware ownership

This split is deliberate: launch files compose the system, runtime packages own
hardware behavior, interfaces stay contract-only, and shared Python helpers stay
out of the hardware packages unless they are reusable across packages.
=======
## Core Commands

```bash
make doctor-hw
make hw
make camera-hw
make sim
```

## Package Overview

- `promoc_bringup`: launch files and runtime wiring
- `camera_nodes`: autofocus, MTF, exposure, ROI services
- `linear_axis_nodes`: LTS300 axis motion and status
- `planar_motor_nodes`: mover motion and control services
- `promoc_assembly_interfaces`: ROS contracts only
- `promoc_core`: shared reusable Python logic
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

## Key Docs

- Docs index: [`docs/README.md`](docs/README.md)
- Onboarding: [`docs/START_HERE.md`](docs/START_HERE.md)
- Package guide: [`docs/PACKAGES.md`](docs/PACKAGES.md)
- System overview: [`docs/SYSTEM_OVERVIEW.md`](docs/SYSTEM_OVERVIEW.md)
- Setup: [`setup/README.md`](setup/README.md)
