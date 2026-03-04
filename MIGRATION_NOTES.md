# Migration Notes (Release N+1)

Release N+1 removes all temporary compatibility aliases introduced in Release N.
Only canonical launch arguments, service namespaces, and config keys are supported.

## Launch Arguments

Canonical launch argument:
- `runtime_mode:=hardware|sim`

Removed in N+1:
- `sim_mode`
- `use_simulator` (as launch argument)

## Service Namespaces

Only canonical service/topic paths are supported.
Legacy aliases are removed and now return "not found".

### Camera

- `/promoc/camera/select_roi`
- `/promoc/camera/autofocus`
- `/promoc/camera/autofocus_comparison`
- `/promoc/camera/measure_mtf`
- `/promoc/camera/detect_rois`
- `/promoc/camera/set_exposure`

### Linear Axis

- `/promoc/linear_axis/<axis_name>/move_absolute`
- `/promoc/linear_axis/<axis_name>/move_relative`
- `/promoc/linear_axis/<axis_name>/home`
- `/promoc/linear_axis/<axis_name>/get_position`
- `/promoc/linear_axis/<axis_name>/set_velocity_parameters`
- `/promoc/linear_axis/<axis_name>/get_velocity_parameters`
- `/promoc/linear_axis/<axis_name>/position`

### Planar Motor

- `/promoc/mover/activate_xbots`
- `/promoc/mover/levitation_xbots`
- `/promoc/mover/linear_motion_si`
- `/promoc/mover/six_dof_motion`
- `/promoc/mover/arc_motion_si`
- `/promoc/mover/rotary_motion`
- `/promoc/mover/stop_motion`
- `/promoc/mover/set_velocity_acceleration`
- `/promoc/mover/xbot_info`

## Config Schema

Canonical user config schema:
- `promoc_bringup/config/user_config.v2.example.yaml`

Canonical keys:
- `runtime.mode`
- `measurement.operator`
- `measurement.base_path`
- `camera.*`
- `autofocus.*`
- `mtf.*`
- `measurement_conditions.*`

Removed compatibility keys in N+1:
- `user.name`
- `user.measurement_base_path`
- `camera.mtf_csv_path`

## Camera Parameter Contract

Deprecated camera parameter compatibility declarations/mappings were removed.
`camera_nodes/camera_nodes/config.py` now declares canonical parameters only.

## Internal Module Structure

The service/helper package restructuring introduced in Release N remains in place:

- `camera_nodes.services.*` and `camera_nodes.helpers.*`
- `linear_axis_nodes.services.*` and `linear_axis_nodes.helpers.*`
- `planar_motor_nodes.services.*` and `planar_motor_nodes.helpers.*`

## Release N+1 Verification

- `python promoc_bringup/scripts/release_n_check.py --quiet`
- `make lint`
- `make test-unit`
- ROS2 smoke on target: canonical service calls only
