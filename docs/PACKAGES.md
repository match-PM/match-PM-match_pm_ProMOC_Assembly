# Package Guide

This page answers two questions:

1. which package owns a behavior
2. where a student should start reading before changing it

## Package Summary

| Package | Purpose | Executables | Main Config |
| --- | --- | --- | --- |
| `camera_nodes` | camera runtime for raw image republishing and status | `camera_node` | `camera_nodes/config/camera.yaml` |
| `linear_axis_nodes` | X and Z linear-axis runtime | `lts300_node` | `linear_axis_nodes/config/x_axis.yaml`, `linear_axis_nodes/config/z_axis.yaml` |
| `planar_motor_nodes` | planar-motor runtime and motion services | `mover_node` | `planar_motor_nodes/config/planar_motor.yaml` |
| `promoc_assembly_interfaces` | ROS messages and services only | none | n/a |
| `promoc_core` | shared status/errors plus optional system controller | `promoc_system_controller` | `promoc_core/config/system_controller.yaml` |
| `promoc_bringup` | launch composition and package wiring | none | camera hardware profiles |
| `promoc_simulation` | RViz/URDF assets for future richer simulation | none | `promoc_simulation/launch/display.launch.py` and URDF assets |

## Package Details

### `camera_nodes`

- Purpose: publish `/promoc/camera/image_raw` and `/promoc/camera/status`
- Public runtime surface today: raw image and status only
- Mock behavior: generates a synthetic image stream with the same public topics
- Hardware behavior: expects a real camera driver chain via `camera.launch.py`
- Limitation: camera autofocus and exposure interfaces are kept as contracts,
  but the current reduced `camera_node` does not wire those services
- Start here:
  [`../camera_nodes/README.md`](../camera_nodes/README.md)

### `linear_axis_nodes`

- Purpose: run one axis node per configured Thorlabs axis
- Public runtime surface:
  `/promoc/linear_axis/lts300_x_axis/...` and
  `/promoc/linear_axis/lts300_z_axis/...`
- Mock behavior: software-only axis driver behind the same services and topics
- Hardware behavior: expects the real axis connection details from config
- Limitation: safe motion still depends on correct homing, limits, and operator
  awareness
- Start here:
  [`../linear_axis_nodes/README.md`](../linear_axis_nodes/README.md)

### `planar_motor_nodes`

- Purpose: expose mover status plus planar-motor control and motion services
- Public runtime surface:
  `/promoc/mover/xbot_info` and `/promoc/mover/...`
- Mock behavior: software-only driver with the same ROS service names
- Hardware behavior: depends on planar-motor vendor support and connectivity
- Limitation: hardware mode needs local PMCLib under
  `drivers/vendor/pmclib/`; this path is intentionally local-only
- Start here:
  [`../planar_motor_nodes/README.md`](../planar_motor_nodes/README.md)

### `promoc_assembly_interfaces`

- Purpose: define shared ROS message and service contracts
- Current important messages:
  `DeviceStatus`, `SystemStatus`, `planar_motor/XBotInfo`
- Current important services:
  linear-axis motion/control services, planar-motor motion/control services, and
  `Stop`
- Limitation: not every historic interface is currently used by the maintained
  runtime path

### `promoc_core`

- Purpose: hold shared status/error helpers and the optional system controller
- Executable: `promoc_system_controller`
- Optional runtime surface:
  `/promoc/system/status`, `/promoc/system/stop_all`, `/promoc/system/reset_stop`
- Limitation: it is a software coordinator, not a certified safety layer
- Start here:
  [`../promoc_core/README.md`](../promoc_core/README.md)

### `promoc_bringup`

- Purpose: launch the system and connect each package to its config
- Maintained launch files:
  `system.launch.py`, `camera.launch.py`
- Limitation: old auto-moving demo paths were removed from the maintained
  beginner startup surface
- Start here:
  [`../promoc_bringup/README.md`](../promoc_bringup/README.md)

### `promoc_simulation`

- Purpose: keep RViz/URDF assets and future simulation-related material
- Current limitation: the checked mock bringup does not come from this package
- Start here:
  [`../promoc_simulation/README.md`](../promoc_simulation/README.md)

## First File To Open For Common Changes

| You want to change... | Start here |
| --- | --- |
| system composition or launch arguments | `promoc_bringup/launch/system.launch.py` |
| camera runtime behavior | `camera_nodes/camera_nodes/node.py` |
| linear-axis runtime behavior | `linear_axis_nodes/linear_axis_nodes/node.py` |
| planar-motor runtime behavior | `planar_motor_nodes/planar_motor_nodes/node.py` |
| system stop/reset behavior | `promoc_core/promoc_core/system_controller.py` |
| message or service contracts | `promoc_assembly_interfaces/msg/` or `promoc_assembly_interfaces/srv/` |

## Current Source Layout Convention

Device packages use direct imports and explicit node wiring. Package
`__init__.py` files are package markers, not public import hubs. If you are
looking for behavior, open the concrete module named in the table above rather
than relying on package-level exports.

## Read Next

- [`INTERFACES.md`](INTERFACES.md)
- [`CONFIGURATION.md`](CONFIGURATION.md)
- [`EXTENDING_THE_SYSTEM.md`](EXTENDING_THE_SYSTEM.md)
