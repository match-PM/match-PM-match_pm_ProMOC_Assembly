# ProMOC Repository Architecture

This document explains why the repository is split the way it is and which boundaries must stay stable.

## Design Principles

- hardware-first runtime, simulation second
- stable documented namespaces under `/promoc/...`
- clear separation between launch wiring, service orchestration, drivers, and domain logic
- contract definitions live separately from runtime implementations
- shared reusable Python code stays independent from runtime packages

## Package Boundaries

| Package | Responsibility | Must stay true |
|---|---|---|
| `promoc_bringup` | launch files, runtime selection, config wiring | no business logic in launch files |
| `camera_nodes` | camera-facing node, services, drivers, camera domain logic | public camera namespaces remain stable |
| `linear_axis_nodes` | axis node, axis services, LTS300 integration | axis namespaces remain stable |
| `planar_motor_nodes` | mover node, mover services, planar motor integration | mover namespaces remain stable |
| `promoc_assembly_interfaces` | ROS `srv` and `msg` contracts | contract-only, no runtime logic |
| `promoc_core` | shared Python utilities and reusable logic | independent from runtime packages |

## Runtime Layers

Runtime packages use the same internal layers:

1. `node.py`
   Owns node construction, service registration, parameter loading, and ROS-level orchestration.
2. `services/`
   Owns handlers, clients, validation, and service registry wiring.
3. `drivers/`
   Owns hardware, simulation, or mock backends.
4. `domain/`
   Owns package-specific business logic and models.
5. `adapters/`
   Owns conversions, mapping, and boundary validation.

The intended flow is:

`launch -> node.py -> services -> domain/drivers -> adapters when crossing boundaries`

## Stable Invariants

These are the repository rules that should not drift during cleanup or feature work:

- launch uses `runtime_mode:=hardware|sim`
- documented service namespaces stay under:
  - `/promoc/camera/*`
  - `/promoc/linear_axis/<axis_name>/*`
  - `/promoc/mover/*`
- `promoc_assembly_interfaces` remains contract-only
- `promoc_core` remains independent from runtime packages
- launch files compose and configure nodes; they do not own business logic

## Typical Request Flows

Camera service flow:

1. launch starts camera node
2. `camera_nodes/camera_nodes/node.py` builds the node and registers services
3. `camera_nodes/camera_nodes/services/handlers/` processes the request
4. `domain/`, `drivers/`, and `adapters/` do the actual work

Linear-axis flow:

1. launch starts an axis node
2. `linear_axis_nodes/linear_axis_nodes/node.py` registers canonical axis services
3. motion handlers validate and route commands
4. hardware or sim drivers execute the motion

Planar-motor flow:

1. launch starts the mover node
2. `planar_motor_nodes/planar_motor_nodes/node.py` registers mover services
3. service handlers apply motion and control rules
4. driver backends talk to PMC hardware or the mock implementation

## Non-Goals

Avoid these patterns:

- new generic `helpers/` or `utils/` dumping grounds
- launch files with embedded business logic
- runtime packages importing each other directly for shared helpers
- mixing contract changes with unrelated runtime behavior changes without updating both sides

## Workflow Orchestration Stance

There is currently no need for a dedicated `promoc_orchestration` or `promoc_workflows` package.

Reason:

- the repo has optional demo flows, but not at least three production cross-node workflows with distinct coordination logic
- the existing `promoc_bringup.unified_demo` node is a demo helper, not a canonical runtime manager
- adding a new orchestration package now would introduce another concept for beginners without clearly reducing complexity

If real cross-node workflows grow beyond demo sequences, revisit this decision with a small optional package instead of expanding `promoc_core` or moving logic into launch files.

## Read Next

- docs index: [`README.md`](README.md)
- onboarding: [`START_HERE.md`](START_HERE.md)
- file ownership map: [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)
- package-level guides:
  - [`../promoc_bringup/README.md`](../promoc_bringup/README.md)
  - [`../camera_nodes/README.md`](../camera_nodes/README.md)
  - [`../linear_axis_nodes/README.md`](../linear_axis_nodes/README.md)
  - [`../planar_motor_nodes/README.md`](../planar_motor_nodes/README.md)
