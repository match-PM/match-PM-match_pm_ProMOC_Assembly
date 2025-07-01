# ProMOC Assembly Setup Scripts

This directory contains all installation and validation scripts for the ProMOC Assembly system.

## 🚀 Quick Installation

**For complete automated installation:**
```bash
cd setup/
./install_all.sh
```

## 📁 Files Overview

### Core Installation Scripts
- **`install_all.sh`** - 🎯 **Master installer** - runs everything automatically
- **`install_system_deps.sh`** - Installs system dependencies (.NET SDK, Mono, build tools)  
- **`install_python_deps.sh`** - Installs Python dependencies with PEP 668 compatibility
- **`dependencies.txt`** - Python package requirements (enhanced with version pinning)

### Validation and Testing
- **`validate_setup_enhanced.sh`** - 🔍 **Comprehensive system validation** with detailed reporting
- **`validate_setup.sh`** - Basic validation script (legacy)
- **`check_dotnet_runtime.py`** - Tests .NET runtime compatibility and configuration
- **`test_basic_functionality.py`** - Basic functionality tests for development

### Documentation
- **`QUICKSTART.md`** - Quick installation guide for experienced users
- **`README.md`** - This file
- **Auto-generated files:**
  - **`INSTALLATION_SUMMARY.md`** - Generated after successful installation
  - **`VALIDATION_REPORT.md`** - Generated after validation

## 📋 Step-by-Step Installation

### 1. Prerequisites
```bash
# Ensure ROS2 is installed and sourced
source /opt/ros/humble/setup.bash  # or your ROS distro
echo $ROS_DISTRO  # Should show your ROS version
```

### 2. Run Master Installer
```bash
cd setup/
./install_all.sh
```

The master installer will:
- ✅ Check prerequisites (ROS2, OS compatibility)
- ✅ Install system dependencies (.NET, Mono, build tools)
- ✅ Install Python dependencies (pythonnet, pylablib, etc.)
- ✅ Install ROS2 dependencies via rosdep
- ✅ Build the workspace with colcon
- ✅ Validate the installation
- ✅ Generate installation summary

### 3. Manual Installation (Alternative)
```bash
# If you prefer step-by-step control:
./install_system_deps.sh      # System dependencies
./install_python_deps.sh      # Python packages  
cd .. && rosdep install --from-paths . --ignore-src -y  # ROS2 deps
colcon build --symlink-install  # Build workspace
cd setup && ./validate_setup_enhanced.sh  # Validate
```

## 🔧 PMCLib Installation (Hardware Only)

For actual planar motor hardware control:

```bash
# 1. Obtain PMCLib wheel from Match/IEMCA
# 2. Copy to local_libs directory
cp /path/to/pmclib-*.whl ../local_libs/

# 3. Install PMCLib
pip install ../local_libs/pmclib-*.whl

# 4. Validate
./validate_setup_enhanced.sh
```

## ✅ Validation and Testing

### Comprehensive Validation
```bash
./validate_setup_enhanced.sh
```

This checks:
- 🌐 ROS2 environment and tools
- 🔧 System dependencies (.NET, build tools)
- 🐍 Python dependencies and versions
- 📦 Workspace build status
- 🎮 PMCLib availability
- 🧪 Basic functionality tests

### Quick Functionality Test
```bash
python3 test_basic_functionality.py
```

### Launch Simulation Test
```bash
# Source workspace first
source ../install/setup.bash

# Test dual LTS300 simulation
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py

# Test single axis
ros2 launch promoc_bringup test_single_lts300.launch.py test_axis:=x
```

## 🐛 Troubleshooting

### Common Issues

**1. ROS2 not found:**
```bash
source /opt/ros/humble/setup.bash
export ROS_DISTRO=humble
```

**2. Permission denied:**
```bash
chmod +x *.sh
```

**3. Python dependencies fail (Ubuntu 24.04):**
```bash
# Create virtual environment
python3 -m venv ~/ros2_promoc_venv
source ~/ros2_promoc_venv/bin/activate
./install_python_deps.sh
```

**4. .NET issues:**
```bash
python3 check_dotnet_runtime.py
```

**5. Build failures:**
```bash
# Clean and rebuild
cd ..
rm -rf build install log
./setup/install_all.sh
```

### Get Help
- 📋 Check: `VALIDATION_REPORT.md` (auto-generated)
- 📝 See: `INSTALLATION_SUMMARY.md` (auto-generated)
- 🔍 Run: `./validate_setup_enhanced.sh` for detailed diagnostics

## 📁 Project Structure

```
ProMOC_Assembly/
├── linear_axis_nodes/          # Thorlabs LTS300 control
├── planar_motor_nodes/         # Planar motor with PMCLib  
├── promoc_assembly_interfaces/ # Custom ROS2 messages/services
├── promoc_bringup/            # Launch files and configurations
├── setup/ (this directory)    # Installation and validation
└── local_libs/               # Proprietary libraries (PMCLib)
```

## 📝 Notes

- All scripts are designed to be run from the `setup/` directory
- The master installer (`install_all.sh`) handles most edge cases automatically
- For development without hardware, mock implementations are used automatically
- PMCLib is proprietary and must be obtained separately from Match/IEMCA
