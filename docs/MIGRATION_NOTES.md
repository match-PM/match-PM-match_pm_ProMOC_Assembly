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

Runtime packages were standardized to the same internal shape:

- `node.py`
- `config.py`
- `services/{registry.py,handlers/,clients/,validation.py}`
- `drivers/{base.py,hardware.py,sim.py|mock.py}`
- `domain/{logic.py,models.py,algorithms/ when needed}`
- `adapters/{conversions.py,mapping.py,validation.py}`

`helpers/` folders were removed from runtime packages.

### Module Path Migration (Old -> New)

#### camera_nodes

- `camera_nodes/camera_nodes/camera_node.py` -> `camera_nodes/camera_nodes/node.py`
- `camera_nodes/camera_nodes/drivers/camera_driver.py` -> `camera_nodes/camera_nodes/drivers/base.py`
- `camera_nodes/camera_nodes/drivers/aravis_camera_driver.py` -> `camera_nodes/camera_nodes/drivers/hardware.py`
- `camera_nodes/camera_nodes/drivers/simulated_camera_driver.py` -> `camera_nodes/camera_nodes/drivers/sim.py`
- `camera_nodes/camera_nodes/services/base.py` -> `camera_nodes/camera_nodes/services/handlers/base.py`
- `camera_nodes/camera_nodes/services/autofocus_handler.py` -> `camera_nodes/camera_nodes/services/handlers/autofocus.py`
- `camera_nodes/camera_nodes/services/autofocus_runner.py` -> `camera_nodes/camera_nodes/services/handlers/autofocus_runner.py`
- `camera_nodes/camera_nodes/services/autofocus_response.py` -> `camera_nodes/camera_nodes/services/handlers/autofocus_response.py`
- `camera_nodes/camera_nodes/services/mtf_handler.py` -> `camera_nodes/camera_nodes/services/handlers/mtf.py`
- `camera_nodes/camera_nodes/services/exposure_handler.py` -> `camera_nodes/camera_nodes/services/handlers/exposure.py`
- `camera_nodes/camera_nodes/services/autofocus_axis_clients.py` -> `camera_nodes/camera_nodes/services/clients/autofocus_axis.py`
- `camera_nodes/camera_nodes/helpers/axis_helpers.py` -> `camera_nodes/camera_nodes/services/clients/axis_velocity.py`
- `camera_nodes/camera_nodes/helpers/camera_format_controller.py` -> `camera_nodes/camera_nodes/services/clients/camera_format.py`
- `camera_nodes/camera_nodes/helpers/parameter_access.py` -> `camera_nodes/camera_nodes/services/clients/parameter_access.py`
- `camera_nodes/camera_nodes/helpers/focus_profile.py` -> `camera_nodes/camera_nodes/domain/models.py`
- `camera_nodes/camera_nodes/helpers/fly_over.py` -> `camera_nodes/camera_nodes/domain/fly_over.py`
- `camera_nodes/camera_nodes/helpers/image_processing.py` -> `camera_nodes/camera_nodes/domain/camera_image_processing.py`
- `camera_nodes/camera_nodes/helpers/mtf_param_mapping.py` -> `camera_nodes/camera_nodes/adapters/mapping.py`

#### linear_axis_nodes

- `linear_axis_nodes/linear_axis_nodes/lts300_node.py` -> `linear_axis_nodes/linear_axis_nodes/node.py`
- `linear_axis_nodes/linear_axis_nodes/drivers/linear_axis_driver.py` -> `linear_axis_nodes/linear_axis_nodes/drivers/base.py`
- `linear_axis_nodes/linear_axis_nodes/drivers/thorlabs_lts300_driver.py` -> `linear_axis_nodes/linear_axis_nodes/drivers/hardware.py`
- `linear_axis_nodes/linear_axis_nodes/drivers/simulated_linear_axis_driver.py` -> `linear_axis_nodes/linear_axis_nodes/drivers/sim.py`
- `linear_axis_nodes/linear_axis_nodes/helpers/lts300_interface.py` -> `linear_axis_nodes/linear_axis_nodes/services/clients/lts300_interface.py`
- `linear_axis_nodes/linear_axis_nodes/services/service_handlers.py` -> `linear_axis_nodes/linear_axis_nodes/services/registry.py`
- `linear_axis_nodes/linear_axis_nodes/services/admin_callbacks.py` -> `linear_axis_nodes/linear_axis_nodes/services/handlers/admin.py`
- `linear_axis_nodes/linear_axis_nodes/services/motion_callbacks.py` -> `linear_axis_nodes/linear_axis_nodes/services/handlers/motion.py`
- `linear_axis_nodes/linear_axis_nodes/services/status.py` -> `linear_axis_nodes/linear_axis_nodes/domain/status.py`
- `linear_axis_nodes/linear_axis_nodes/services/state_store.py` -> `linear_axis_nodes/linear_axis_nodes/domain/state_store.py`

#### planar_motor_nodes

- `planar_motor_nodes/planar_motor_nodes/mover_node.py` -> `planar_motor_nodes/planar_motor_nodes/node.py`
- `planar_motor_nodes/planar_motor_nodes/helpers/pmc_interface.py` -> `planar_motor_nodes/planar_motor_nodes/drivers/hardware.py`
- `planar_motor_nodes/planar_motor_nodes/drivers/mock_pmclib.py` -> `planar_motor_nodes/planar_motor_nodes/drivers/mock.py`
- `planar_motor_nodes/planar_motor_nodes/helpers/mover_utils.py` -> `planar_motor_nodes/planar_motor_nodes/domain/logic.py`
- `planar_motor_nodes/planar_motor_nodes/services/base.py` -> `planar_motor_nodes/planar_motor_nodes/services/handlers/base.py`
- `planar_motor_nodes/planar_motor_nodes/services/control.py` -> `planar_motor_nodes/planar_motor_nodes/services/handlers/control.py`
- `planar_motor_nodes/planar_motor_nodes/services/motion.py` -> `planar_motor_nodes/planar_motor_nodes/services/handlers/motion.py`
- `planar_motor_nodes/planar_motor_nodes/services/service_handlers.py` -> `planar_motor_nodes/planar_motor_nodes/services/registry.py`
- `planar_motor_nodes/planar_motor_nodes/services/motion_input.py` -> `planar_motor_nodes/planar_motor_nodes/adapters/mapping.py`

### Compatibility Notes

- ROS executable names are unchanged:
  - `camera_node`
  - `camera_simulator`
  - `lts300_node`
  - `mover_node`
- `setup.py` entry points now target canonical `node.py` modules.
- Legacy module files remain as thin wrappers where needed (old node module names and old service/driver module names).
- Canonical ROS service/topic namespaces remain unchanged (`/promoc/...`).

## Release N+1 Verification

- `python promoc_bringup/scripts/release_n_check.py --quiet`
- `make lint`
- `make test-unit`
- ROS2 smoke on target: canonical service calls only
