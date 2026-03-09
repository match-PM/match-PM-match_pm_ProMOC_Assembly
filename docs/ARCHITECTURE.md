# Architecture

This repository uses a simple runtime structure on purpose.

## Main Rules

1. `promoc_bringup` starts the system, but does not contain business logic.
2. Runtime packages keep their own ROS node, services, drivers, and package-local models.
3. `promoc_core` stays a utility package, not a runtime god object.
4. `promoc_assembly_interfaces` stays contract-only.
5. Public ROS names stay stable.

## Runtime Package Shape

Each runtime package aims for this structure:

- `node.py`
- `config.py`
- `models.py`
- `services/`
- `drivers/`
- `algorithms/` only where the package really needs algorithms
- `compat/` only if a public start path or transition really still needs it

## Why Service-First

We prefer a service-first layout because a new contributor can reason about it quickly:

- service broken -> open `services/`
- hardware broken -> open `drivers/`
- parameter broken -> open `config.py`
- shared state broken -> open `models.py`
- camera algorithm broken -> open `algorithms/`

That is easier to navigate than splitting the same feature across multiple abstract folder layers.

## Package Boundaries

- `camera_nodes`: camera-facing runtime behavior, autofocus, MTF, exposure, simulator
- `linear_axis_nodes`: single-axis motion runtime for the LTS300
- `planar_motor_nodes`: planar motor motion and control runtime
- `promoc_bringup`: launch composition and startup choices
- `promoc_core`: reusable helpers only
- `promoc_assembly_interfaces`: ROS contracts only

## Stable Runtime Contracts

These should remain stable unless there is a very strong reason to change them:

- `/promoc/camera/*`
- `/promoc/linear_axis/<axis_name>/*`
- `/promoc/mover/*`
- `runtime_mode:=hardware|sim`

## Orchestrator Decision

There is no central orchestration node by default.

Reason:

- the current system is easier to understand when launch stays in `promoc_bringup`
- runtime behavior stays inside the package that owns it
- adding a central manager too early would add another concept without reducing enough complexity

