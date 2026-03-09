# Linear Axis Nodes

## Purpose

`linear_axis_nodes` owns the LTS300 runtime node, axis services, and axis-specific motion behavior.

## How To Run

```bash
make doctor-hw
make hw
make sim
```

Direct node example:

```bash
ros2 run linear_axis_nodes lts300_node --ros-args \
  -r __node:=lts300_x_axis \
  -p serial_port:=/dev/ttyUSB0 \
  -p serial_number:=45874027
```

## Stable Public ROS APIs

Namespace pattern:

- `/promoc/linear_axis/<axis_name>/*`

Common examples:

- `/promoc/linear_axis/lts300_x_axis/move_absolute`
- `/promoc/linear_axis/lts300_x_axis/move_relative`
- `/promoc/linear_axis/lts300_x_axis/home`
- `/promoc/linear_axis/lts300_x_axis/position`

## Where To Edit Common Changes

| Goal | Open this first |
|---|---|
| Change node wiring or namespace registration | `linear_axis_nodes/linear_axis_nodes/node.py` |
| Change service registration | `linear_axis_nodes/linear_axis_nodes/services/registry.py` |
| Change motion rules or request handling | `linear_axis_nodes/linear_axis_nodes/services/handlers/motion.py` |
| Change admin or status handlers | `linear_axis_nodes/linear_axis_nodes/services/handlers/admin.py` |
| Change service validation | `linear_axis_nodes/linear_axis_nodes/services/validation.py` |
| Change hardware backend behavior | `linear_axis_nodes/linear_axis_nodes/drivers/hardware.py` |
| Change simulation behavior | `linear_axis_nodes/linear_axis_nodes/drivers/sim.py` |
| Change typed config and defaults | `linear_axis_nodes/linear_axis_nodes/config.py`, `promoc_bringup/config/linear_axes_params.yaml` |

## Legacy Wrappers You May Still See

- `linear_axis_nodes/linear_axis_nodes/lts300_node.py`: compatibility wrapper, do not extend
- `linear_axis_nodes/linear_axis_nodes/services/admin_callbacks.py`: compatibility wrapper, do not extend
- `linear_axis_nodes/linear_axis_nodes/services/motion_callbacks.py`: compatibility wrapper, do not extend
- `linear_axis_nodes/linear_axis_nodes/services/service_handlers.py`: compatibility wrapper, do not extend
- `linear_axis_nodes/linear_axis_nodes/drivers/thorlabs_lts300_driver.py`: compatibility wrapper, do not extend

## Verify Changes

```bash
make lint
make test-unit
make release-n1-check
```

Package-only check:

```bash
colcon test --packages-select linear_axis_nodes
colcon test-result --verbose
```

## Related Docs

- onboarding: [`../START_HERE.md`](../START_HERE.md)
- structure map: [`../docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- interfaces: [`../promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md)
