# Camera Configuration Directory

This directory contains the small camera configuration files used by the CS runtime.

## Runtime Focus

The maintained runtime only needs a few camera facts:

- camera identity and driver type
- pixel size and native resolution
- active pixel format and binning default
- exposure and frame-rate defaults
- camera calibration info
- dynamic GenICam parameters that the driver should expose

This directory is intentionally not an MTF or optical-analysis configuration area.

## Files

- `ids_u3_3800cp_hq.yaml`: default runtime camera
- `camera_template.yaml`: starting point for a new camera profile
- `README.md`: this overview

## Typical Workflow

1. Copy `camera_template.yaml` to a new `<camera_name>.yaml`
2. Fill in GUID, driver, camera name, pixel size, and resolution
3. Add calibration data to `camera_info`
4. List the dynamic camera parameters your hardware supports
5. Launch with:
   `ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware camera_type:=<camera_name>`

## Keep It Simple

When adding a new camera config, prefer only the keys the runtime actually uses:

- `camera_params`
- `exposure_time`
- `frame_rate`
- `camera_info`
- `dynamic_parameters`