# Path Migration Table

This table tracks runtime-package module moves for the structural refactor.
Canonical ROS service/topic namespaces remain unchanged.

## Legend

- `compat`: whether a wrapper/re-export remains at old path during migration
- `phase`: planned implementation phase

## camera_nodes

| Old path | New path | compat | phase |
|---|---|---|---|
| `camera_nodes/camera_nodes/camera_node.py` | `camera_nodes/camera_nodes/node.py` | yes | 3 |
| `camera_nodes/camera_nodes/drivers/camera_driver.py` | `camera_nodes/camera_nodes/drivers/base.py` | yes | 3 |
| `camera_nodes/camera_nodes/drivers/aravis_camera_driver.py` | `camera_nodes/camera_nodes/drivers/hardware.py` | yes | 3 |
| `camera_nodes/camera_nodes/drivers/simulated_camera_driver.py` | `camera_nodes/camera_nodes/drivers/sim.py` | yes | 3 |
| `camera_nodes/camera_nodes/services/base.py` | `camera_nodes/camera_nodes/services/handlers/base.py` | yes | 3 |
| `camera_nodes/camera_nodes/services/autofocus_handler.py` | `camera_nodes/camera_nodes/services/handlers/autofocus.py` | yes | 3 |
| `camera_nodes/camera_nodes/services/autofocus_runner.py` | `camera_nodes/camera_nodes/services/handlers/autofocus_runner.py` | yes | 3 |
| `camera_nodes/camera_nodes/services/autofocus_response.py` | `camera_nodes/camera_nodes/services/handlers/autofocus_response.py` | yes | 3 |
| `camera_nodes/camera_nodes/services/exposure_handler.py` | `camera_nodes/camera_nodes/services/handlers/exposure.py` | yes | 3 |
| `camera_nodes/camera_nodes/services/mtf_handler.py` | `camera_nodes/camera_nodes/services/handlers/mtf.py` | yes | 3 |
| `camera_nodes/camera_nodes/services/autofocus_axis_clients.py` | `camera_nodes/camera_nodes/services/clients/autofocus_axis.py` | yes | 3 |
| `camera_nodes/camera_nodes/helpers/axis_helpers.py` | `camera_nodes/camera_nodes/services/clients/axis_velocity.py` | no | 3 |
| `camera_nodes/camera_nodes/helpers/camera_format_controller.py` | `camera_nodes/camera_nodes/services/clients/camera_format.py` | no | 3 |
| `camera_nodes/camera_nodes/helpers/parameter_access.py` | `camera_nodes/camera_nodes/services/clients/parameter_access.py` | no | 3 |
| `camera_nodes/camera_nodes/helpers/focus_profile.py` | `camera_nodes/camera_nodes/domain/models.py` | no | 3 |
| `camera_nodes/camera_nodes/helpers/fly_over.py` | `camera_nodes/camera_nodes/domain/fly_over.py` | no | 3 |
| `camera_nodes/camera_nodes/helpers/image_processing.py` | `camera_nodes/camera_nodes/domain/camera_image_processing.py` | no | 3 |
| `camera_nodes/camera_nodes/helpers/mtf_param_mapping.py` | `camera_nodes/camera_nodes/adapters/mapping.py` | no | 3 |
| `camera_nodes/camera_nodes/algorithms/` | `camera_nodes/camera_nodes/domain/algorithms/` | yes (package re-export) | 3 |

## linear_axis_nodes

| Old path | New path | compat | phase |
|---|---|---|---|
| `linear_axis_nodes/linear_axis_nodes/lts300_node.py` | `linear_axis_nodes/linear_axis_nodes/node.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/drivers/linear_axis_driver.py` | `linear_axis_nodes/linear_axis_nodes/drivers/base.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/drivers/thorlabs_lts300_driver.py` | `linear_axis_nodes/linear_axis_nodes/drivers/hardware.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/drivers/simulated_linear_axis_driver.py` | `linear_axis_nodes/linear_axis_nodes/drivers/sim.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/helpers/lts300_interface.py` | `linear_axis_nodes/linear_axis_nodes/services/clients/lts300_interface.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/services/admin_callbacks.py` | `linear_axis_nodes/linear_axis_nodes/services/handlers/admin.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/services/motion_callbacks.py` | `linear_axis_nodes/linear_axis_nodes/services/handlers/motion.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/services/service_handlers.py` | `linear_axis_nodes/linear_axis_nodes/services/registry.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/services/state_store.py` | `linear_axis_nodes/linear_axis_nodes/domain/state_store.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/services/status.py` | `linear_axis_nodes/linear_axis_nodes/domain/status.py` | yes | 4 |
| `linear_axis_nodes/linear_axis_nodes/services/validation.py` | `linear_axis_nodes/linear_axis_nodes/services/validation.py` | n/a | 4 |

## planar_motor_nodes

| Old path | New path | compat | phase |
|---|---|---|---|
| `planar_motor_nodes/planar_motor_nodes/mover_node.py` | `planar_motor_nodes/planar_motor_nodes/node.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/helpers/pmc_interface.py` | `planar_motor_nodes/planar_motor_nodes/drivers/hardware.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/drivers/mock_pmclib.py` | `planar_motor_nodes/planar_motor_nodes/drivers/mock.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/helpers/mover_utils.py` | `planar_motor_nodes/planar_motor_nodes/domain/logic.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/services/base.py` | `planar_motor_nodes/planar_motor_nodes/services/handlers/base.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/services/control.py` | `planar_motor_nodes/planar_motor_nodes/services/handlers/control.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/services/motion.py` | `planar_motor_nodes/planar_motor_nodes/services/handlers/motion.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/services/motion_input.py` | `planar_motor_nodes/planar_motor_nodes/adapters/mapping.py` | yes | 5 |
| `planar_motor_nodes/planar_motor_nodes/services/service_handlers.py` | `planar_motor_nodes/planar_motor_nodes/services/registry.py` | yes | 5 |

## Entry Points and Launches (No Behavioral Change)

| Surface | Current | Target |
|---|---|---|
| `camera_nodes` console script | `camera_node = camera_nodes.camera_node:main` | unchanged name; forwards to `camera_nodes.node:main` |
| `camera_nodes` console script | `camera_simulator = camera_nodes.nodes.camera_simulator:main` | unchanged |
| `linear_axis_nodes` console script | `lts300_node = linear_axis_nodes.lts300_node:main` | unchanged name; forwards to `linear_axis_nodes.node:main` |
| `planar_motor_nodes` console script | `mover_node = planar_motor_nodes.mover_node:main` | unchanged name; forwards to `planar_motor_nodes.node:main` |
| `promoc_bringup` launches | `camera_node`, `camera_simulator`, `lts300_node`, `mover_node` | unchanged executable names |

## Import Migration Hotspots

- Replace `*.helpers.*` imports with:
  - `services.clients.*` for ROS service/client interaction utilities
  - `domain.*` for behavior/state models and domain logic
  - `adapters.*` for mapping/conversion/validation glue
- Keep compatibility imports where entrypoint or high-surface modules are used by scripts/tests.
