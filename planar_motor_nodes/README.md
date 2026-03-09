# Planar Motor Nodes

## Purpose

`planar_motor_nodes` provides mover services for XBot planar motor control
in canonical ProMOC namespaces.

## How To Run / Build

Hardware-first system run:

```bash
make doctor-hw
make hw
```

Optional simulation/mock path:

```bash
make sim
```

Direct node run in mock mode:

```bash
ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true
```

## Key APIs

Canonical namespace:

- `/promoc/mover/*`

Common services:

- `/promoc/mover/activate_xbots`
- `/promoc/mover/linear_motion_si`
- `/promoc/mover/stop_motion`
- topic: `/promoc/mover/xbot_info`

## Where To Edit

| Goal | Start Here | Then Check |
|---|---|---|
| Change motion service behavior | `planar_motor_nodes/planar_motor_nodes/services/handlers/motion.py` | `planar_motor_nodes/planar_motor_nodes/domain/logic.py` |
| Change control service behavior | `planar_motor_nodes/planar_motor_nodes/services/handlers/control.py` | `planar_motor_nodes/planar_motor_nodes/node.py` |
| Change service/topic namespace wiring | `planar_motor_nodes/planar_motor_nodes/node.py` | `planar_motor_nodes/planar_motor_nodes/services/registry.py`, `planar_motor_nodes/planar_motor_nodes/services/handlers/base.py` |
| Change parameter defaults and bounds | `planar_motor_nodes/planar_motor_nodes/config.py` | `promoc_bringup/config/mover_node_params.yaml` |
| Change PMC backend integration | `planar_motor_nodes/planar_motor_nodes/drivers/hardware.py` | `planar_motor_nodes/planar_motor_nodes/drivers/mock.py` |

## Verify Changes

```bash
make lint
make test-unit
make release-n1-check
```

Package-level tests:

```bash
colcon test --packages-select planar_motor_nodes
colcon test-result --verbose
```

## Related Docs

- Root onboarding: [`START_HERE.md`](../START_HERE.md)
- Project map: [`docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- Interfaces: [`promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md)

