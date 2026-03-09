# ProMOC Assembly ROS2 System

Hardware-first ROS2 repository for precision assembly with camera services, linear axes, planar motor control, and shared bringup wiring.

## Start Here

If you are new to the repository, use this order:

1. [`docs/START_HERE.md`](docs/START_HERE.md)
2. [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
3. the README of the package you want to change

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
source install/setup.bash
make doctor-hw
make hw
```

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

## Key Docs

- Docs index: [`docs/README.md`](docs/README.md)
- Onboarding: [`docs/START_HERE.md`](docs/START_HERE.md)
- Structure map: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Setup: [`setup/README.md`](setup/README.md)
- Migration notes: [`docs/MIGRATION_NOTES.md`](docs/MIGRATION_NOTES.md)
