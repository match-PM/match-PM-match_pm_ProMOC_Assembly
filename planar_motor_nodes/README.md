# planar_motor_nodes

## Purpose

`planar_motor_nodes` owns the planar-motor runtime and its ROS motion/control
services.

## Executable

- `ros2 run planar_motor_nodes mover_node`

The normal startup path is through:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

or `driver_mode:=hardware` when the real setup is available.

## Configuration

- `config/planar_motor.yaml`

Important keys:

- `driver_mode`
- `xbot_id`
- `publish_rate`
- `pmc_ip`
- `auto_activate` defaults to `false`; setting it to `true` is advanced and
  sends an activation command during startup
- workspace bounds: `x_min`, `x_max`, `y_min`, `y_max`, `z_min`, `z_max`
- tolerances
- default speed profile values:
  `default_xy_vel`, `default_xy_max_accel`, `default_z_vel`,
  `default_z_max_accel`, `default_rx_vel`, `default_ry_vel`, `default_rz_vel`

## Primary Topic

- `/promoc/mover/xbot_info`

## Primary Services

- `/promoc/mover/activate_xbots`
- `/promoc/mover/levitation_xbots`
- `/promoc/mover/linear_motion_si`
- `/promoc/mover/six_dof_motion`
- `/promoc/mover/arc_motion_si`
- `/promoc/mover/rotary_motion`
- `/promoc/mover/set_velocity_acceleration`
- `/promoc/mover/stop_motion`

## Hardware And Mock Behavior

- `driver_mode:=mock`
  uses a software-only backend for bringup and smoke testing
- `driver_mode:=hardware`
  expects planar-motor dependencies and connectivity

Hardware mode loads PMCLib lazily from the local-only vendor package:

```text
planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib/
```

Do not commit that proprietary directory. Mock mode works without it. If the
vendor package uses .NET interop, hardware mode also needs `pythonnet`/`clr`.

Hardware startup does not activate XBots by default. Use the activation service
explicitly after checking status, or set `auto_activate:=true` only when that
startup intervention is intentional.

`z_max_accel` is kept in the public speed-profile API for compatibility. The
current PMCLib hardware backend accepts and stores the value, but does not apply
a separate Z acceleration when the vendor motion call has no matching argument.

## Current Limitations

- mock mode is not a mechanical simulation
- real hardware verification is not yet complete for the current simplified
  runtime
- planar-motor hardware PMCLib loading is wired, but real controller behavior
  still needs hardware validation

## Related Docs

- [`../docs/START_HERE.md`](../docs/START_HERE.md)
- [`../docs/CONFIGURATION.md`](../docs/CONFIGURATION.md)
- [`../docs/INTERFACES.md`](../docs/INTERFACES.md)
- [`../docs/MOCK_MODE.md`](../docs/MOCK_MODE.md)
