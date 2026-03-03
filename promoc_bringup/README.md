# ProMOC Bringup (Hardware-First)

This package provides launch files and runtime configuration for the ProMOC system.

`verification` integration has been removed. The launch stack now targets the production
hardware workflow directly.

## Current Internal Structure

```text
promoc_bringup/
  launch/
    system.launch.py
    camera.launch.py
    optical_measurement_system.launch.py
    planar_motor_demo.launch.py
    promoc_assembly_demo.launch.py
  promoc_bringup/
    launch_utils.py
  config/
    mover_node_params.yaml
    linear_axes_params.yaml
    cameras/*.yaml
    user_config.v2.example.yaml
```

## Main Launch Files

- `system.launch.py`:
  - full system startup
  - camera + planar motor + linear axes
  - canonical runtime argument: `runtime_mode:=hardware|sim`
- `camera.launch.py`:
  - camera stack only
- `optical_measurement_system.launch.py`:
  - camera stack + focused linear axis flow
  - no verification node
- `promoc_assembly_demo.launch.py`:
  - full demo on top of `system.launch.py`
- `planar_motor_demo.launch.py`:
  - planar motor demo path

## Change Guide (First Files To Open)

| You want to change... | Start here | Then check |
|---|---|---|
| Which nodes start in full system launch | `promoc_bringup/launch/system.launch.py` | `promoc_bringup/launch/camera.launch.py`, `promoc_bringup/launch/optical_measurement_system.launch.py` |
| Runtime mode argument handling (`runtime_mode`, legacy aliases) | `promoc_bringup/promoc_bringup/launch_utils.py` (`resolve_runtime_mode`) | all launch files that declare runtime args |
| User config schema/normalization | `promoc_bringup/promoc_bringup/launch_utils.py` (`_normalize_user_config`, `load_user_config`) | `promoc_bringup/config/user_config.v2.example.yaml`, `promoc_bringup/config/README.md` |
| Default parameters for mover/linear-axis/camera | `promoc_bringup/config/*.yaml` | corresponding node package READMEs and config dataclasses |
| Demo launch flow | `promoc_bringup/launch/promoc_assembly_demo.launch.py` | `promoc_bringup/launch/planar_motor_demo.launch.py` |

## Hardware-First Commands

```bash
make doctor-hw
make hw
make camera-hw
```

## Optional Simulation

Simulation remains available but is not a release gate:

```bash
make sim
```

## Configuration

- `config/mover_node_params.yaml`
- `config/linear_axes_params.yaml`
- `config/cameras/*.yaml`
- `config/user_config.yaml` (local override, optional)
- `config/user_config.v2.example.yaml` (canonical schema example)
