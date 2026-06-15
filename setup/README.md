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

Use these scripts as secondary machine-setup helpers only. The recommended
build and test path for the authoritative target platform is:

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
- completed Humble verification is still pending
- hardware-specific setup remains operator- and device-dependent
