# Camera Profiles

This directory holds hardware camera profile files used by:

```bash
ros2 launch promoc_bringup camera.launch.py \
  driver_mode:=hardware \
  camera_type:=<profile-name>
```

## Current Files

- `ids_u3_3800cp_hq.yaml`
- `camera_template.yaml`

## What A Profile Owns

A profile may define:

- camera identity and driver type
- GUID or connection details
- resolution and pixel-format information
- calibration data
- dynamic parameters exposed to the hardware driver

## What It Does Not Do

This directory is not the main runtime selector. Driver selection still happens
through `driver_mode:=mock|hardware`.

## See Also

- [`../../../docs/CONFIGURATION.md`](../../../docs/CONFIGURATION.md)
- [`../../../promoc_bringup/README.md`](../../../promoc_bringup/README.md)
