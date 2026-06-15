# Mock Mode

`driver_mode:=mock` is the checked development path when real hardware is not
available.

## What Mock Mode Is

- a development aid
- a software-only stand-in for the public ROS interfaces
- a way to test build, launch, status publication, and control wiring

## What Mock Mode Is Not

- not a physics simulation
- not a mechanical safety validation
- not a timing-accurate reproduction of the real system
- not proof that hardware mode is safe

## What Uses Mock Mode

- `camera_node` can publish a synthetic image stream
- `lts300_node` can run with mock drivers
- `mover_node` can run with a mock planar-motor backend
- `tools/check_project.py --full` uses mock-mode smoke checks

## Relationship To `promoc_simulation`

`promoc_simulation` currently contains RViz and URDF assets. That package is
not the same thing as the checked mock bringup. The full mock-system checks run
through `promoc_bringup` plus mock drivers in the runtime packages.
