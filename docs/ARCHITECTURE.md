# ProMOC Repository Architecture (2026)

This document explains how the repository is structured and where to add or change functionality.

## Design Principles

- Hardware-first runtime; simulation is optional and useful for learning/debug.
- Canonical service namespaces:
  - `/promoc/camera/*`
  - `/promoc/linear_axis/*`
  - `/promoc/mover/*`
- Typed config models for node parameters (instead of loose dict access).
- Clear module boundaries: launch/wiring separated from business logic.
- Legacy aliases are kept only for migration windows and log deprecation hints.

## Package Map

| Package | Responsibility | Main Entrypoints | Depends On |
|---|---|---|---|
| `promoc_bringup` | Launch files, runtime-mode resolution, user config mapping | `launch/system.launch.py`, `launch/camera.launch.py`, `promoc_bringup/launch_utils.py` | all runtime node packages |
| `camera_nodes` | Camera control, autofocus, exposure, MTF measurement | `camera_nodes/camera_nodes/camera_node.py`, `camera_nodes/camera_nodes/services/*`, `camera_nodes/camera_nodes/helpers/*` | `promoc_assembly_interfaces`, `promoc_core` |
| `linear_axis_nodes` | LTS300 axis control and services | `linear_axis_nodes/lts300_node.py`, `lts300_interface.py`, `lts300_service_callbacks.py` | `promoc_assembly_interfaces`, `promoc_core` |
| `planar_motor_nodes` | Planar motor mover services via PMC | `planar_motor_nodes/mover_node.py`, `mover_pmc_interface.py`, `callbacks/*` | `promoc_assembly_interfaces`, `promoc_core` |
| `promoc_assembly_interfaces` | ROS2 `srv`/`msg` contracts | `srv/*`, `msg/*` | none |
| `promoc_core` | Shared validation, conversions, logging, motion helpers | `promoc_core/*` | none |
| `setup` | Environment bootstrap and install scripts | `setup/install_all.sh`, `setup/check_installation.sh` | system tools |

## Runtime Layers

1. Launch/Config Layer (`promoc_bringup`)
2. Node Orchestration Layer (`*_node.py`)
3. Service/Handler Layer (`callbacks/*`, `services/*`)
4. Driver/Hardware Layer (`drivers/*`, `*_interface.py`)
5. Shared Core Utilities (`promoc_core`)

## Typical Flows

### Hardware (official)

1. `make doctor-hw`
2. `make hw`
3. Call canonical services, for example:
   - `/promoc/camera/autofocus`
   - `/promoc/mover/activate_xbots`
   - `/promoc/linear_axis/lts300_x_axis/move_absolute`

### Simulation (learning/debug)

1. `make sim`
2. Use the same canonical service endpoints as in hardware mode.

## Where To Change What

- New launch argument or config mapping:
  - `promoc_bringup/promoc_bringup/launch_utils.py`
  - related `promoc_bringup/launch/*.launch.py`
- New service contract:
  - add/modify `promoc_assembly_interfaces/srv/*.srv`
  - then wire node callbacks in package-specific node files
- New camera behavior:
  - `camera_nodes/camera_nodes/services/*`
  - reuse `camera_nodes/camera_nodes/helpers/*` for shared helper logic
- New linear-axis behavior:
  - `linear_axis_nodes/linear_axis_nodes/lts300_service_callbacks.py`
- New mover behavior:
  - `planar_motor_nodes/planar_motor_nodes/callbacks/*`

## Beginner Reading Order

1. `START_HERE.md`
2. `docs/learning_path_en.md` or `docs/learning_path_de.md`
3. this file (`docs/ARCHITECTURE.md`)
4. package READMEs (`camera_nodes`, `linear_axis_nodes`, `planar_motor_nodes`, `promoc_bringup`)

## Quality Gate Commands

- `make format`
- `make lint`
- `make test-unit`
- `make release-n-check`
- `make check`
