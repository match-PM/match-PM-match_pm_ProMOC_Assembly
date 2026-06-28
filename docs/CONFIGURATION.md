# Configuration Guide

## Ownership

The current runtime is configured by package-owned YAML files:

- `camera_nodes/config/camera.yaml`
- `linear_axis_nodes/config/x_axis.yaml`
- `linear_axis_nodes/config/z_axis.yaml`
- `planar_motor_nodes/config/planar_motor.yaml`
- `promoc_core/config/system_controller.yaml`

Hardware camera profiles live in:

- `promoc_bringup/config/cameras/*.yaml`

## Launch Choices Versus Device Settings

- `system.launch.py` owns top-level start choices through launch arguments
- device parameters live in package-specific YAML files
- camera hardware profiles live under `promoc_bringup/config/cameras/`

## Camera

`camera_nodes/config/camera.yaml` defines:

- `driver_mode`
- `camera_name`
- `source_image_topic`
- `image_topic`
- `status_topic`
- `frame_id`
- publish and timeout rates
- mock image size and encoding

Hardware-specific camera profile files under
`promoc_bringup/config/cameras/` define:

- camera product identity, GUID, and driver type
- resolution and pixel format data
- calibration data
- dynamic parameter exposure

The default hardware profile is `ids_u3_3800cp_hq`, matching the IDS
U3-3800CP-C-HQ Rev.2.2 (`AB12874`) USB3 camera with Sony IMX183 CMOS sensor,
5536x3692 maximum sensor resolution, and 2.40 um pixels. The physical sensor
resolution is stored under `camera_params.sensor_resolution_h/v`; the
`camera_info.image_width/height` values are calibration/runtime CameraInfo and
may describe a smaller active stream.

## Linear Axes

`linear_axis_nodes/config/x_axis.yaml` and `z_axis.yaml` define:

- `axis_id`
- `driver_mode`
- `serial_number`
- `serial_port`
- `min_position`
- `max_position`
- `default_velocity`
- `default_acceleration`
- `movement_timeout`
- `homing_timeout`
- `state_publish_rate_hz`

These files own the local soft limits for each axis. Wrong values here can make
commands unsafe or unusable.

In hardware mode, `serial_number` is the preferred axis selector. Leave
`serial_port` empty for the normal setup: the driver scans `/dev/ttyUSB*` and
`/dev/ttyACM*`, opens each candidate briefly, reads the Thorlabs serial number,
and keeps the device whose serial matches the axis config. Set `serial_port`
only when you intentionally want to force one device path.

## Planar Motor

`planar_motor_nodes/config/planar_motor.yaml` defines:

- `driver_mode`
- `xbot_id`
- `publish_rate`
- `pmc_ip`
- workspace bounds: `x_min`, `x_max`, `y_min`, `y_max`, `z_min`, `z_max`
- tolerances
- default speed profile values:
  `default_xy_vel`, `default_xy_max_accel`, `default_z_vel`,
  `default_z_max_accel`, `default_rx_vel`, `default_ry_vel`, `default_rz_vel`

This package owns its local movement limits and default motion speeds.

Planar-motor hardware mode loads the proprietary PMCLib package from the
local-only path:

```text
planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib/
```

Mock mode works without that directory.

## System Controller

`promoc_core/config/system_controller.yaml` defines:

- required device list
- status topic names for all monitored devices
- stop service names for motion-capable devices
- planar-motor XBot selection
- status freshness timeout
- service call timeout
- system status publication rate

The system controller is optional. The default `system.launch.py` device stack
does not start it unless `system_controller:=true` is passed.

These values define how the controller decides whether device state is fresh and
whether `reset_stop` may succeed.

The system-controller node keeps these defaults in the small
`PARAMETER_DEFAULTS` table inside
`promoc_core/promoc_core/system_controller.py`, so the YAML and code stay easy
to compare.

## `driver_mode`

Current launches use `driver_mode`, not `runtime_mode`, `use_mock`, or
`use_simulator`.

- `driver_mode:=mock`
  uses simple software-only dummy drivers behind the same ROS topics and
  services. These are wiring checks, not mechanical simulations.
- `driver_mode:=hardware`
  tries to connect to real devices or vendor integrations

`use_sim_time` is not used to choose driver behavior. Driver selection is an
application concern, not a ROS time-source concern.

## Clean Workspace Layout

The repository should sit under the ROS workspace `src/` directory:

```text
<ros-workspace>/
  src/
    <this repository>
```

Do not keep `.venv`, IDE metadata, agent scratch folders, or `build/`,
`install/`, `log/` inside the repository directory. ROS build artifacts belong
at the workspace root.
