# System Overview

## Purpose

This repository is the current ROS 2 control stack for the ProMOC CS setup. It
focuses on a camera, two linear axes, a planar motor, and a small system
controller.

The maintained startup path is:

```text
promoc_bringup/launch/system.launch.py
```

## Target Platform

This repository is maintained against:

- Ubuntu 22.04
- ROS 2 Humble
- Python 3.10

Completed Humble verification is still pending.

## Main Components

- `camera_nodes`
  republishes raw images and camera status
- `linear_axis_nodes`
  runs one `lts300_node` per axis with axis-specific configuration
- `planar_motor_nodes`
  exposes planar-motor motion and control services
- `promoc_core`
  provides reusable helpers and the system controller
- `promoc_bringup`
  owns launch composition and package-to-config wiring
- `promoc_assembly_interfaces`
  contains only message and service definitions
- `promoc_simulation`
  currently contains RViz/URDF assets, not the mock drivers used by the checked
  mock bringup

## Runtime Modes

Current launch files use:

- `driver_mode:=mock`
- `driver_mode:=hardware`

`mock` means software-only device substitutes behind the same public ROS
interfaces. `hardware` means the node will try to connect to real devices or
vendor drivers.

## Package Boundaries

Keep these boundaries intact:

- hardware-facing runtime logic stays in the package that owns the device
- launch files compose nodes and parameters but do not implement device logic
- `promoc_core` holds shared helpers and system-level coordination only
- `promoc_assembly_interfaces` stays contract-only
- future process logic belongs in dedicated higher-level nodes, not in device
  drivers

## System Controller

`promoc_system_controller` lives in `promoc_core` and:

- subscribes to camera, X-axis, Z-axis, and planar-motor status
- publishes `/promoc/system/status`
- exposes `/promoc/system/stop_all`
- exposes `/promoc/system/reset_stop`
- latches a stop condition until a guarded reset succeeds

## Configuration Ownership

Main package-owned configuration files:

- `camera_nodes/config/camera.yaml`
- `linear_axis_nodes/config/x_axis.yaml`
- `linear_axis_nodes/config/z_axis.yaml`
- `planar_motor_nodes/config/planar_motor.yaml`
- `promoc_core/config/system_controller.yaml`
- `promoc_bringup/config/system.yaml`

The current `system.launch.py` loads the package-specific config files directly.
`promoc_bringup/config/system.yaml` is tracked as a central composition summary,
but the current main launch does not read it automatically.

## What This Repository Does Not Yet Claim

It does not currently claim:

- hardware-certified emergency-stop behavior
- complete collision prevention across devices
- workspace-zone approval
- automatic safe parking
- full real-hardware verification for the current refactor

## Read Next

- [`PACKAGES.md`](PACKAGES.md)
- [`CONFIGURATION.md`](CONFIGURATION.md)
- [`INTERFACES.md`](INTERFACES.md)
- [`SAFETY.md`](SAFETY.md)
