# Interface Reference

This page lists the runtime-facing topics and services that matter for bringup,
status inspection, and basic control.

## Camera

Topics:

- `/promoc/camera/image_raw`
- `/promoc/camera/status`

Notes:

- `image_raw` is published by `camera_node`
- `status` uses `promoc_assembly_interfaces/msg/DeviceStatus`
- the current reduced camera runtime does not expose autofocus or exposure
  services

## Linear Axes

Current namespaces from source and launch configuration:

- `/promoc/linear_axis/lts300_x_axis`
- `/promoc/linear_axis/lts300_z_axis`

Published topics per axis:

- `.../position`
- `.../status`

Services per axis:

- `.../home`
- `.../move_absolute`
- `.../move_relative`
- `.../jog_axis`
- `.../stop`
- `.../emergency_stop`
- `.../get_operation_status`
- `.../get_position`
- `.../get_velocity_parameters`
- `.../set_velocity_parameters`
- `.../shutdown`

Common response fields used by the motion/control services:

- `success`
- `error_code`
- `status_message`

Additional examples:

- `get_position` also returns `axis_position`
- `get_operation_status` also returns `operation_status`
- `set_velocity_parameters` also returns the actual applied velocity values

## Planar Motor

Topic:

- `/promoc/mover/xbot_info`

Main services:

- `/promoc/mover/activate_xbots`
- `/promoc/mover/levitation_xbots`
- `/promoc/mover/linear_motion_si`
- `/promoc/mover/six_dof_motion`
- `/promoc/mover/arc_motion_si`
- `/promoc/mover/rotary_motion`
- `/promoc/mover/set_velocity_acceleration`
- `/promoc/mover/stop_motion`

`/promoc/mover/xbot_info` carries:

- position fields for X, Y, Z, RX, RY, RZ
- `xbot_state`
- embedded `device_status`

## System Controller

Topic:

- `/promoc/system/status`

Services:

- `/promoc/system/stop_all`
- `/promoc/system/reset_stop`

Both services use `promoc_assembly_interfaces/srv/Stop` and return:

- `success`
- `error_code`
- `status_message`

`/promoc/system/status` uses `SystemStatus` and includes:

- `state`
- `stop_latched`
- `all_required_present`
- `all_required_fresh`
- `error_code`
- `message`

Status freshness is determined by `status_timeout_sec` in
`promoc_core/config/system_controller.yaml`.

## Inspecting Interfaces At Runtime

```bash
ros2 topic list
ros2 service list
ros2 topic echo /promoc/system/status --once
ros2 interface show promoc_assembly_interfaces/msg/SystemStatus
ros2 interface show promoc_assembly_interfaces/srv/Stop
```
