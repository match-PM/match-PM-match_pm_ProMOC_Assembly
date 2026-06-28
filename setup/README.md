# Setup Helper

The `setup/` directory contains one convenience CLI for machine preparation.
For this milestone, the canonical verified workflow is still the normal ROS
workspace build documented in:

- [`../README.md`](../README.md)
- [`../docs/INSTALLATION.md`](../docs/INSTALLATION.md)

## Commands

Run from the repository root:

```bash
python3 setup/setup.py check
python3 setup/setup.py install --all
python3 setup/setup.py install --python
python3 setup/setup.py install --system
python3 setup/setup.py install --camera
python3 setup/setup.py validate
python3 setup/setup.py repair
```

Useful dry run:

```bash
python3 setup/setup.py install --all --dry-run
```

## Recommendation

Use `setup/setup.py` as a secondary machine-setup helper only. The recommended
build and test path for the authoritative target platform remains:

```bash
source /opt/ros/humble/setup.bash
cd <ros-workspace>
colcon build --symlink-install
source install/setup.bash
colcon test
colcon test-result --verbose
```

## Notes

- the authoritative target is ROS 2 Humble on Ubuntu 22.04 with Python 3.10
- Humble build/test verification is recorded in the handover baseline
- hardware-specific setup remains operator- and device-dependent
- `install --all` installs apt/Python dependencies, runs rosdep, and builds the
  workspace; add `--camera` when you also want `camera_aravis2`
- keep this repository as clean ROS 2 source packages; do not create `.venv`,
  `local_libs`, or external driver checkouts inside this repo
- place the proprietary PMCLib package locally at
  `planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib/` for hardware
  mode only; do not commit it
