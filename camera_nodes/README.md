# Camera Nodes

## Purpose

`camera_nodes` owns the camera runtime node and the camera-facing ROS services for autofocus, MTF measurement, ROI detection, and exposure control.

## How To Run

```bash
make hw
make camera-hw
make sim
```

## Stable Public ROS APIs

- `/promoc/camera/autofocus`
- `/promoc/camera/measure_mtf`
- `/promoc/camera/detect_rois`
- `/promoc/camera/set_exposure`

## Where To Edit Common Changes

| Goal | Open this first |
|---|---|
| Change node wiring or service registration | `camera_nodes/camera_nodes/node.py` |
| Change service registration details | `camera_nodes/camera_nodes/services/registry.py` |
| Change autofocus behavior | `camera_nodes/camera_nodes/services/handlers/autofocus.py` |
| Change MTF behavior | `camera_nodes/camera_nodes/services/handlers/mtf.py` |
| Change camera-facing service clients | `camera_nodes/camera_nodes/services/clients/` |
| Change camera drivers | `camera_nodes/camera_nodes/drivers/hardware.py` or `camera_nodes/camera_nodes/drivers/sim.py` |
| Change package-level business logic or models | `camera_nodes/camera_nodes/domain/` |
| Change conversions or response mapping | `camera_nodes/camera_nodes/adapters/` |
| Change typed config and defaults | `camera_nodes/camera_nodes/config.py`, `promoc_bringup/config/cameras/` |

Use the canonical module paths above. Compatibility wrappers may still exist for migration, but they are not the preferred edit points.

## Legacy Wrappers You May Still See

- `camera_nodes/camera_nodes/camera_node.py`: compatibility wrapper, do not extend
- `camera_nodes/camera_nodes/services/autofocus_handler.py`: compatibility wrapper, do not extend
- `camera_nodes/camera_nodes/services/mtf_handler.py`: compatibility wrapper, do not extend
- `camera_nodes/camera_nodes/services/exposure_handler.py`: compatibility wrapper, do not extend
- `camera_nodes/camera_nodes/drivers/aravis_camera_driver.py`: compatibility wrapper, do not extend
- `camera_nodes/camera_nodes/drivers/simulated_camera_driver.py`: compatibility wrapper, do not extend

## Verify Changes

```bash
make lint
make test-unit
make release-n1-check
```

Package-only check:

```bash
colcon test --packages-select camera_nodes
colcon test-result --verbose
```

## Related Docs

- onboarding: [`../docs/START_HERE.md`](../docs/START_HERE.md)
- structure map: [`../docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- camera-specific notes: [`docs/`](docs/)
