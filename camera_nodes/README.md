# camera_nodes

ROS2 camera runtime package for autofocus, MTF measurement, exposure control, and the camera simulator.

## Start Here

Open these files in this order:

1. `camera_nodes/camera_nodes/node.py`
2. `camera_nodes/camera_nodes/services/autofocus.py` or `services/mtf.py`
3. `camera_nodes/camera_nodes/algorithms/`
4. `camera_nodes/camera_nodes/drivers/`

## What To Edit

| Change | Start here |
| --- | --- |
| Node wiring or service registration | `camera_nodes/camera_nodes/node.py` |
| Autofocus behavior | `camera_nodes/camera_nodes/services/autofocus.py` |
| MTF behavior | `camera_nodes/camera_nodes/services/mtf.py` |
| Exposure behavior | `camera_nodes/camera_nodes/services/exposure.py` |
| Camera algorithms | `camera_nodes/camera_nodes/algorithms/` |
| Camera hardware or sim backend | `camera_nodes/camera_nodes/drivers/` |
| Shared camera models | `camera_nodes/camera_nodes/models.py` |

## Canonical Runtime Files

- `camera_nodes/camera_nodes/node.py`
- `camera_nodes/camera_nodes/config.py`
- `camera_nodes/camera_nodes/models.py`
- `camera_nodes/camera_nodes/services/`
- `camera_nodes/camera_nodes/drivers/`
- `camera_nodes/camera_nodes/algorithms/`
- `camera_nodes/camera_nodes/sim_node.py`

## Stable Public ROS APIs

- `/promoc/camera/autofocus`
- `/promoc/camera/autofocus_comparison`
- `/promoc/camera/measure_mtf`
- `/promoc/camera/detect_rois`
- `/promoc/camera/select_roi`
- `/promoc/camera/set_exposure`

## Related Docs

- [`../docs/START_HERE.md`](../docs/START_HERE.md)
- [`../docs/PACKAGES.md`](../docs/PACKAGES.md)
- [`../docs/SYSTEM_OVERVIEW.md`](../docs/SYSTEM_OVERVIEW.md)
