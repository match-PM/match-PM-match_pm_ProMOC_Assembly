# planar_motor_nodes

ROS2 runtime package for planar motor motion and control.

## Start Here

Open these files in this order:

1. `planar_motor_nodes/planar_motor_nodes/node.py`
2. `planar_motor_nodes/planar_motor_nodes/services/motion.py`
3. `planar_motor_nodes/planar_motor_nodes/services/control.py`
4. `planar_motor_nodes/planar_motor_nodes/services/status.py`
5. `planar_motor_nodes/planar_motor_nodes/drivers/`

## What To Edit

| Change | Start here |
| --- | --- |
| Node wiring or service registration | `planar_motor_nodes/planar_motor_nodes/node.py` |
| Motion behavior | `planar_motor_nodes/planar_motor_nodes/services/motion.py` |
| Control behavior | `planar_motor_nodes/planar_motor_nodes/services/control.py` |
| Position/status helper behavior | `planar_motor_nodes/planar_motor_nodes/services/status.py` |
| Request normalization | `planar_motor_nodes/planar_motor_nodes/services/motion_input.py` |
| Hardware or mock backend | `planar_motor_nodes/planar_motor_nodes/drivers/` |
| Shared runtime models | `planar_motor_nodes/planar_motor_nodes/models.py` |

## Canonical Runtime Files

- `planar_motor_nodes/planar_motor_nodes/node.py`
- `planar_motor_nodes/planar_motor_nodes/config.py`
- `planar_motor_nodes/planar_motor_nodes/models.py`
- `planar_motor_nodes/planar_motor_nodes/services/`
- `planar_motor_nodes/planar_motor_nodes/drivers/`

## Stable Public ROS APIs

- `/promoc/mover/linear_motion_si`
- `/promoc/mover/six_dof_motion`
- `/promoc/mover/activate_xbots`
- `/promoc/mover/levitation_xbots`
- `/promoc/mover/arc_motion_si`
- `/promoc/mover/stop_motion`
- `/promoc/mover/rotary_motion`
- `/promoc/mover/set_velocity_acceleration`

## Related Docs

- `docs/START_HERE.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/PACKAGE_INFO.md`
- `docs/ARCHITECTURE.md`
