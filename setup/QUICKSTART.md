# ProMOC Assembly - Quick Start Guide# Quick Start Guide



## 🚀 One-Command Installation## For New Users - Complete Setup



```bash1. **System Dependencies (Ubuntu):**

cd setup/   ```bash

./install_all.sh   ./install_system_deps.sh

```   ```

   Installs .NET SDK 8.0 + Mono fallback + build tools

This installs **everything** needed for a fresh Ubuntu 24.04 system:

- System dependencies (.NET, Mono, Aravis, build tools)2. **Python Dependencies:**

- Python dependencies (pythonnet, pylablib, numba)   ```bash

- USB/Serial permissions (dialout group, udev rules)   ./install_python_deps.sh

- camera_aravis2 driver (for IDS cameras)   ```

- ROS2 workspace build   Installs packages + tests .NET runtime compatibility



**⚠️ IMPORTANT**: After installation, **logout and login again** for group changes!3. **Hardware Setup (if using real hardware):**

   ```bash

---   # Copy PMCLib wheel file

   cp /path/to/pmclib-*.whl local_libs/

## 📋 Step-by-Step (If You Prefer Manual)   # Reinstall with PMCLib

   ./install_python_deps.sh

### 1. Prerequisites   ```



```bash4. **Build and Test:**

# Ensure ROS2 Jazzy is installed and sourced   ```bash

source /opt/ros/jazzy/setup.bash   cd ~/your_ros2_workspace

   colcon build

# Check colcon is available   source install/setup.bash

colcon --version || sudo apt install python3-colcon-common-extensions   ros2 launch promoc_bringup promoc_assembly_launch.py

```   ```



### 2. Install Dependencies## Development Mode (Mock Services)



```bash```bash

cd setup/# Quick test without hardware

ros2 launch promoc_bringup promoc_assembly_launch.py

# System dependencies (includes udev rules)

./install_system_deps.sh# Test individual services

ros2 service call /planar_motor/move_absolute promoc_assembly_interfaces/srv/LinearMotionSi "{bot_id: 1, x_pos: 0.1, y_pos: 0.1, velocity: 0.5, acceleration: 1.0}"

# Python dependencies (with correct numba version!)```

./install_python_deps.sh

## Hardware Mode

# Camera driver (optional, for IDS cameras)

./install_camera_aravis2.sh```bash

```# Ensure hardware is connected and PMCLib is installed

ros2 launch promoc_bringup promoc_assembly_hardware_launch.py

### 3. Build Workspace```



```bash## Common Issues

cd ~/Documents/Development/Ros2/promoc_assembly

colcon build --symlink-install- **Permission denied on scripts:** `chmod +x *.sh`

source install/setup.bash- **Python import errors:** Check virtual environment and dependencies

```- **.NET runtime issues:** Run `python3 check_dotnet_runtime.py`

- **Hardware not found:** Check connections and permissions

### 4. Add to ~/.bashrc- **Build failures:** Ensure ROS2 is sourced: `source /opt/ros/humble/setup.bash`

- **PMCLib fails:** Try Mono fallback: `sudo apt-get install mono-complete`

```bash
# Add ROS2 and workspace to bashrc
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/Documents/Development/Ros2/promoc_assembly/install/setup.bash' >> ~/.bashrc

# If camera_aravis2 is in separate workspace:
echo 'source ~/ros2_ws/install/setup.bash' >> ~/.bashrc
```

---

## 🎮 Running the System

### LTS300 Linear Axis

```bash
# Start LTS300 node (connect hardware first!)
ros2 run linear_axis_nodes lts300_node --ros-args \
    -r __node:=lts300_x_axis \
    -p serial_port:=/dev/ttyUSB0 \
    -p debug_mode:=true
```

### IDS USB3 Camera

```bash
# Find your camera GUID first
arv-tool-0.8

# Start camera driver
ros2 launch promoc_bringup assembly_camera.launch.py
```

### Full System (via Launch Files)

```bash
# Launch complete assembly system
ros2 launch promoc_bringup promoc_assembly_launch.py
```

---

## 🔧 Common Issues & Fixes

### Serial Port Permission Denied

```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Then logout and login again!
```

### pylablib/numba Import Error

```bash
# Install correct numba version (critical!)
pip install --break-system-packages numba==0.59.1 llvmlite==0.42.0 coverage<7.4
```

### Camera Not Detected

```bash
# Check USB connection
lsusb | grep 1409

# Check user groups
groups $USER  # should include 'plugdev'

# List cameras
arv-tool-0.8
```

### ROS2 Not Found

```bash
# Source ROS2 Jazzy
source /opt/ros/jazzy/setup.bash

# Or add to ~/.bashrc permanently
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
```

---

## 📁 Project Structure

```
promoc_assembly/
├── src/
│   └── match-PM-match_pm_ProMOC_Assembly/
│       ├── camera_nodes/         # Camera integration
│       ├── linear_axis_nodes/    # Thorlabs LTS300 control
│       ├── planar_motor_nodes/   # Planar motor (PMCLib)
│       ├── promoc_bringup/       # Launch files & config
│       ├── promoc_assembly_interfaces/  # ROS2 messages/services
│       └── setup/                # Installation scripts
│           ├── install_all.sh    # Master installer ⭐
│           ├── install_system_deps.sh
│           ├── install_python_deps.sh
│           ├── install_camera_aravis2.sh
│           └── dependencies.txt
└── install/                      # Built packages (after colcon build)
```

---

## 🔗 External Dependencies

| Package | Purpose | Installation |
|---------|---------|--------------|
| camera_aravis2 | IDS USB3 camera driver | `./install_camera_aravis2.sh` |
| PMCLib | Planar motor control | Copy to `local_libs/pmclib/` |
| pylablib | Thorlabs hardware | `pip install pylablib` |
| pythonnet | .NET integration | `pip install pythonnet` |

---

## 📞 Hardware Info

### Thorlabs LTS300
- Connection: USB (serial port `/dev/ttyUSB0`)
- Requires: `dialout` group membership
- Driver: pylablib

### IDS USB3 Vision Camera (U3-380xCP-C)
- Vendor ID: 0x1409
- Connection: USB3
- Requires: `plugdev` group membership, udev rules
- Driver: camera_aravis2

---

*Last updated: $(date +%Y-%m-%d)*
