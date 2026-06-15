# Bringup Configuration

This directory contains tracked bringup-level configuration artifacts.

## Files

- `system.yaml`
- `demo_controller_params.yaml`
- `cameras/*.yaml`

## Current Source Behavior

`system.yaml` records the intended top-level composition:

- `driver_mode`
- component enable flags
- config paths for package-owned YAML files

Current `system.launch.py` behavior is simpler:

- it declares launch arguments directly
- it loads package-owned YAML files directly
- it does not currently parse `system.yaml`

## Camera Profiles

Hardware camera profile files under `cameras/` are used by:

```bash
ros2 launch promoc_bringup camera.launch.py \
  driver_mode:=hardware \
  camera_type:=ids_u3_3800cp_hq
```

## Demo Parameters

`demo_controller_params.yaml` belongs to the optional `unified_demo` flow, not
to the canonical startup path.

## See Also

- [`../../docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md)
- [`../../promoc_bringup/README.md`](../../promoc_bringup/README.md)
