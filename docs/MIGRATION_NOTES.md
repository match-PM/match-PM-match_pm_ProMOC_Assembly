# Release N+1

Current runtime structure:

- `node.py`
- `config.py`
- `models.py`
- `services/`
- `drivers/`
- `algorithms/` where needed

Older multi-layer folder splits are no longer the active structure.

Current canonical entry points:

- `camera_nodes/camera_nodes/node.py`
- `linear_axis_nodes/linear_axis_nodes/node.py`
- `planar_motor_nodes/planar_motor_nodes/node.py`

Current package story:

- service behavior lives in `services/`
- hardware and mock code live in `drivers/`
- shared runtime data lives in `models.py`
- camera algorithms live in `algorithms/`

Compatibility stance:

- keep only public ROS names and launch behavior stable
- do not add new code to old wrapper paths
- remove obsolete wrappers once tests and entry points no longer need them
