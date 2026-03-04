# ProMOC Refactoring Task Plan (N+1, Breaking, Incremental)

## Summary
Refactor the repository to a canonical N+1 architecture without legacy compatibility paths, while keeping behavior stable on canonical APIs.

Execution strategy: 3 waves for controlled risk, easier reviews, and clean rollback points.

## Public API and Interface Changes (Breaking)
1. Launch API is only `runtime_mode:=hardware|sim`.
2. Remove legacy launch args `sim_mode` and `use_simulator`.
3. Keep only canonical ROS namespaces:
4. Camera: `/promoc/camera/*`.
5. Linear axis: `/promoc/linear_axis/<axis_name>/*` and `/promoc/linear_axis/<axis_name>/position`.
6. Planar motor: `/promoc/mover/*` and `/promoc/mover/xbot_info`.
7. Remove service alias compatibility layer (`promoc_core/promoc_core/service_alias.py`).
8. Keep only v2 user config keys (`measurement.*`, `runtime.mode`, etc.).
9. Remove deprecated camera parameter compatibility declarations/mappings.

## Wave 1: Remove Legacy and Freeze Canonical Contract
1. Remove legacy launch compatibility logic from:
2. `promoc_bringup/launch/system.launch.py`
3. `promoc_bringup/launch/camera.launch.py`
4. `promoc_bringup/launch/optical_measurement_system.launch.py`
5. `promoc_bringup/promoc_bringup/launch_utils.py`
6. Remove legacy service/topic alias wiring in:
7. `camera_nodes/camera_nodes/camera_node.py`
8. `camera_nodes/camera_nodes/nodes/camera_simulator.py`
9. `linear_axis_nodes/linear_axis_nodes/lts300_node.py`
10. `planar_motor_nodes/planar_motor_nodes/mover_node.py`
11. Remove deprecated camera parameter compatibility from:
12. `camera_nodes/camera_nodes/config.py`
13. Replace `promoc_bringup/scripts/release_n_check.py` with canonical N+1 contract checks and adjust corresponding tests.
14. Update migration and package docs to N+1-only behavior.

## Wave 2: Internal Simplification (No Intended Behavior Change)
1. Split `camera_nodes/camera_nodes/services/autofocus_handler.py` into smaller responsibility modules (axis client mgmt, autofocus runner, response building).
2. Add public hooks in `camera_nodes/camera_nodes/algorithms/autofocus.py` so handlers no longer rely on private fields like `_measurements` or `_calculate_score`.
3. Split `linear_axis_nodes/linear_axis_nodes/services/callbacks.py` into status, validation, and service callback modules.
4. Replace planar motor service MRO mixing with explicit composition/registry:
5. `planar_motor_nodes/planar_motor_nodes/services/__init__.py`
6. `planar_motor_nodes/planar_motor_nodes/services/base.py`
7. Move launch parameter mapping logic out of `promoc_bringup/launch/camera.launch.py` into a dedicated builder/helper.

## Wave 3: Quality Gates, Lint, Tests, Cleanup
1. Reduce Ruff excludes in `pyproject.toml`, especially:
2. `planar_motor_nodes/planar_motor_nodes/helpers/pmc_interface.py`
3. `promoc_bringup/promoc_bringup/service_helper.py`
4. `promoc_bringup/promoc_bringup/unified_demo.py`
5. Convert namespace migration tests into canonical contract tests.
6. Update `Makefile` and CI workflow target naming for N+1 checks.
7. Final docs consistency pass.

## Test Cases and Acceptance Criteria
1. Static contract checks confirm no legacy launch args, no legacy service/topic aliases, and no `register_service_alias_pair` usage.
2. Unit tests pass with canonical namespace/config expectations.
3. `ruff check`, `ruff format --check`, and `py_compile` pass for active code.
4. Manual ROS2 smoke (later on target system):
5. `ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware|sim` works.
6. Canonical service calls succeed.
7. Legacy calls fail with expected "not found" behavior.

## Assumptions and Defaults
1. Breaking changes are allowed for this cleanup.
2. Refactor depth remains incremental (no large new cross-package abstraction in this cycle).
3. Rollout remains in 3 waves.
4. Local ROS2 runtime tests happen later; current validation focuses on static and unit checks.
