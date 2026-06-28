# Camera Profiles

This directory holds hardware camera profile files used by:

```bash
ros2 launch promoc_bringup camera.launch.py \
  driver_mode:=hardware \
  camera_type:=<profile-name>
```

## Current Files

- `ids_u3_3800cp_hq.yaml`
  IDS U3-3800CP-C-HQ Rev.2.2 (`AB12874`), CP family, USB 3,
  Sony IMX183 CMOS, 5536x3692 max sensor resolution, 2.40 um pixels,
  19.8 fps at full resolution.
- `camera_template.yaml`

## What A Profile Owns

A profile may define:

- camera identity and driver type
- GUID or connection details
- product, sensor, interface, resolution, and pixel-format information
- calibration data
- dynamic parameters exposed to the hardware driver

`camera_params.sensor_resolution_h/v` describes the physical sensor maximum.
`camera_info.image_width/height` describes the calibration/runtime CameraInfo
and may be smaller when the active stream is cropped, binned, or calibrated for
a specific ROI.

## What It Does Not Do

This directory is not the main runtime selector. Driver selection still happens
through `driver_mode:=mock|hardware`.

## See Also

- [`../../../docs/CONFIGURATION.md`](../../../docs/CONFIGURATION.md)
- [`../../../promoc_bringup/README.md`](../../../promoc_bringup/README.md)
