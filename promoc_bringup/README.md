# ProMOC Bringup

## Purpose

`promoc_bringup` owns launch files, runtime selection, and parameter wiring for the whole system.

## Official Launches

Use these for normal startup and development:

- `launch/system.launch.py`
- `launch/camera.launch.py`

Use this only for the optical-measurement workflow:

- `launch/optical_measurement_system.launch.py`

## Examples And Compatibility

These files are not the primary system entry points:

- `launch/promoc_assembly_demo.launch.py`
- `launch/planar_motor_demo.launch.py`
- `launch/assembly_camera.launch.py` (deprecated compatibility wrapper for `camera.launch.py`)

The `unified_demo` node is an optional demo runner. It is not the canonical system orchestrator or the normal startup path.

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
| Change optical-measurement startup | `promoc_bringup/launch/optical_measurement_system.launch.py` |
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

- onboarding: [`../docs/START_HERE.md`](../docs/START_HERE.md)
- structure map: [`../docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- bringup config docs: [`config/README.md`](config/README.md)
