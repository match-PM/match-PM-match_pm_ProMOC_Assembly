# System Overview

This page explains how the repository is organized and which rules should stay stable while you work on it.

## Main Idea

The repository is hardware-first.

- `promoc_bringup` starts and wires the system
- runtime behavior lives inside the package that owns the hardware or feature
- `promoc_assembly_interfaces` contains contracts only
- `promoc_core` contains reusable helper code only

There is no big central orchestrator node by default.

## Package Boundaries

- `camera_nodes`: camera-facing behavior such as autofocus, MTF, ROI detection, exposure
- `linear_axis_nodes`: LTS300 axis runtime behavior
- `planar_motor_nodes`: mover motion and control runtime behavior
- `promoc_bringup`: launch composition, runtime mode, user config wiring
- `promoc_assembly_interfaces`: ROS messages and services only
- `promoc_core`: shared helpers with no runtime ownership of hardware

## Runtime Conventions

Across runtime packages, keep this structure in mind:

- `node.py` wires ROS interfaces
- `services/` contains feature behavior
- `drivers/` talks to hardware, sim, or mocks
- `config.py` loads and shapes parameters
- `models.py` stores small shared state or typed containers
- `algorithms/` exists only where the package really needs it

## Stable Contracts

These should stay stable unless there is a very strong reason to change them:

- `/promoc/camera/*`
- `/promoc/linear_axis/<axis_name>/*`
- `/promoc/mover/*`
- `runtime_mode:=hardware|sim`

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
3. start the system with `make hw`, `make camera-hw`, or `make sim`
4. interact through ROS services under `/promoc/...`

## Read Next

- onboarding: [`START_HERE.md`](START_HERE.md)
- package guide: [`PACKAGES.md`](PACKAGES.md)
- package README for the concrete area you want to change
