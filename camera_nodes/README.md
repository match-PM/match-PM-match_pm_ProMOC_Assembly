# Camera Nodes

## Purpose

`camera_nodes` provides camera-facing ROS services for autofocus, MTF measurement,
ROI detection, and exposure control.

## How To Run / Build

Run via system launch (hardware-first):

```bash
make hw
```

Camera-only hardware launch:

```bash
make camera-hw
```

Optional simulation path:

```bash
make sim
```

## Key APIs

Canonical services:

- `/promoc/camera/autofocus`
- `/promoc/camera/measure_mtf`
- `/promoc/camera/detect_rois`
- `/promoc/camera/set_exposure` (hardware path only)

Release N compatibility:

- legacy aliases under `/promoc/camera_node/*` remain available with deprecation warnings.

Internal package layout (simplified):

- `camera_nodes/camera_nodes/camera_node.py` (main node)
- `camera_nodes/camera_nodes/nodes/camera_simulator.py` (sim-only node)
- `camera_nodes/camera_nodes/services/` (service logic)
- `camera_nodes/camera_nodes/helpers/` (shared parameter/MTF/image-processing helpers)

## Where To Edit

| Goal | Start Here | Then Check |
|---|---|---|
| Change service wiring and registration | `camera_nodes/camera_nodes/camera_node.py` | `camera_nodes/camera_nodes/services/registry.py` |
| Change autofocus behavior | `camera_nodes/camera_nodes/services/autofocus_handler.py` | `camera_nodes/camera_nodes/algorithms/autofocus.py` |
| Change MTF behavior and export mapping | `camera_nodes/camera_nodes/services/mtf_handler.py` | `camera_nodes/camera_nodes/algorithms/mtf/`, `camera_nodes/camera_nodes/helpers/mtf_param_mapping.py` |
| Change camera parameter model/defaults | `camera_nodes/camera_nodes/config.py` | `promoc_bringup/config/cameras/*.yaml` |
| Change hardware/sim driver behavior | `camera_nodes/camera_nodes/drivers/aravis_camera_driver.py` | `camera_nodes/camera_nodes/drivers/simulated_camera_driver.py` |

## Verify Changes

```bash
make lint
make test-unit
make release-n-check
```

Package-level tests:

```bash
colcon test --packages-select camera_nodes
colcon test-result --verbose
```

## Related Docs

- Root onboarding: [`START_HERE.md`](../START_HERE.md)
- Project map: [`docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- Callback guides (EN/DE): [`camera_nodes/docs/`](docs/)
