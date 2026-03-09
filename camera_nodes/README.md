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

Internal package layout (simplified):

- `camera_nodes/camera_nodes/node.py` (main node)
- `camera_nodes/camera_nodes/nodes/camera_simulator.py` (sim-only node)
- `camera_nodes/camera_nodes/services/` (registry, handlers, clients, validation)
- `camera_nodes/camera_nodes/domain/` (logic + models)
- `camera_nodes/camera_nodes/adapters/` (conversions + mapping + validation)

## Where To Edit

| Goal | Start Here | Then Check |
|---|---|---|
| Change service wiring and registration | `camera_nodes/camera_nodes/node.py` | `camera_nodes/camera_nodes/services/registry.py` |
| Change autofocus behavior | `camera_nodes/camera_nodes/services/handlers/autofocus.py` | `camera_nodes/camera_nodes/services/handlers/autofocus_runner.py`, `camera_nodes/camera_nodes/services/clients/autofocus_axis.py`, `camera_nodes/camera_nodes/algorithms/autofocus.py` |
| Change MTF behavior and export mapping | `camera_nodes/camera_nodes/services/handlers/mtf.py` | `camera_nodes/camera_nodes/algorithms/mtf/`, `camera_nodes/camera_nodes/adapters/mapping.py` |
| Change camera parameter model/defaults | `camera_nodes/camera_nodes/config.py` | `promoc_bringup/config/cameras/*.yaml` |
| Change hardware/sim driver behavior | `camera_nodes/camera_nodes/drivers/hardware.py` | `camera_nodes/camera_nodes/drivers/sim.py` |

## Verify Changes

```bash
make lint
make test-unit
make release-n1-check
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

