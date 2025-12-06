# ProMOC Assembly - Quick Start Guide

## 🚀 One-Command Installation

```bash
cd setup/
./install_all.sh
```

This installs **everything** needed for a fresh Ubuntu 24.04 system:
- System dependencies (.NET, Mono, Aravis, build tools)
- Python dependencies (pythonnet, pylablib, numba)
- USB/Serial permissions (dialout group, udev rules)
- camera_aravis2 driver (for IDS cameras)
- ROS2 workspace build

**⚠️ IMPORTANT**: After installation, **logout and login again** for group changes!

---

## 📋 Step-by-Step (If You Prefer Manual)

### 1. Prerequisites

```bash
# Ensure ROS2 Jazzy is installed and sourced
source /opt/ros/jazzy/setup.bash

# Check colcon is available
colcon --version || sudo apt install python3-colcon-common-extensions
```

### 2. Install Dependencies

```bash
cd setup/

# System dependencies (includes udev rules)
./install_system_deps.sh

# Python dependencies (with correct numba version!)
./install_python_deps.sh

# Camera driver (optional, for IDS cameras)
./install_camera_aravis2.sh
```

### 3. Build Workspace

```bash
cd ~/Documents/Development/Ros2/promoc_assembly
colcon build --symlink-install
source install/setup.bash
```

### 4. Add to ~/.bashrc

```bash
# Add ROS2 and workspace to bashrc
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/Documents/Development/Ros2/promoc_assembly/install/setup.bash' >> ~/.bashrc

# Activate Python virtual environment
echo 'source ~/ros2_promoc_venv/bin/activate' >> ~/.bashrc
```

---

## 🔧 Repair & Troubleshooting

### Python Environment Repair

If you have problems with Python dependencies (import errors, version conflicts):

```bash
cd setup/

# Interactive repair (recommended)
./repair.sh

# Force complete recreation (delete & recreate venv)
./repair.sh --force

# Quick reinstall (keep venv, only reinstall packages)
./repair.sh --keep-venv
```

### Check Installation Status

```bash
cd setup/
./check_installation.sh
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
# Option 1: Use repair script (recommended)
./repair.sh

# Option 2: Manual fix
pip install numba==0.59.1 llvmlite==0.42.0
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

---

## 📁 Project Structure

```
promoc_assembly/
├── src/
│   └── match-PM-match_pm_ProMOC_Assembly/
│       ├── camera_nodes/         # Camera integration
│       ├── linear_axis_nodes/    # Thorlabs LTS300 control
│       ├── lens_testing_nodes/   # Autofocus & MTF measurement
│       ├── planar_motor_nodes/   # Planar motor (PMCLib)
│       ├── promoc_bringup/       # Launch files & config
│       ├── promoc_core/          # Shared utilities & exceptions
│       ├── promoc_assembly_interfaces/  # ROS2 messages/services
│       └── setup/                # Installation scripts
│           ├── install_all.sh    # Master installer ⭐
│           ├── install_system_deps.sh
│           ├── install_python_deps.sh
│           ├── install_camera_aravis2.sh
│           ├── check_installation.sh  # Diagnose installation
│           ├── repair.sh         # Fix Python environment ⭐
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

*Last updated: 2024-12-06*
