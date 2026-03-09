# Planar Motor Nodes

## Purpose

`planar_motor_nodes` owns the mover runtime node, mover services, and planar motor backend integration.

## How To Run

```bash
make doctor-hw
make hw
make sim
```

Direct mock example:

```bash
ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true
```

## Stable Public ROS APIs

- `/promoc/mover/activate_xbots`
- `/promoc/mover/linear_motion_si`
- `/promoc/mover/stop_motion`
- `/promoc/mover/xbot_info`

## Where To Edit Common Changes

| Goal | Open this first |
|---|---|
| Change node wiring or service registration | `planar_motor_nodes/planar_motor_nodes/node.py`, `planar_motor_nodes/planar_motor_nodes/services/registry.py` |
| Change motion behavior | `planar_motor_nodes/planar_motor_nodes/services/handlers/motion.py` |
| Change control behavior | `planar_motor_nodes/planar_motor_nodes/services/handlers/control.py` |
| Change package-level business logic | `planar_motor_nodes/planar_motor_nodes/domain/logic.py` |
| Change hardware integration | `planar_motor_nodes/planar_motor_nodes/drivers/hardware.py` |
| Change mock behavior | `planar_motor_nodes/planar_motor_nodes/drivers/mock.py` |
| Change typed config and limits | `planar_motor_nodes/planar_motor_nodes/config.py`, `promoc_bringup/config/mover_node_params.yaml` |

## Verify Changes

```bash
make lint
make test-unit
make release-n1-check
```

Package-only check:

```bash
colcon test --packages-select planar_motor_nodes
colcon test-result --verbose
```

## Related Docs

- onboarding: [`../START_HERE.md`](../START_HERE.md)
- structure map: [`../docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- interfaces: [`../promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md)
