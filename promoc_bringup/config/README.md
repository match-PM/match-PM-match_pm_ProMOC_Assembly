# Bringup Configuration

This directory contains tracked bringup-level configuration artifacts.

## Files

- `cameras/*.yaml`

## Current Source Behavior

`system.launch.py` owns top-level start choices directly:

- it declares launch arguments directly
- it loads package-owned YAML files directly
- it does not parse a separate bringup-level system YAML

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
