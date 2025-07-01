# Quick Start Guide

Get the ProMOC Assembly system running in 5 minutes!

## Prerequisites

- Ubuntu 20.04/22.04/24.04 LTS
- ROS2 Humble or newer installed and sourced

```bash
# Verify ROS2 is installed
ros2 --version
echo $ROS_DISTRO
```

## 1. One-Command Installation

```bash
cd setup/
./install_all.sh
```

This installs everything automatically:
- ✅ System dependencies (.NET, build tools)
- ✅ Python dependencies (pythonnet, pylablib)  
- ✅ ROS2 dependencies (via rosdep)
- ✅ Builds the workspace
- ✅ Validates the installation

## 2. Source the Workspace

```bash
source install/setup.bash
```

## 3. Launch Simulation

### Dual LTS300 System
```bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py
```

### Single Axis Test
```bash
# Test X-axis
ros2 launch promoc_bringup test_single_lts300.launch.py test_axis:=x

# Test Z-axis  
ros2 launch promoc_bringup test_single_lts300.launch.py test_axis:=z
```

## 4. Basic Testing

### Check ROS2 Topics
```bash
# List available topics
ros2 topic list

# Monitor linear axis status
ros2 topic echo /promoc_assembly/x_axis/linear_axis_info
```

### Move the Axes
```bash
# Move X-axis to 50mm
ros2 service call /promoc_assembly/x_axis/move_absolute \
  promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute \
  "{target_position: 0.05, velocity: 0.01}"

# Move Z-axis to 30mm  
ros2 service call /promoc_assembly/z_axis/move_absolute \
  promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute \
  "{target_position: 0.03, velocity: 0.01}"
```

### Check Position
```bash
# Get X-axis position
ros2 service call /promoc_assembly/x_axis/get_position \
  promoc_assembly_interfaces/srv/linear_axis/GetPosition

# Get Z-axis position
ros2 service call /promoc_assembly/z_axis/get_position \
  promoc_assembly_interfaces/srv/linear_axis/GetPosition
```

## 5. Validation

```bash
cd setup/
./validate_setup_enhanced.sh
```

This performs comprehensive checks and generates a detailed report.

## What's Running?

After launching, you'll have:

1. **Gazebo Simulation** - Visual 3D environment
2. **Robot State Publisher** - Publishes robot model
3. **Joint Controllers** - Position control for both axes
4. **Linear Axis Nodes** - High-level motion services
5. **Custom Interfaces** - ProMOC-specific messages/services

## Next Steps

- 📖 Read the {doc}`../tutorials/index` for detailed usage
- 🔧 Explore the {doc}`../api/linear_axis_nodes` for API details
- 🎯 Check {doc}`../hardware/linear_axes` for real hardware setup
- 🚀 Try {doc}`../simulation/testing` for advanced testing

## Troubleshooting

### Installation Issues
```bash
# Re-run validation
./setup/validate_setup_enhanced.sh

# Check detailed report
cat setup/VALIDATION_REPORT.md
```

### Launch Issues
```bash
# Check ROS2 environment
env | grep ROS

# Source workspace
source install/setup.bash

# Check package visibility
ros2 pkg list | grep promoc
```

### Common Problems

1. **ROS_DISTRO not set**: `source /opt/ros/humble/setup.bash`
2. **Package not found**: `source install/setup.bash`  
3. **Permission denied**: `chmod +x setup/*.sh`
4. **Build errors**: `rm -rf build install log && ./setup/install_all.sh`

## Hardware Mode

For real hardware (when available):

```bash
# Install PMCLib (if available)
pip install local_libs/pmclib-*.whl

# Launch with hardware
ros2 launch promoc_bringup promoc_assembly_launch.py use_sim_time:=false
```

```{note}
The system automatically detects available hardware and switches between simulation and real drivers.
```

## Success Indicators

You know it's working when:

- ✅ Gazebo opens with the dual LTS300 system
- ✅ RViz shows the robot model (optional)
- ✅ Service calls move the simulated axes
- ✅ Topics publish position updates
- ✅ No error messages in the terminal

**Congratulations! Your ProMOC Assembly system is ready!** 🎉
