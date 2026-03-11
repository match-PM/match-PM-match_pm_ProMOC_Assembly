# linear_axis_nodes

ROS2 runtime package for the Thorlabs LTS300 linear axis.

## Start Here

Open these files in this order:

1. `linear_axis_nodes/linear_axis_nodes/node.py`
2. `linear_axis_nodes/linear_axis_nodes/services/motion.py`
3. `linear_axis_nodes/linear_axis_nodes/services/admin.py`
4. `linear_axis_nodes/linear_axis_nodes/drivers/`

## What To Edit

| Change | Start here |
| --- | --- |
| Node wiring or service registration | `linear_axis_nodes/linear_axis_nodes/node.py` |
| Motion behavior | `linear_axis_nodes/linear_axis_nodes/services/motion.py` |
| Admin or status behavior | `linear_axis_nodes/linear_axis_nodes/services/admin.py` |
| Request validation | `linear_axis_nodes/linear_axis_nodes/services/validation.py` |
| Hardware or sim backend | `linear_axis_nodes/linear_axis_nodes/drivers/` |
| Shared runtime state | `linear_axis_nodes/linear_axis_nodes/models.py` |

## Canonical Runtime Files

- `linear_axis_nodes/linear_axis_nodes/node.py`
- `linear_axis_nodes/linear_axis_nodes/config.py`
- `linear_axis_nodes/linear_axis_nodes/models.py`
- `linear_axis_nodes/linear_axis_nodes/services/`
- `linear_axis_nodes/linear_axis_nodes/drivers/`

## Stable Public ROS APIs

- `/promoc/linear_axis/<axis_name>/move_absolute`
- `/promoc/linear_axis/<axis_name>/move_relative`
- `/promoc/linear_axis/<axis_name>/home`
- `/promoc/linear_axis/<axis_name>/get_position`
- `/promoc/linear_axis/<axis_name>/get_operation_status`
- `/promoc/linear_axis/<axis_name>/set_velocity_parameters`
- `/promoc/linear_axis/<axis_name>/get_velocity_parameters`
- `/promoc/linear_axis/<axis_name>/stop`
- `/promoc/linear_axis/<axis_name>/emergency_stop`
- `/promoc/linear_axis/<axis_name>/jog_axis`

## Related Docs

- [`../docs/START_HERE.md`](../docs/START_HERE.md)
- [`../docs/PACKAGES.md`](../docs/PACKAGES.md)
- [`../docs/SYSTEM_OVERVIEW.md`](../docs/SYSTEM_OVERVIEW.md)
