# System Overview

This page explains how the repository is organized and which rules should stay stable while you work on it.

## Main Idea

The repository is hardware-first.

- `promoc_bringup` starts and wires the system
- runtime behavior lives inside the package that owns the hardware or feature
- `promoc_assembly_interfaces` contains contracts only
- `promoc_core` contains reusable helper code only

There is no big central orchestrator node by default. The maintained CS runtime
is built around one main launch path:

`system.launch.py -> camera + linear axes + planar motor + future runtime nodes`

For explanations to management or new maintainers, that launch path is the main
story of the branch: one bringup entry point, a few runtime packages with clear
ownership, and ROS services under stable `/promoc/...` namespaces.

## Package Boundaries

- `camera_nodes`: camera-facing behavior such as Four-Step autofocus and exposure- `linear_axis_nodes`: LTS300 axis runtime behavior
- `planar_motor_nodes`: mover motion and control runtime behavior
- `promoc_bringup`: launch composition, runtime mode, user config wiring
- `promoc_assembly_interfaces`: ROS messages and services only
- `promoc_core`: shared helpers with no runtime ownership of hardware

The branch is shaped this way on purpose:

- bringup explains how the system starts
- runtime packages explain how a hardware area behaves
- interfaces explain what can be called from ROS
- core explains reusable logic that should not own hardware

That separation keeps the branch small enough to explain quickly and reduces the
chance that new behavior gets hidden in the wrong layer.
## Working Rules

- keep business logic out of launch files
- do not turn `promoc_core` into a catch-all runtime package
- keep `promoc_assembly_interfaces` contract-only
- prefer changing canonical files instead of adding wrappers
- keep service and topic names under the documented `/promoc/...` namespaces

## Common Mistakes

- putting feature logic directly into `node.py`
- mixing SDK code into service callback files
- adding new compatibility wrappers instead of fixing the canonical path
- changing public service names casually
- hiding behavior in extra abstraction layers that make onboarding harder

## Build And Run Mental Model

The usual flow is:

1. build the workspace
2. source `install/setup.bash`
3. start the system with `ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware`
4. interact through ROS services under `/promoc/...`

In other words:

`system.launch.py -> bringup wiring -> runtime nodes -> ROS services -> hardware`
## Read Next

- onboarding: [`START_HERE.md`](START_HERE.md)
- package guide: [`PACKAGES.md`](PACKAGES.md)
- package README for the concrete area you want to change
