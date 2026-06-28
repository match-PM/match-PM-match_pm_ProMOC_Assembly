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

The recorded handover baseline includes Humble and Jazzy build/test checks plus
mock-runtime checks. Real hardware behavior is still not certified by those
checks.

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

`mock` means simple software-only substitutes behind the same public ROS
interfaces. These substitutes are for wiring checks, not physical simulation.
`hardware` means the node will try to connect to real devices or vendor
drivers.

## Package Boundaries

Keep these boundaries intact:

- hardware-facing runtime logic stays in the package that owns the device
- launch files compose nodes and parameters but do not implement device logic
- `promoc_core` holds shared helpers and system-level coordination only
- `promoc_assembly_interfaces` stays contract-only
- future process logic belongs in dedicated higher-level nodes, not in device
  drivers

## Code Style For This Repository

The current runtime intentionally favors a boring, explicit ROS 2 style:

- import drivers and helpers from their real modules, not from package-level
  barrel exports
- put ROS publishers, subscriptions, services, and timers visibly in the node
- use direct `declare_parameter()` calls where that helps a beginner see the
  ROS parameter API
- avoid lazy module `__getattr__`, hidden service registries, and magic
  factories unless they solve a real problem
- keep generated artifacts, virtual environments, IDE folders, and agent
  scratch folders outside this source repository

## Optional System Controller

`promoc_system_controller` lives in `promoc_core`. It is optional and is not
started by the default `system.launch.py` path. Enable it with
`system_controller:=true` when shared system status or coordinated stop/reset
behavior is needed.

Leave it off for direct camera, axis, or planar-motor bringup. Turn it on when
one ROS interface should summarize the whole setup and coordinate a software
stop across all motion devices.

When enabled, it:

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

The current `system.launch.py` loads the package-specific config files directly.
Top-level component choices are launch arguments, not a separate bringup YAML.

## What This Repository Does Not Yet Claim

It does not currently claim:

- hardware-certified emergency-stop behavior
- complete collision prevention across devices
- workspace-zone approval
- automatic safe parking
- full real-hardware verification for the current simplified runtime

## Read Next

- [`PACKAGES.md`](PACKAGES.md)
- [`CONFIGURATION.md`](CONFIGURATION.md)
- [`INTERFACES.md`](INTERFACES.md)
- [`SAFETY.md`](SAFETY.md)
