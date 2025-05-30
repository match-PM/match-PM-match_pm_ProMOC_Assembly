# Quick Start Guide

## For New Users - Complete Setup

1. **System Dependencies (Ubuntu):**
   ```bash
   ./install_system_deps.sh
   ```
   Installs .NET SDK 8.0 + Mono fallback + build tools

2. **Python Dependencies:**
   ```bash
   ./install_python_deps.sh
   ```
   Installs packages + tests .NET runtime compatibility

3. **Hardware Setup (if using real hardware):**
   ```bash
   # Copy PMCLib wheel file
   cp /path/to/pmclib-*.whl local_libs/
   # Reinstall with PMCLib
   ./install_python_deps.sh
   ```

4. **Build and Test:**
   ```bash
   cd ~/your_ros2_workspace
   colcon build
   source install/setup.bash
   ros2 launch promoc_bringup promoc_assembly_launch.py
   ```

## Development Mode (Mock Services)

```bash
# Quick test without hardware
ros2 launch promoc_bringup promoc_assembly_launch.py

# Test individual services
ros2 service call /planar_motor/move_absolute promoc_assembly_interfaces/srv/LinearMotionSi "{bot_id: 1, x_pos: 0.1, y_pos: 0.1, velocity: 0.5, acceleration: 1.0}"
```

## Hardware Mode

```bash
# Ensure hardware is connected and PMCLib is installed
ros2 launch promoc_bringup promoc_assembly_hardware_launch.py
```

## Common Issues

- **Permission denied on scripts:** `chmod +x *.sh`
- **Python import errors:** Check virtual environment and dependencies
- **.NET runtime issues:** Run `python3 check_dotnet_runtime.py`
- **Hardware not found:** Check connections and permissions
- **Build failures:** Ensure ROS2 is sourced: `source /opt/ros/humble/setup.bash`
- **PMCLib fails:** Try Mono fallback: `sudo apt-get install mono-complete`
