# ProMOC Bringup

## Purpose

`promoc_bringup` owns launch files, runtime selection, and parameter wiring for
the CS runtime.

If you need to explain the package briefly: this package decides which runtime
nodes start, which config they receive, and which launch path is the official
one for the branch. It should not contain hardware business logic.

## Official Launch

- `launch/system.launch.py`

This is the maintained main entry point for the branch:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
```

Secondary paths that may still be useful for development:

- `launch/camera.launch.py`
- `launch/optical_measurement_system.launch.py`
- `launch/promoc_assembly_demo.launch.py`
- `launch/planar_motor_demo.launch.py`
- `launch/assembly_camera.launch.py`

They are not equal alternatives to `system.launch.py`.

Canonical launch argument:

- `runtime_mode:=hardware|sim`

## How To Run

```bash
make doctor-hw
make hw
make sim
```

For management-style explanations, the important point is that there is one
official runtime entry and a few clearly secondary helper launches.

## Where To Edit Common Changes

| Goal | Open this first |
|---|---|
| Change which nodes start | `promoc_bringup/launch/system.launch.py` |
| Change a secondary camera-only start | `promoc_bringup/launch/camera.launch.py` |
| Change a secondary optical-measurement start | `promoc_bringup/launch/optical_measurement_system.launch.py` |
| Change runtime-mode handling | `promoc_bringup/promoc_bringup/launch_utils.py` |
| Change camera parameter mapping | `promoc_bringup/promoc_bringup/camera_launch_builder.py` |
| Change user config loading or defaults | `promoc_bringup/promoc_bringup/launch_utils.py`, `promoc_bringup/config/` |

Keep business logic out of launch files. Launch code should compose nodes and map configuration, not implement runtime behavior.

## Verify Changes

```bash
make lint
make test-unit
make cs-runtime-check
```

## Related Docs

- onboarding: [`../docs/START_HERE.md`](../docs/START_HERE.md)
- package guide: [`../docs/PACKAGES.md`](../docs/PACKAGES.md)
- system overview: [`../docs/SYSTEM_OVERVIEW.md`](../docs/SYSTEM_OVERVIEW.md)
- bringup config docs: [`config/README.md`](config/README.md)
