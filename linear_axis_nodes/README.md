# linear_axis_nodes

## Purpose

`linear_axis_nodes` owns the X and Z linear-axis runtime.

One executable is reused for both axes:

- `lts300_x_axis`
- `lts300_z_axis`

The difference comes from the loaded parameter file and the launched node name.

## Executable

- `ros2 run linear_axis_nodes lts300_node`

The normal startup path is through `promoc_bringup/system.launch.py`, which
starts one node with `x_axis.yaml` and one with `z_axis.yaml`.

Driver selection is explicit in `linear_axis_nodes/node.py`:
`driver_mode:=mock` uses `MockLinearAxisDriver`, `driver_mode:=hardware`
uses the Thorlabs hardware driver. Invalid values are rejected. There is no
package-level driver factory.

## Configuration

- `config/x_axis.yaml`
- `config/z_axis.yaml`

Important keys:

- `axis_id`
- `driver_mode`
- `serial_number`
- `serial_port`
- `min_position`
- `max_position`
- `default_velocity`
- `default_acceleration`
- `movement_timeout`
- `homing_timeout`
- `state_publish_rate_hz`

## Primary Topics

Per axis:

- `/promoc/linear_axis/lts300_x_axis/position`
- `/promoc/linear_axis/lts300_x_axis/status`
- `/promoc/linear_axis/lts300_z_axis/position`
- `/promoc/linear_axis/lts300_z_axis/status`

## Primary Services

Per axis:

- `move_absolute`
- `move_relative`
- `home`
- `jog_axis`
- `stop`
- `emergency_stop`
- `get_operation_status`
- `get_position`
- `get_velocity_parameters`
- `set_velocity_parameters`
- `shutdown`

See [`../docs/INTERFACES.md`](../docs/INTERFACES.md) for the full namespaces.

## Hardware And Mock Behavior

- `driver_mode:=mock`
  uses a software-only axis backend with the same ROS surface
- `driver_mode:=hardware`
  uses the real axis connection settings from the config file

## Current Limitations

- correct homing is still required for safe work
- local soft limits are configuration-based, not certified machine protection
- real hardware validation is not yet complete for the current simplified
  runtime

## Related Docs

- [`../docs/START_HERE.md`](../docs/START_HERE.md)
- [`../docs/CONFIGURATION.md`](../docs/CONFIGURATION.md)
- [`../docs/INTERFACES.md`](../docs/INTERFACES.md)
- [`../docs/SAFETY.md`](../docs/SAFETY.md)
