# ProMOC Assembly ROS2 System

Hardware-first ROS2 system for precision assembly with:
- Linear axes (Thorlabs LTS300)
- Planar motor control
- Camera autofocus and MTF measurement services

## Official Runtime Path

Hardware is the official release path.
Simulation is available for learning and debugging.

Primary onboarding:
- [`START_HERE.md`](START_HERE.md)

## Quick Start (Official Hardware)

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

## Core Commands (Unified)

```bash
make doctor-hw   # hardware readiness checks
make hw          # full system, hardware mode
make camera-hw   # camera stack, hardware mode
make sim         # optional/experimental simulation
```

Canonical launch argument:
- `runtime_mode:=hardware|sim`

## Documentation

- Architecture map: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Root onboarding flow: [`START_HERE.md`](START_HERE.md)
- Learning path (EN): [`docs/learning_path_en.md`](docs/learning_path_en.md)
- Learning path (DE): [`docs/learning_path_de.md`](docs/learning_path_de.md)
- Migration notes: [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md)
- Setup scripts: [`setup/README.md`](setup/README.md)
- Bringup/launch: [`promoc_bringup/README.md`](promoc_bringup/README.md)
- Camera package: [`camera_nodes/README.md`](camera_nodes/README.md)
- Interfaces: [`promoc_assembly_interfaces/README.md`](promoc_assembly_interfaces/README.md)
