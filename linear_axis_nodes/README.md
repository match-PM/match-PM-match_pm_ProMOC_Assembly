# Linear Axis Nodes

## Purpose

`linear_axis_nodes` controls Thorlabs LTS300 axes and exposes canonical ROS APIs
for axis motion and status in ProMOC.

## How To Run / Build

Hardware-first system run:

```bash
make doctor-hw
make hw
```

Optional simulation path:

```bash
make sim
```

Direct node run example:

```bash
ros2 run linear_axis_nodes lts300_node --ros-args \
  -r __node:=lts300_x_axis \
  -p serial_port:=/dev/ttyUSB0 \
  -p serial_number:=45874027
```

## Key APIs

Canonical namespace:

- `/promoc/linear_axis/<axis_name>/*`

Example services for `lts300_x_axis`:

- `/promoc/linear_axis/lts300_x_axis/move_absolute`
- `/promoc/linear_axis/lts300_x_axis/move_relative`
- `/promoc/linear_axis/lts300_x_axis/home`
- topic: `/promoc/linear_axis/lts300_x_axis/position`

Release N compatibility:

- legacy service aliases under `/<axis_name>/*`
- legacy cross-axis topic aliases under `/{namespace}/<axis_name>/position`

## Where To Edit

| Goal | Start Here | Then Check |
|---|---|---|
| Change service behavior and motion rules | `linear_axis_nodes/linear_axis_nodes/lts300_service_callbacks.py` | `linear_axis_nodes/linear_axis_nodes/lts300_node.py` |
| Change service/topic namespace wiring | `linear_axis_nodes/linear_axis_nodes/lts300_node.py` | `promoc_core/promoc_core/service_alias.py` |
| Change parameter defaults and typed config | `linear_axis_nodes/linear_axis_nodes/config.py` | `promoc_bringup/config/linear_axes_params.yaml` |
| Change driver connection flow | `linear_axis_nodes/linear_axis_nodes/lts300_interface.py` | `linear_axis_nodes/linear_axis_nodes/drivers/thorlabs_lts300_driver.py` |
| Change simulation behavior | `linear_axis_nodes/linear_axis_nodes/drivers/simulated_linear_axis_driver.py` | `linear_axis_nodes/linear_axis_nodes/lts300_interface.py` |

## Verify Changes

```bash
make lint
make test-unit
make release-n-check
```

Package-level tests:

```bash
colcon test --packages-select linear_axis_nodes
colcon test-result --verbose
```

## Related Docs

- Root onboarding: [`START_HERE.md`](../START_HERE.md)
- Project map: [`docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- Interfaces: [`promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md)
