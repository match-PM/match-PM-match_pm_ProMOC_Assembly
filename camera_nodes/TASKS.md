# Camera Nodes Tasks

## Next Session

- Continue with `camera_nodes/services/autofocus.py`.
- Goal: make runner, axis, and result flow as readable as the algorithm layer.
- Likely refactor targets:
  - split long control flow into smaller helper methods
  - align naming with the updated autofocus algorithms
  - make step boundaries in the service orchestration easier to follow
- Context from the last session:
  - algorithm files in `camera_nodes/camera_nodes/algorithms/` were already simplified
  - autofocus strategies now use clearer step markers and enum-based internal states
  - next focus is readability, not behavior changes
