# Camera Nodes (Hardware-First)

This package provides camera processing services for the ProMOC system.

Official workflow is hardware-first. Simulation is optional and experimental.

## Core Services

- `/promoc/camera/autofocus`
- `/promoc/camera/measure_mtf`
- `/promoc/camera/detect_rois`
- `/promoc/camera/set_exposure` (hardware mode only)

Legacy aliases under `/promoc/camera_node/*` are still available in Release N with deprecation warnings.

## Start Commands

```bash
# Full hardware system
make hw
```

```bash
# Camera stack only (hardware mode)
make camera-hw
```

```bash
# Optional/experimental simulation
make sim
```

## Current Internal Structure

```text
camera_nodes/camera_nodes/
  camera_node.py
  services.py
  config.py
  parameter_access.py
  handlers/
    autofocus_handler.py
    exposure_handler.py
    mtf_handler.py
  algorithms/
    autofocus.py
    mtf/
  drivers/
    aravis_camera_driver.py
    simulated_camera_driver.py
camera_nodes/scripts/
  reproduce_mtf.py
```

## Change Guide (First Files To Open)

| You want to change... | Start here | Then check |
|---|---|---|
| Camera service names or routing | `camera_nodes/camera_nodes/services.py` | `camera_nodes/camera_nodes/camera_node.py` |
| Autofocus behavior | `camera_nodes/camera_nodes/handlers/autofocus_handler.py` | `camera_nodes/camera_nodes/algorithms/autofocus.py` |
| MTF behavior or CSV mapping | `camera_nodes/camera_nodes/handlers/mtf_handler.py` | `camera_nodes/camera_nodes/algorithms/mtf/`, `camera_nodes/camera_nodes/mtf_param_mapping.py` |
| Parameter defaults or validation | `camera_nodes/camera_nodes/config.py` | `camera_nodes/camera_nodes/parameter_access.py`, `promoc_bringup/config/cameras/*.yaml` |
| Real/sim camera driver behavior | `camera_nodes/camera_nodes/drivers/aravis_camera_driver.py` | `camera_nodes/camera_nodes/drivers/simulated_camera_driver.py`, `camera_nodes/camera_nodes/drivers/camera_driver.py` |

## Camera Setup Notes

1. Ensure `camera_aravis2` is installed (via `dependencies.repos` + setup scripts).
2. Check camera visibility:
   - `arv-tool-0.8`
3. Check permissions for IDS USB3 cameras (udev + user groups).

## Callback User Guides

- German: [`docs/callbacks_user_guide_de.md`](docs/callbacks_user_guide_de.md)
- English: [`docs/callbacks_user_guide_en.md`](docs/callbacks_user_guide_en.md)
