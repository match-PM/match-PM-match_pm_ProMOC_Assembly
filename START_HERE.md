# START_HERE

Primary onboarding entry for Python beginners and ROS2 newcomers.

## ROS2 Support

| Topic | Jazzy | Humble |
|---|---|---|
| Officially supported | yes | yes |
| Launch API | `runtime_mode:=hardware|sim` | `runtime_mode:=hardware|sim` |

## 1. Build

```bash
colcon build --symlink-install
source install/setup.bash
```

## 2. Choose Runtime Path

### Hardware-first (official)

```bash
make doctor-hw
make hw
```

Camera-only hardware start:

```bash
make camera-hw
```

### Simulation-first (learning/debug)

```bash
make sim
```

## 3. Canonical Service Calls

```bash
ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus \
"{start_position: 260.0, end_position: 290.0, focus_mode: 0, skip_flyover: false}"
```

```bash
ros2 service call /promoc/camera/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF \
"{auto_roi: true, target_edge: 'any'}"
```

```bash
ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure \
"{exposure_time: 12000.0}"
```

## 4. Repository Map

- Launch and runtime config: `promoc_bringup`
- Camera services and handlers: `camera_nodes` (`camera_nodes/camera_nodes/node.py`)
- Linear axis node: `linear_axis_nodes` (`linear_axis_nodes/linear_axis_nodes/node.py`)
- Planar motor mover node: `planar_motor_nodes` (`planar_motor_nodes/planar_motor_nodes/node.py`)
- Shared ROS interfaces (`srv`, `msg`): `promoc_assembly_interfaces`
- Shared Python utilities: `promoc_core`

Detailed module boundaries:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Beginner-first file map: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)

## 5. Where To Change What

If you want to implement a feature quickly, start with these package-level change guides:

- Bringup and launch wiring: [`promoc_bringup/README.md`](promoc_bringup/README.md)
- Camera behavior and services: [`camera_nodes/README.md`](camera_nodes/README.md)
- Linear-axis behavior and safety rules: [`linear_axis_nodes/README.md`](linear_axis_nodes/README.md)
- Planar-motor behavior and motion callbacks: [`planar_motor_nodes/README.md`](planar_motor_nodes/README.md)
- ROS interface contracts (`srv`, `msg`): [`promoc_assembly_interfaces/README.md`](promoc_assembly_interfaces/README.md)
- Shared core helpers (validation/logging/errors): [`promoc_core/README.md`](promoc_core/README.md)

## 6. Next Docs

- Beginner path (EN): [`docs/learning_path_en.md`](docs/learning_path_en.md)
- Beginner path (DE): [`docs/learning_path_de.md`](docs/learning_path_de.md)
- Project structure guide: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- Migration details: [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md)

## 7. Contract

Release N+1 is canonical-only. Use only:
- `runtime_mode:=hardware|sim`
- `/promoc/camera/*`
- `/promoc/linear_axis/<axis_name>/*`
- `/promoc/mover/*`
