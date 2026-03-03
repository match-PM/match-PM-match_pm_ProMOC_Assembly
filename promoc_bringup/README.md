# ProMOC Bringup

## Purpose

`promoc_bringup` owns launch wiring and runtime configuration mapping for the full system.
It is the package where node composition and startup behavior are defined.

## How To Run / Build

Official hardware flow:

```bash
make doctor-hw
make hw
```

Camera-only hardware flow:

```bash
make camera-hw
```

Optional simulation flow:

```bash
make sim
```

## Key APIs

Primary launch files:

- `launch/system.launch.py` (full stack)
- `launch/camera.launch.py` (camera stack only)
- `launch/optical_measurement_system.launch.py` (camera + focused optical flow)
- `launch/promoc_assembly_demo.launch.py` (demo flow)
- `launch/planar_motor_demo.launch.py` (planar motor demo)

Canonical launch argument:

- `runtime_mode:=hardware|sim`

Release N compatibility:

- legacy launch args `sim_mode` and `use_simulator` are still accepted with warnings.

## Where To Edit

| Goal | Start Here | Then Check |
|---|---|---|
| Change which nodes start in full-system launch | `promoc_bringup/launch/system.launch.py` | other launch files in `promoc_bringup/launch/` |
| Change runtime argument handling or compatibility rules | `promoc_bringup/promoc_bringup/launch_utils.py` (`resolve_runtime_mode`) | launch files that declare runtime args |
| Change user config schema mapping | `promoc_bringup/promoc_bringup/launch_utils.py` (`_normalize_user_config`, `load_user_config`) | `promoc_bringup/config/README.md`, `promoc_bringup/config/user_config.v2.example.yaml` |
| Change default node parameters | `promoc_bringup/config/*.yaml` | package config dataclasses in runtime node packages |

## Verify Changes

```bash
make lint
make test-unit
make release-n-check
```

## Related Docs

- Root onboarding: [`START_HERE.md`](../START_HERE.md)
- Project map: [`docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- Architecture boundaries: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- Bringup config docs: [`promoc_bringup/config/README.md`](config/README.md)
