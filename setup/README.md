# Setup Helpers

The `setup/` directory contains helper scripts and notes for machine
preparation. For this milestone, the canonical verified workflow is still the
manual ROS workspace build documented in:

- [`../README.md`](../README.md)
- [`../docs/INSTALLATION.md`](../docs/INSTALLATION.md)

## What Is Here

- `install_all.sh`
- `install_system_deps.sh`
- `install_python_deps.sh`
- `install_camera_aravis2.sh`
- `check_installation.sh`
- `validate_setup_enhanced.sh`
- `repair.sh`

## Current Recommendation

Use these scripts as secondary machine-setup helpers only. The verified build
and test path for the current repository state is:

```bash
source /opt/ros/jazzy/setup.bash
cd <ros-workspace>
colcon build --symlink-install
source install/setup.bash
colcon test
colcon test-result --verbose
```

## Notes

- the checked baseline is ROS 2 Jazzy
- ROS 2 Humble is a target, not a completed verification result
- hardware-specific setup remains operator- and device-dependent
