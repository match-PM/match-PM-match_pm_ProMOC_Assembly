# Project Structure

Read this after `docs/START_HERE.md`.

## Official Read Order

1. `README.md`
2. `docs/START_HERE.md`
3. `docs/PROJECT_STRUCTURE.md`
4. package README for the package you want to change
5. `docs/PACKAGE_INFO.md`
6. `docs/ARCHITECTURE.md`

## Top-Level Packages

- `promoc_bringup`: launch files and startup wiring
- `camera_nodes`: camera runtime node, autofocus, MTF, exposure, simulator
- `linear_axis_nodes`: LTS300 linear-axis runtime node and services
- `planar_motor_nodes`: planar motor runtime node and services
- `promoc_assembly_interfaces`: ROS messages and services only
- `promoc_core`: shared utilities, conversions, logging, validation

## Where To Edit First

| You want to change... | Start here |
| --- | --- |
| Camera node wiring or service registration | `camera_nodes/camera_nodes/node.py` |
| Camera autofocus behavior | `camera_nodes/camera_nodes/services/autofocus.py` |
| Camera MTF behavior | `camera_nodes/camera_nodes/services/mtf.py` |
| Camera image algorithms | `camera_nodes/camera_nodes/algorithms/` |
| Linear-axis node wiring | `linear_axis_nodes/linear_axis_nodes/node.py` |
| Linear-axis motion behavior | `linear_axis_nodes/linear_axis_nodes/services/motion.py` |
| Linear-axis admin or status behavior | `linear_axis_nodes/linear_axis_nodes/services/admin.py` |
| Planar mover node wiring | `planar_motor_nodes/planar_motor_nodes/node.py` |
| Planar mover motion behavior | `planar_motor_nodes/planar_motor_nodes/services/motion.py` |
| Planar mover control behavior | `planar_motor_nodes/planar_motor_nodes/services/control.py` |
| Shared runtime state models | each package `models.py` |
| Hardware or mock behavior | each package `drivers/` |
| Launch behavior | `promoc_bringup/launch/` |
| ROS interfaces | `promoc_assembly_interfaces/` |

## Runtime Package Story

The beginner-friendly rule is the same in every runtime package:

- `node.py`: ROS wiring
- `config.py`: parameters and typed config
- `models.py`: shared runtime state and simple data types
- `services/`: feature behavior and callbacks
- `drivers/`: hardware and mock/sim communication
- `algorithms/`: only where real algorithm code exists

## Canonical Paths

Use these as the real entry points:

- `camera_nodes/camera_nodes/node.py`
- `linear_axis_nodes/linear_axis_nodes/node.py`
- `planar_motor_nodes/planar_motor_nodes/node.py`

Do not build new code in removed historical folders from older refactors. Start from the canonical paths above instead.

## Dependency Direction

The intended direction is simple:

- `node.py` wires services and drivers
- `services/` uses `drivers/`, `models.py`, and `algorithms/` when needed
- `drivers/` talks to hardware or mocks
- `promoc_core` stays reusable and node-independent
- `promoc_assembly_interfaces` stays contract-only

## Common Mistakes To Avoid

- putting feature logic straight into `node.py`
- hiding service behavior in extra wrapper layers
- mixing hardware SDK code into service files
- adding new compatibility wrappers instead of fixing the canonical path
