# Repository Refactor Plan (ROS2 Runtime Packages)

## Scope and Constraints

This refactor standardizes runtime package internals while preserving:

- Top-level package boundaries:
  - `promoc_bringup`
  - `camera_nodes`
  - `linear_axis_nodes`
  - `planar_motor_nodes`
  - `promoc_assembly_interfaces`
  - `promoc_core`
  - `docs`
  - `setup`
- Canonical ROS APIs (`/promoc/...` service/topic namespaces)
- Runtime behavior and launch semantics
- CLI entrypoint behavior (`ros2 run ...`)

Out of scope:

- New ROS service/message contracts in `promoc_assembly_interfaces`
- Cross-package coupling from `promoc_core` to runtime nodes

## Current Inventory (Pre-Refactor)

### 1. Current runtime package internals

- `camera_nodes/camera_nodes/`
  - `camera_node.py`, `config.py`
  - `services/` (flat callback files)
  - `drivers/` (`camera_driver.py`, `aravis_camera_driver.py`, `simulated_camera_driver.py`)
  - `algorithms/` (autofocus, MTF, ROI, focus metrics)
  - `helpers/` (axis, parameter, formatting, mapping, focus profile, flyover)
  - `nodes/camera_simulator.py`
- `linear_axis_nodes/linear_axis_nodes/`
  - `lts300_node.py`, `config.py`
  - `services/` (callbacks, registry, validation, state/status)
  - `drivers/` (`linear_axis_driver.py`, hardware and simulated drivers)
  - `helpers/lts300_interface.py`
- `planar_motor_nodes/planar_motor_nodes/`
  - `mover_node.py`, `config.py`
  - `services/` (callbacks, motion input, registry)
  - `drivers/mock_pmclib.py`
  - `helpers/` (`pmc_interface.py`, `mover_utils.py`)

### 2. Entry points (`setup.py`)

- `camera_nodes`
  - `camera_node = camera_nodes.camera_node:main`
  - `camera_simulator = camera_nodes.nodes.camera_simulator:main`
- `linear_axis_nodes`
  - `lts300_node = linear_axis_nodes.lts300_node:main`
- `planar_motor_nodes`
  - `mover_node = planar_motor_nodes.mover_node:main`
- `promoc_bringup`
  - `unified_demo = promoc_bringup.unified_demo:main`

### 3. Launch references to runtime executables

- `promoc_bringup/launch/camera.launch.py`
  - `camera_nodes/camera_simulator`
  - `camera_nodes/camera_node`
- `promoc_bringup/launch/optical_measurement_system.launch.py`
  - `linear_axis_nodes/lts300_node`
  - `camera_nodes/camera_node`
- `promoc_bringup/launch/system.launch.py`
  - `planar_motor_nodes/mover_node`
  - `linear_axis_nodes/lts300_node`
- `promoc_bringup/launch/planar_motor_demo.launch.py`
  - `planar_motor_nodes/mover_node`

### 4. Import hotspots and migration-sensitive paths

- Node modules importing `helpers/*`:
  - `camera_nodes/camera_nodes/camera_node.py`
  - `linear_axis_nodes/linear_axis_nodes/lts300_node.py`
  - `planar_motor_nodes/planar_motor_nodes/mover_node.py`
- Service modules importing `helpers/*`:
  - camera autofocus/MTF services
  - linear-axis service callbacks
  - planar-motor service base
- Tests asserting old import strings:
  - `linear_axis_nodes/test/test_linear_axis_namespace_contract.py`
  - `planar_motor_nodes/test/test_mover_namespace_contract.py`
- Bringup validation script with hardcoded old file paths:
  - `promoc_bringup/scripts/release_n_check.py`

## Target Runtime Layout (Per Package)

Each runtime package (`camera_nodes`, `linear_axis_nodes`, `planar_motor_nodes`) will converge to:

- `node.py`
- `config.py`
- `services/`
  - `registry.py`
  - `handlers/`
  - `clients/`
  - `validation.py`
- `drivers/`
  - `base.py`
  - `hardware.py`
  - `sim.py` or `mock.py`
- `domain/`
  - `logic.py`
  - `models.py`
  - `algorithms/` (if needed)
- `adapters/`
  - `conversions.py`
  - `mapping.py`
  - `validation.py`

Compatibility wrappers are added only where needed to keep existing CLI/executable behavior and common import surfaces stable during migration.

## Phase Execution Plan

### Phase 1: Docs and migration map

- Add this plan and path migration table
- Record inventory and compatibility strategy

### Phase 2: Bringup cleanup

- Update path checks/references in bringup scripts/tests/docs
- Keep launch files behaviorally equivalent (same executable names, params, namespaces)

### Phase 3: `camera_nodes` cleanup

- Move node entry implementation to `node.py`
- Replace `helpers/` usage with `services/clients`, `domain`, `adapters`
- Standardize drivers into `base/hardware/sim`
- Move algorithms into `domain/algorithms`
- Keep compatibility shims for legacy module paths where necessary

### Phase 4: `linear_axis_nodes` cleanup

- Move node implementation to `node.py`
- Replace `helpers/lts300_interface.py` with `services/clients` location
- Standardize drivers and services layout

### Phase 5: `planar_motor_nodes` cleanup

- Move node implementation to `node.py`
- Replace helper modules with `drivers` + `domain` + `services/clients`
- Standardize service handlers/registry layout

### Phase 6: `promoc_core` consolidation

- Keep core utilities independent of runtime packages
- Ensure no reverse dependency into node packages
- Align docs and exports for beginner discoverability

### Phase 7: Final docs and cleanup

- Update `docs/START_HERE.md`
- Update `docs/PROJECT_STRUCTURE.md`
- Update `docs/MIGRATION_NOTES.md` with old->new module paths and compatibility notes
- Run available checks and fix regressions

## Verification Strategy Per Phase

- Structural checks:
  - `rg --files` package layout verification
  - import path scans (`rg -n "helpers|old_module_path"`)
- Buildability checks:
  - `python -m py_compile` on changed Python files
  - targeted `pytest` modules where feasible
- Behavioral safety checks:
  - keep service path literals (`/promoc/...`) unchanged
  - keep `setup.py` console script names unchanged (or equivalent wrappers)

## Execution Status (2026-03-09)

- Phase 1: completed
- Phase 2: completed
- Phase 3: completed
- Phase 4: completed
- Phase 5: completed
- Phase 6: completed (`promoc_core` remains independent; no runtime package imports)
- Phase 7: completed
