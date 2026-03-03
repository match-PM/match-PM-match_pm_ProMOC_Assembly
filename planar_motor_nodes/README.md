# Planar Motor Nodes

ROS2 package for controlling XBot planar motors in ProMOC.

Canonical API namespace:
- `/promoc/mover/*`

Release N also keeps legacy aliases:
- `/mover_node/*`
- topic alias `xbot_info` (canonical: `/promoc/mover/xbot_info`)

## Main Entry Point

- Node executable: `mover_node`
- Default node name: `mover_node`

## Current Internal Structure

```text
planar_motor_nodes/planar_motor_nodes/
  mover_node.py
  config.py
  mover_pmc_interface.py
  mover_utils.py
  callbacks/
    base.py
    control.py
    motion.py
  drivers/
    mock_pmclib.py
```

## Change Guide (First Files To Open)

| You want to change... | Start here | Then check |
|---|---|---|
| Motion service behavior (linear, arc, 6-DoF) | `planar_motor_nodes/planar_motor_nodes/callbacks/motion.py` | `planar_motor_nodes/planar_motor_nodes/callbacks/base.py`, `planar_motor_nodes/planar_motor_nodes/mover_utils.py` |
| Control service behavior (activate, stop, velocity) | `planar_motor_nodes/planar_motor_nodes/callbacks/control.py` | `planar_motor_nodes/planar_motor_nodes/mover_node.py` |
| Service/topic namespace wiring | `planar_motor_nodes/planar_motor_nodes/mover_node.py` | `promoc_bringup/launch/system.launch.py` |
| Parameter defaults, bounds, tolerances | `planar_motor_nodes/planar_motor_nodes/config.py` | `planar_motor_nodes/planar_motor_nodes/mover_utils.py`, `promoc_bringup/config/mover_node_params.yaml` |
| PMC hardware/mock backend behavior | `planar_motor_nodes/planar_motor_nodes/mover_pmc_interface.py` | `planar_motor_nodes/planar_motor_nodes/drivers/mock_pmclib.py` |

## Quick Start

Hardware-first (recommended):

```bash
make doctor-hw
make hw
```

Simulation/mock path:

```bash
make sim
```

Direct node run in mock mode:

```bash
ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true
```

## Canonical Services

```bash
ros2 service call /promoc/mover/activate_xbots \
  promoc_assembly_interfaces/srv/ActivateXbots "{activation_status: true}"
```

```bash
ros2 service call /promoc/mover/linear_motion_si \
  promoc_assembly_interfaces/srv/LinearMotionSi "{xbot_id: 0, x_pos: 10.0, y_pos: 20.0}"
```

```bash
ros2 service call /promoc/mover/stop_motion \
  promoc_assembly_interfaces/srv/StopMotion "{xbot_id: 0}"
```

```bash
ros2 topic echo /promoc/mover/xbot_info
```

## Parameters

Important ROS parameters:
- `use_mock`
- `xbot_id`
- `publish_rate`
- `pmc_ip`
- `xy_tolerance`
- `six_d_tolerance`
- `x_min`, `x_max`
- `y_min`, `y_max`
- `z_min`, `z_max`

Primary config file:
- `promoc_bringup/config/mover_node_params.yaml`

## Operational Notes

- On hardware mode, the node retries PMC connection until available.
- After connection, activation and periodic status publishing start automatically.
- For first integration steps, use mock mode before hardware mode.

## Development and Tests

Run package tests:

```bash
colcon test --packages-select planar_motor_nodes
colcon test-result --verbose
```

Repository-level fast checks:

```bash
make lint
make test-unit
make release-n-check
```

## Troubleshooting

Connection issues:
- Check PMC network reachability (default `192.168.10.100`).
- Power-cycle PMC if connection repeatedly fails.
- Switch to mock mode to isolate software wiring.

Service issues:
- Verify node is running (`ros2 node list`).
- Verify canonical services (`ros2 service list | grep /promoc/mover`).
