# Bringup Configuration

This directory contains tracked bringup-level configuration artifacts.

## Files

- `system.reference.yaml`
- `cameras/*.yaml`

## Current Source Behavior

`system.reference.yaml` records the intended top-level composition:

- `driver_mode`
- component enable flags
- config paths for package-owned YAML files

`system.launch.py` behavior is intentionally simpler:

- it declares launch arguments directly
- it loads package-owned YAML files directly
- it does not parse the reference file

## Camera Profiles

Hardware camera profile files under `cameras/` are used by:

```bash
ros2 launch promoc_bringup camera.launch.py \
  driver_mode:=hardware \
  camera_type:=ids_u3_3800cp_hq
```

## See Also

- [`../../docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md)
- [`../../promoc_bringup/README.md`](../../promoc_bringup/README.md)
