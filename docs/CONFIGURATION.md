# Configuration Guide

## Ownership

The current runtime is configured by package-owned YAML files:

- `promoc_bringup/config/system.yaml`
- `camera_nodes/config/camera.yaml`
- `linear_axis_nodes/config/x_axis.yaml`
- `linear_axis_nodes/config/z_axis.yaml`
- `planar_motor_nodes/config/planar_motor.yaml`
- `promoc_core/config/system_controller.yaml`

Hardware camera profiles live in:

- `promoc_bringup/config/cameras/*.yaml`

## Central Versus Package-Specific Settings

`promoc_bringup/config/system.yaml` records the intended top-level composition:

- `driver_mode`
- component enable flags
- config paths for each package

Current state from source:

- `system.launch.py` loads the package-specific YAML files directly
- `system.yaml` is tracked and useful as a central reference
- `system.yaml` is not currently consumed automatically by the main launch

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

- camera GUID and driver type
- resolution and pixel format data
- calibration data
- dynamic parameter exposure

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

## Planar Motor

`planar_motor_nodes/config/planar_motor.yaml` defines:

- `driver_mode`
- `xbot_id`
- `publish_rate`
- `pmc_ip`
- workspace bounds: `x_min`, `x_max`, `y_min`, `y_max`, `z_min`, `z_max`
- tolerances
- standard velocity parameters

This package owns its local movement limits and default motion speeds.

## System Controller

`promoc_core/config/system_controller.yaml` defines:

- required device list
- status topic names for all monitored devices
- stop service names for motion-capable devices
- planar-motor XBot selection
- status freshness timeout
- service call timeout
- system status publication rate

These values define how the controller decides whether device state is fresh and
whether `reset_stop` may succeed.

## `driver_mode`

Current launches use `driver_mode`, not `runtime_mode`, `use_mock`, or
`use_simulator`.

- `driver_mode:=mock`
  uses software-only drivers behind the same ROS topics and services
- `driver_mode:=hardware`
  tries to connect to real devices or vendor integrations

`use_sim_time` is not used to choose driver behavior. Driver selection is an
application concern, not a ROS time-source concern.
