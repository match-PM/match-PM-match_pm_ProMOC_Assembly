# Mock Mode

`driver_mode:=mock` is the checked development path when real hardware is not
available.

Beginner command after `make build` and `source ../install/setup.bash` from
the repository root:

```bash
make start-mock
```

## What Mock Mode Is

- a development aid
- a simple software-only stand-in for the public ROS interfaces
- a way to test build, launch, status publication, and control wiring

## What Mock Mode Is Not

- not a physics simulation
- not a mechanical safety validation
- not a timing-accurate reproduction of the real system
- not proof that hardware mode is safe

## What Uses Mock Mode

- `camera_node` can publish a synthetic image stream
- `lts300_node` can run with tiny in-memory dummy drivers
- `mover_node` can run with a tiny in-memory planar-motor dummy backend
- `setup/setup.py validate` checks the maintained source-level mock paths

The axis and planar-motor dummy drivers update stored positions immediately
when commands are accepted. They intentionally do not model travel time,
mechanics, collisions, controller firmware, or real stop distance.

## Relationship To `promoc_simulation`

`promoc_simulation` currently contains RViz and URDF assets. That package is
not the same thing as the checked mock bringup. The maintained mock bringup runs
through `promoc_bringup` plus mock drivers in the runtime packages.
