# Project Structure Guide (Beginner-First, 2026)

This guide explains where things live in the repo and which files you should open first for a specific task.

## Read Order (Fastest Onboarding)

1. `START_HERE.md`
2. `docs/learning_path_en.md` or `docs/learning_path_de.md`
3. this file (`docs/PROJECT_STRUCTURE.md`)
4. `docs/ARCHITECTURE.md` for deeper boundaries

## Top-Level Map

| Path | What it owns | Open this first |
|---|---|---|
| `promoc_bringup/` | Launch files, runtime mode, config wiring | `promoc_bringup/launch/system.launch.py` |
| `camera_nodes/` | Camera node, autofocus/MTF/exposure services | `camera_nodes/camera_nodes/node.py` |
| `linear_axis_nodes/` | LTS300 axis node and axis services | `linear_axis_nodes/linear_axis_nodes/node.py` |
| `planar_motor_nodes/` | Planar motor mover node and motion services | `planar_motor_nodes/planar_motor_nodes/node.py` |
| `promoc_assembly_interfaces/` | ROS message/service contracts (`msg`, `srv`) | `promoc_assembly_interfaces/README.md` |
| `promoc_core/` | Shared utilities (validation, logging, conversions, helpers) | `promoc_core/promoc_core/` |
| `setup/` | Installation and system checks | `setup/README.md` |
| `docs/` | Onboarding and architecture docs | `docs/ARCHITECTURE.md` |

## Task-Oriented Entry Points

If you want to add or change something, start here:

| Goal | First files to open |
|---|---|
| Start/stop different node sets | `promoc_bringup/launch/system.launch.py`, `promoc_bringup/launch/camera.launch.py` |
| Add launch argument or config mapping | `promoc_bringup/promoc_bringup/launch_utils.py` |
| Add camera service behavior | `camera_nodes/camera_nodes/services/handlers/` |
| Add camera service client/wiring logic | `camera_nodes/camera_nodes/services/clients/` |
| Add camera domain logic/models | `camera_nodes/camera_nodes/domain/` |
| Add autofocus/MTF algorithm logic | `camera_nodes/camera_nodes/domain/algorithms/` (bridge) or `camera_nodes/camera_nodes/algorithms/` (implementation) |
| Add synthetic MTF validation fixtures | `camera_nodes/test/fixtures/` |
| Add linear-axis service behavior | `linear_axis_nodes/linear_axis_nodes/services/handlers/` |
| Add mover service behavior | `planar_motor_nodes/planar_motor_nodes/services/handlers/` |
| Add shared conversion/validation/helper | `promoc_core/promoc_core/` |
| Add a new ROS service contract | `promoc_assembly_interfaces/srv/` then wire in node packages |

## Standard Runtime Layout

Runtime packages (`camera_nodes`, `linear_axis_nodes`, `planar_motor_nodes`) now share a common internal shape:

- `node.py`
- `config.py`
- `services/`
  - `registry.py`
  - `handlers/`
  - `clients/`
  - `validation.py`
- `drivers/`
  - `base.py`
  - `hardware.py`
  - `sim.py` or `mock.py`
- `domain/`
  - `logic.py`
  - `models.py`
  - `algorithms/` (when needed)
- `adapters/`
  - `conversions.py`
  - `mapping.py`
  - `validation.py`

Legacy module paths (`camera_node.py`, `lts300_node.py`, `mover_node.py`, old service module names) remain as thin compatibility wrappers where needed.

## Dependency Direction (Keep It Simple)

Use this direction to avoid spaghetti:

1. `promoc_bringup` can depend on all runtime packages.
2. Runtime node packages (`camera_nodes`, `linear_axis_nodes`, `planar_motor_nodes`) depend on:
   `promoc_assembly_interfaces` + `promoc_core`.
3. `promoc_core` should stay independent from node packages.
4. `promoc_assembly_interfaces` is contract-only (`msg`/`srv`), no runtime logic.

## Quality Gate (Before Commit)

```bash
make format
make lint
make test-unit
make release-n1-check
```

## Common Beginner Mistakes

- Adding business logic into launch files instead of node/handler modules.
- Creating new legacy paths instead of canonical `/promoc/...` paths.
- Skipping interface contract updates (`srv`/`msg`) when adding new services.
- Reintroducing generic `helpers/` folders instead of placing code into `services`, `domain`, `adapters`, or `drivers`.

