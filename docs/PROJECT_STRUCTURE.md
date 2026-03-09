# Project Structure Guide

This guide answers two questions:

1. which package owns a change
2. which file should you open first

## Read Order

1. `../README.md`
2. `START_HERE.md`
3. the README of the package you will edit
4. this file
5. `ARCHITECTURE.md`

## Top-Level Package Map

| Path | What it owns | Open this first |
|---|---|---|
| `promoc_bringup/` | launch files, runtime mode, config wiring | `promoc_bringup/launch/system.launch.py` |
| `camera_nodes/` | camera node, autofocus, MTF, ROI, exposure services | `camera_nodes/camera_nodes/node.py` |
| `linear_axis_nodes/` | LTS300 axis node, motion services, axis status | `linear_axis_nodes/linear_axis_nodes/node.py` |
| `planar_motor_nodes/` | mover node, motion services, planar motor integration | `planar_motor_nodes/planar_motor_nodes/node.py` |
| `promoc_assembly_interfaces/` | ROS `srv` and `msg` contracts only | `promoc_assembly_interfaces/README.md` |
| `promoc_core/` | reusable Python logic shared by packages | `promoc_core/README.md` |
| `docs/` | onboarding, structure, architecture, migration references | `README.md` |
| `setup/` | installation scripts and environment checks | `setup/README.md` |

## Common Tasks

| Task | Start here |
|---|---|
| Change which nodes start | `promoc_bringup/launch/system.launch.py` |
| Add launch argument or runtime mapping | `promoc_bringup/promoc_bringup/launch_utils.py` |
| Change camera service wiring | `camera_nodes/camera_nodes/node.py`, `camera_nodes/camera_nodes/services/registry.py` |
| Change autofocus behavior | `camera_nodes/camera_nodes/services/handlers/autofocus.py` |
| Change MTF behavior | `camera_nodes/camera_nodes/services/handlers/mtf.py` |
| Change camera driver behavior | `camera_nodes/camera_nodes/drivers/hardware.py` or `camera_nodes/camera_nodes/drivers/sim.py` |
| Change linear-axis motion behavior | `linear_axis_nodes/linear_axis_nodes/services/handlers/motion.py` |
| Change linear-axis parameter or namespace wiring | `linear_axis_nodes/linear_axis_nodes/node.py`, `linear_axis_nodes/linear_axis_nodes/config.py` |
| Change mover motion behavior | `planar_motor_nodes/planar_motor_nodes/services/handlers/motion.py` |
| Change mover backend integration | `planar_motor_nodes/planar_motor_nodes/drivers/hardware.py` or `planar_motor_nodes/planar_motor_nodes/drivers/mock.py` |
| Add shared validation or conversion logic | `promoc_core/promoc_core/validation.py` or `promoc_core/promoc_core/conversions.py` |
| Add a new ROS contract | `promoc_assembly_interfaces/srv/` or `promoc_assembly_interfaces/msg/` |

## Standard Runtime Layout

All runtime node packages use the same internal shape:

- `node.py`
- `config.py`
- `services/`
- `drivers/`
- `domain/`
- `adapters/`

Use these folders consistently:

- `services/`: service registration, handlers, clients, request validation
- `drivers/`: hardware and sim or mock backends
- `domain/`: business logic, models, package-specific algorithms
- `adapters/`: conversions, mapping, boundary validation

Compatibility wrappers may still exist for some runtime packages, but beginner-facing edits should start from the canonical paths above.

Common examples:

- `linear_axis_nodes/linear_axis_nodes/lts300_node.py` -> use `linear_axis_nodes/linear_axis_nodes/node.py`
- `planar_motor_nodes/planar_motor_nodes/mover_node.py` -> use `planar_motor_nodes/planar_motor_nodes/node.py`

## Dependency Direction

Keep dependencies moving in this direction:

1. `promoc_bringup` may depend on runtime packages
2. runtime packages may depend on `promoc_assembly_interfaces` and `promoc_core`
3. `promoc_core` must not depend on runtime packages
4. `promoc_assembly_interfaces` stays contract-only

## Common Beginner Mistakes

- putting business logic into launch files
- editing a compatibility wrapper instead of the canonical module
- adding a generic `helpers/` folder instead of placing code into `services`, `drivers`, `domain`, or `adapters`
- changing ROS namespaces without checking documented `/promoc/...` contracts
- adding shared logic to a runtime package when it belongs in `promoc_core`
