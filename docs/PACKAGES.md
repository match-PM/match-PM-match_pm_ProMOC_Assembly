# Packages

Use this page when you already know the system roughly and want to answer:

- which package owns this behavior
- which file should I open first
- what the usual structure inside a runtime package looks like

## Package Overview

| Package | Owns | Typical ROS API | Start here |
| --- | --- | --- | --- |
| `promoc_bringup` | launch files, runtime selection, config wiring | `ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware` | `promoc_bringup/launch/` and [`../promoc_bringup/README.md`](../promoc_bringup/README.md) |
| `camera_nodes` | Four-Step autofocus, exposure, camera simulator | `/promoc/camera/autofocus` | `camera_nodes/camera_nodes/node.py` and [`../camera_nodes/README.md`](../camera_nodes/README.md) |
| `linear_axis_nodes` | LTS300 axis motion, admin, status | `/promoc/linear_axis/<axis_name>/move_absolute` | `linear_axis_nodes/linear_axis_nodes/lts300_node.py` and [`../linear_axis_nodes/README.md`](../linear_axis_nodes/README.md) |
| `planar_motor_nodes` | mover motion and control services | `/promoc/mover/activate_xbots` | `planar_motor_nodes/planar_motor_nodes/mover_node.py` and [`../planar_motor_nodes/README.md`](../planar_motor_nodes/README.md) || `promoc_assembly_interfaces` | ROS `srv` and `msg` contracts only | `promoc_assembly_interfaces/srv/AutoFocus` | `promoc_assembly_interfaces/srv/`, `promoc_assembly_interfaces/msg/`, and [`../promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md) |
| `promoc_core` | shared validation, conversions, logging, errors, reusable helpers | no public ROS API of its own | `promoc_core/promoc_core/` and [`../promoc_core/README.md`](../promoc_core/README.md) |

## Where To Edit First

| You want to change... | Start here |
| --- | --- |
| which nodes start or how they are launched | `promoc_bringup/launch/system.launch.py` |
| camera node wiring or service registration | `camera_nodes/camera_nodes/node.py` |
| autofocus behavior | `camera_nodes/camera_nodes/services/autofocus.py` |
| exposure behavior | `camera_nodes/camera_nodes/services/exposure.py` |
| camera hardware or simulator integration | `camera_nodes/camera_nodes/drivers/` |
| linear-axis runtime behavior | `linear_axis_nodes/linear_axis_nodes/lts300_service_callbacks.py` |
| linear-axis hardware integration | `linear_axis_nodes/linear_axis_nodes/lts300_interface.py` |
| mover runtime behavior | `planar_motor_nodes/planar_motor_nodes/callbacks/` |
| mover hardware integration | `planar_motor_nodes/planar_motor_nodes/mover_pmc_interface.py` || launch-time camera config mapping | `promoc_bringup/promoc_bringup/camera_launch_builder.py` |
| ROS interfaces | `promoc_assembly_interfaces/srv/` or `promoc_assembly_interfaces/msg/` |
| shared validation, conversions, or error handling | `promoc_core/promoc_core/` |

## Runtime Package Shape

The runtime packages follow the same ownership pattern even if filenames differ:

- one main entry file wires ROS publishers, subscribers, and services
- `services/` or `callbacks/` contains feature behavior
- `drivers/` talks to hardware, sim, or mocks
- `config.py` and `models.py` exist where a package benefits from typed runtime state
- `algorithms/` exists only where real algorithm code is needed

## Simple Placement Rules

- service behavior broken: start in `services/` or `callbacks/`
- hardware or SDK problem: start in `drivers/`
- startup or parameter issue: start in the package entry file or config layer
- shared runtime state issue: start in `models.py`
- autofocus math issue: start in `algorithms/`
## Canonical Entry Points

Use these as the real runtime entry points:

- `camera_nodes/camera_nodes/node.py`
- `linear_axis_nodes/linear_axis_nodes/lts300_node.py`
- `planar_motor_nodes/planar_motor_nodes/mover_node.py`
Do not add new code to old compatibility paths from earlier refactors.

## Read Next

- onboarding: [`START_HERE.md`](START_HERE.md)
- architecture and rules: [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)
- detailed package README for the package you want to change
