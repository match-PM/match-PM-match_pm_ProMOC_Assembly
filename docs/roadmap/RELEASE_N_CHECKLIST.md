# Release N Acceptance Checklist

Run automated acceptance:

```bash
make release-n1-check
```

Smoke command sets:

```bash
make smoke-sim
make smoke-hw
```

## Launch/API
- [ ] `runtime_mode:=hardware|sim` works for `system.launch.py`
- [ ] `runtime_mode:=hardware|sim` works for `camera.launch.py`
- [ ] `runtime_mode:=hardware|sim` works for `optical_measurement_system.launch.py`
- [ ] Legacy args `sim_mode` and `use_simulator` still work
- [ ] Legacy arg usage emits deprecation warnings

## Canonical Services
- [ ] Camera canonical services under `/promoc/camera/*` are available
- [ ] Camera legacy services under `/promoc/camera_node/*` are available
- [ ] Linear-axis canonical services under `/promoc/linear_axis/<axis>/*` are available
- [ ] Linear-axis legacy services under `/<axis>/*` are available
- [ ] Mover canonical services under `/promoc/mover/*` are available
- [ ] Mover legacy services under `/mover_node/*` are available

## Config Compatibility
- [ ] `user_config.yaml` with v2 keys is accepted
- [ ] `user_config.yaml` with legacy keys is accepted
- [ ] Legacy config key usage emits warnings

## Tooling and Quality Gates
- [ ] `pip install -r requirements-dev.txt` succeeds
- [ ] `make lint` succeeds
- [ ] `make test-unit` succeeds
- [ ] `make release-n1-check` succeeds
- [ ] `make check` succeeds
- [ ] CI runs matrix for `ROS_DISTRO=humble` and `ROS_DISTRO=jazzy`

## Documentation
- [ ] `docs/START_HERE.md` has hardware and simulation flows
- [ ] DE and EN learning-path docs exist and are current
- [ ] Camera callback guides use canonical service names
- [ ] `docs/MIGRATION_NOTES.md` is complete and accurate

