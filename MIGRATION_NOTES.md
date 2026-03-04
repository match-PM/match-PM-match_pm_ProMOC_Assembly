# Migration Notes (Release N)

Release N introduces canonical runtime, namespace, and config naming while keeping legacy aliases for one transition release.

## Launch Arguments

Canonical launch argument:
- `runtime_mode:=hardware|sim`

Legacy launch arguments remain supported in Release N and emit deprecation warnings.

| Legacy argument | Release N behavior | Canonical replacement |
|---|---|---|
| `sim_mode:=true|false` | supported, logs warning | `runtime_mode:=sim|hardware` |
| `use_simulator:=true|false` | supported where applicable, logs warning | `runtime_mode:=sim|hardware` |

## Service Namespaces

This section covers service paths and selected topic namespace changes.

### Camera

| Legacy path | Canonical path |
|---|---|
| `/promoc/camera_node/select_roi` | `/promoc/camera/select_roi` |
| `/promoc/camera_node/autofocus` | `/promoc/camera/autofocus` |
| `/promoc/camera_node/autofocus_comparison` | `/promoc/camera/autofocus_comparison` |
| `/promoc/camera_node/measure_mtf` | `/promoc/camera/measure_mtf` |
| `/promoc/camera_node/detect_rois` | `/promoc/camera/detect_rois` |
| `/promoc/camera_node/set_exposure` | `/promoc/camera/set_exposure` |

### Linear axis

| Legacy path | Canonical path |
|---|---|
| `/<axis_name>/move_absolute` | `/promoc/linear_axis/<axis_name>/move_absolute` |
| `/<axis_name>/move_relative` | `/promoc/linear_axis/<axis_name>/move_relative` |
| `/<axis_name>/home` | `/promoc/linear_axis/<axis_name>/home` |
| `/<axis_name>/get_position` | `/promoc/linear_axis/<axis_name>/get_position` |
| `/<axis_name>/set_velocity_parameters` | `/promoc/linear_axis/<axis_name>/set_velocity_parameters` |
| `/<axis_name>/get_velocity_parameters` | `/promoc/linear_axis/<axis_name>/get_velocity_parameters` |
| `/{namespace}/<axis_name>/position` | `/promoc/linear_axis/<axis_name>/position` |

### Planar motor

| Legacy path | Canonical path |
|---|---|
| `/mover_node/activate_xbots` | `/promoc/mover/activate_xbots` |
| `/mover_node/levitation_xbots` | `/promoc/mover/levitation_xbots` |
| `/mover_node/linear_motion_si` | `/promoc/mover/linear_motion_si` |
| `/mover_node/six_dof_motion` | `/promoc/mover/six_dof_motion` |
| `/mover_node/arc_motion_si` | `/promoc/mover/arc_motion_si` |
| `/mover_node/rotary_motion` | `/promoc/mover/rotary_motion` |
| `/mover_node/stop_motion` | `/promoc/mover/stop_motion` |
| `/mover_node/set_velocity_acceleration` | `/promoc/mover/set_velocity_acceleration` |
| `xbot_info` | `/promoc/mover/xbot_info` |

## Config Schema

Canonical user config schema:
- `promoc_bringup/config/user_config.v2.example.yaml`

### Key mapping (old -> new)

| Legacy key | Release N behavior | Canonical key |
|---|---|---|
| `user.name` | accepted, logs warning | `measurement.operator` |
| `user.measurement_base_path` | accepted, logs warning | `measurement.base_path` |
| `camera.mtf_csv_path` | accepted but ignored, logs warning | `mtf.debug_export_dir` |

Canonical keys:
- `runtime.mode`
- `measurement.operator`
- `measurement.base_path`

## Camera Parameter Deprecations

Deprecated parameters are still declared in Release N and should be migrated:

| Deprecated parameter | Replacement |
|---|---|
| `mtf_csv_path` | `mtf.debug_export_dir` |
| `autofocus.fly_over.step_size_fine` | `autofocus.min_step_mm` |
| `autofocus.fly_over.coarse_scan_range_mm` | autofocus request range |
| `autofocus.fly_over.fine_scan_range_mm` | `autofocus.refinement_shrink_factor` |
| `autofocus.fly_over.coarse_drop_ratio` | `autofocus.fly_over.peak_window_ratio` |
| `autofocus.fly_over.fine_drop_ratio` | `autofocus.fly_over.peak_window_ratio` |
| `autofocus.fly_over.settle_coarse_s` | `autofocus.fly_over.settle_fine_s` |

## Python Module Structure (Breaking Change)

As of **March 4, 2026**, camera internals were refactored to feature-oriented packages and legacy wrapper modules were removed.

### Canonical module roots

- `camera_nodes.services.*`
- `camera_nodes.helpers.*`

### Removed legacy module roots

- `camera_nodes.handlers.*`
- `camera_nodes.support.*`
- `camera_nodes.services` (single-file module `services.py`)

### Import mapping examples

| Old import | New import |
|---|---|
| `from camera_nodes.handlers.autofocus_handler import AutofocusHandler` | `from camera_nodes.services.autofocus_handler import AutofocusHandler` |
| `from camera_nodes.handlers.mtf_handler import MTFHandler` | `from camera_nodes.services.mtf_handler import MTFHandler` |
| `from camera_nodes.handlers.exposure_handler import ExposureHandler` | `from camera_nodes.services.exposure_handler import ExposureHandler` |
| `from camera_nodes.handlers.base import CallbackBase` | `from camera_nodes.services.base import CallbackBase` |
| `from camera_nodes.handlers.fly_over import FlyOverDetector` | `from camera_nodes.helpers.fly_over import FlyOverDetector` |
| `from camera_nodes.support.parameter_access import ParameterAccessor` | `from camera_nodes.helpers.parameter_access import ParameterAccessor` |

## Linear Axis Module Structure (Breaking Change)

As of **March 4, 2026**, linear-axis internals were split into `services/` and `helpers/`.

### Canonical module roots

- `linear_axis_nodes.services.*`
- `linear_axis_nodes.helpers.*`

### Removed legacy module files

- `linear_axis_nodes.lts300_service_callbacks`
- `linear_axis_nodes.lts300_interface`

### Import mapping examples

| Old import | New import |
|---|---|
| `from linear_axis_nodes.lts300_service_callbacks import ServiceCallbacks` | `from linear_axis_nodes.services.callbacks import ServiceCallbacks` |
| `from linear_axis_nodes.lts300_interface import Lts300Interface` | `from linear_axis_nodes.helpers.lts300_interface import Lts300Interface` |

## Release N+1 Plan

- Remove all legacy aliases.
- Remove deprecated parameter declarations and compatibility mappings.
