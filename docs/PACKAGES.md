# Packages

Use this page when you already know the system roughly and want to answer:

- which package owns this behavior
- which file should I open first
- what the usual structure inside a runtime package looks like

## Package Overview

| Package | Owns | Start here |
| --- | --- | --- |
| `promoc_bringup` | launch files, runtime selection, config wiring | `promoc_bringup/launch/` and [`../promoc_bringup/README.md`](../promoc_bringup/README.md) |
| `camera_nodes` | autofocus, MTF, ROI detection, exposure, camera simulator | `camera_nodes/camera_nodes/node.py` and [`../camera_nodes/README.md`](../camera_nodes/README.md) |
| `linear_axis_nodes` | LTS300 axis motion, admin, status | `linear_axis_nodes/linear_axis_nodes/node.py` and [`../linear_axis_nodes/README.md`](../linear_axis_nodes/README.md) |
| `planar_motor_nodes` | mover motion and control services | `planar_motor_nodes/planar_motor_nodes/node.py` and [`../planar_motor_nodes/README.md`](../planar_motor_nodes/README.md) |
| `promoc_assembly_interfaces` | ROS `srv` and `msg` contracts only | `promoc_assembly_interfaces/srv/`, `promoc_assembly_interfaces/msg/`, and [`../promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md) |
| `promoc_core` | shared validation, conversions, logging, errors, reusable helpers | `promoc_core/promoc_core/` and [`../promoc_core/README.md`](../promoc_core/README.md) |

## Where To Edit First

| You want to change... | Start here |
| --- | --- |
| which nodes start or how they are launched | `promoc_bringup/launch/system.launch.py` |
| camera node wiring or service registration | `camera_nodes/camera_nodes/node.py` |
| autofocus behavior | `camera_nodes/camera_nodes/services/autofocus.py` |
| MTF or ROI behavior | `camera_nodes/camera_nodes/services/mtf.py` |
| exposure behavior | `camera_nodes/camera_nodes/services/exposure.py` |
| camera hardware or simulator integration | `camera_nodes/camera_nodes/drivers/` |
| linear-axis motion behavior | `linear_axis_nodes/linear_axis_nodes/services/motion.py` |
| linear-axis admin or status behavior | `linear_axis_nodes/linear_axis_nodes/services/admin.py` |
| mover motion behavior | `planar_motor_nodes/planar_motor_nodes/services/motion.py` |
| mover control behavior | `planar_motor_nodes/planar_motor_nodes/services/control.py` |
| launch-time camera config mapping | `promoc_bringup/promoc_bringup/camera_launch_builder.py` |
| ROS interfaces | `promoc_assembly_interfaces/srv/` or `promoc_assembly_interfaces/msg/` |
| shared validation, conversions, or error handling | `promoc_core/promoc_core/` |

## Runtime Package Shape

The runtime packages use the same basic structure:

- `node.py`: ROS wiring, startup, publishers, subscribers, services
- `config.py`: parameters and typed config
- `models.py`: shared runtime state and simple data objects
- `services/`: service callbacks and feature behavior
- `drivers/`: hardware, simulator, or mock integration
- `algorithms/`: only where real algorithm code exists

This applies mainly to:

- `camera_nodes`
- `linear_axis_nodes`
- `planar_motor_nodes`

## Simple Placement Rules

- service behavior broken: start in `services/`
- hardware or SDK problem: start in `drivers/`
- startup or parameter issue: start in `node.py` or `config.py`
- shared runtime state issue: start in `models.py`
- camera analysis math issue: start in `algorithms/`

## Canonical Entry Points

Use these as the real runtime entry points:

- `camera_nodes/camera_nodes/node.py`
- `linear_axis_nodes/linear_axis_nodes/node.py`
- `planar_motor_nodes/planar_motor_nodes/node.py`

Do not add new code to old compatibility paths from earlier refactors.

## Read Next

- onboarding: [`START_HERE.md`](START_HERE.md)
- architecture and rules: [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)
- detailed package README for the package you want to change
