# ProMOC Assembly ROS2 System

Hardware-first ROS2 repository for precision assembly with camera services, linear axes, planar motor control, and shared bringup wiring.

## Start Here

If you are new to the repository, read [`START_HERE.md`](START_HERE.md) first, then use [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) to find the right package and first file.

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

- Onboarding: [`START_HERE.md`](START_HERE.md)
- Structure map: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Setup: [`setup/README.md`](setup/README.md)
- Migration notes: [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md)
