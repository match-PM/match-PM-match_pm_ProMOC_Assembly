# ProMOC Bringup

## Purpose

`promoc_bringup` owns launch files, runtime selection, and parameter wiring for the whole system.

## What Starts Here

Primary launches:

- `launch/system.launch.py`
- `launch/camera.launch.py`
- `launch/optical_measurement_system.launch.py`
- `launch/promoc_assembly_demo.launch.py`
- `launch/planar_motor_demo.launch.py`

Canonical launch argument:

- `runtime_mode:=hardware|sim`

## How To Run

```bash
make doctor-hw
make hw
make camera-hw
make sim
```

## Where To Edit Common Changes

| Goal | Open this first |
|---|---|
| Change which nodes start | `promoc_bringup/launch/system.launch.py` |
| Change camera-only startup | `promoc_bringup/launch/camera.launch.py` |
| Change runtime-mode handling | `promoc_bringup/promoc_bringup/launch_utils.py` |
| Change camera parameter mapping | `promoc_bringup/promoc_bringup/camera_launch_builder.py` |
| Change user config loading or defaults | `promoc_bringup/promoc_bringup/launch_utils.py`, `promoc_bringup/config/` |

Keep business logic out of launch files. Launch code should compose nodes and map configuration, not implement runtime behavior.

## Verify Changes

```bash
make lint
make test-unit
make release-n1-check
```

## Related Docs

- onboarding: [`../START_HERE.md`](../START_HERE.md)
- structure map: [`../docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- bringup config docs: [`config/README.md`](config/README.md)
