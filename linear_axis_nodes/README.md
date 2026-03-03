# Linear Axis Nodes

ROS2 package for controlling Thorlabs LTS300 stages in ProMOC.

This package exposes canonical services under:
- `/promoc/linear_axis/<axis_name>/*`

Release N also keeps legacy aliases for migration:
- `/<axis_name>/*`
- `/{namespace}/<axis_name>/position`

## Main Entry Point

- Node executable: `lts300_node`
- Typical node names:
  - `lts300_x_axis`
  - `lts300_z_axis`

## Current Internal Structure

```text
linear_axis_nodes/linear_axis_nodes/
  lts300_node.py
  config.py
  lts300_interface.py
  lts300_service_callbacks.py
  drivers/
    linear_axis_driver.py
    thorlabs_lts300_driver.py
  simulated_linear_axis_driver.py
```

## Change Guide (First Files To Open)

| You want to change... | Start here | Then check |
|---|---|---|
| Service behavior (validation, motion rules) | `linear_axis_nodes/linear_axis_nodes/lts300_service_callbacks.py` | `linear_axis_nodes/linear_axis_nodes/lts300_node.py` |
| Service/topic namespace wiring | `linear_axis_nodes/linear_axis_nodes/lts300_node.py` | `promoc_bringup/launch/system.launch.py` |
| Parameter defaults and typed config | `linear_axis_nodes/linear_axis_nodes/config.py` | `linear_axis_nodes/linear_axis_nodes/lts300_node.py`, `promoc_bringup/config/linear_axes_params.yaml` |
| Hardware communication flow | `linear_axis_nodes/linear_axis_nodes/lts300_interface.py` | `linear_axis_nodes/linear_axis_nodes/drivers/thorlabs_lts300_driver.py` |
| Simulation behavior | `linear_axis_nodes/linear_axis_nodes/drivers/simulated_linear_axis_driver.py` | `linear_axis_nodes/linear_axis_nodes/lts300_interface.py` |

## Quick Start

Hardware-first (recommended):

```bash
make doctor-hw
make hw
```

Simulation:

```bash
make sim
```

Direct node run (example):

```bash
ros2 run linear_axis_nodes lts300_node --ros-args \
  -r __node:=lts300_x_axis \
  -p serial_port:=/dev/ttyUSB0 \
  -p serial_number:=45874027
```

## Canonical Services

Examples for `lts300_x_axis`:

```bash
ros2 service call /promoc/linear_axis/lts300_x_axis/move_absolute \
  promoc_assembly_interfaces/srv/MoveAbsolute "{axis_position: 50.0}"
```

```bash
ros2 service call /promoc/linear_axis/lts300_x_axis/move_relative \
  promoc_assembly_interfaces/srv/MoveRelative "{axis_distance: 10.0}"
```

```bash
ros2 service call /promoc/linear_axis/lts300_x_axis/home \
  promoc_assembly_interfaces/srv/Home "{}"
```

```bash
ros2 topic echo /promoc/linear_axis/lts300_x_axis/position
```

## Parameters

Important ROS parameters:
- `use_sim_time`
- `serial_port`
- `serial_number`
- `collision_threshold`
- `max_position`
- `min_position`
- `max_single_move`
- `homing_timeout`
- `velocity_conversion_factor`
- `position_poll_interval_s`

Primary config file:
- `promoc_bringup/config/linear_axes_params.yaml`

## Safety Notes

- Collision checks are performed using the other axis position topic.
- Soft limits are enforced in service callbacks.
- Use homing before precision moves after startup.

## Development and Tests

Run package tests:

```bash
colcon test --packages-select linear_axis_nodes
colcon test-result --verbose
```

Repository-level fast checks:

```bash
make lint
make test-unit
make release-n-check
```

## Troubleshooting

Connection problems:
- Verify USB device visibility (`/dev/ttyUSB*`).
- Check user permissions (dialout/udev on Linux).
- Verify configured `serial_number` matches hardware.

Service issues:
- Confirm node name (`ros2 node list`).
- Confirm canonical service names (`ros2 service list | grep /promoc/linear_axis`).
