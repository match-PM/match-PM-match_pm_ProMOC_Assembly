# Dependencies

## Project Dependencies Overview

The ProMOC Assembly system requires several categories of dependencies:
- **System packages**: OS-level libraries and tools
- **Python packages**: Python libraries for device control and utilities
- **ROS2 packages**: ROS2-specific dependencies
- **Optional packages**: Additional tools for development and simulation

## Automated Installation

### Quick Install (Recommended)
Use the provided installation scripts for automatic dependency setup:

```bash
# Navigate to project setup directory
cd ~/ros2_ws/src/promoc_assembly/setup

# Run the complete installation script
chmod +x install_all.sh
./install_all.sh
```

This script will:
1. Install system dependencies
2. Install Python dependencies  
3. Install ROS2 package dependencies
4. Validate the installation

### Manual Installation Steps

If you prefer manual installation or need to troubleshoot:

```bash
# Install system dependencies
chmod +x install_system_deps.sh
./install_system_deps.sh

# Install Python dependencies
chmod +x install_python_deps.sh
./install_python_deps.sh

# Validate installation
chmod +x validate_setup_enhanced.sh
./validate_setup_enhanced.sh
```

## System Dependencies

### Core System Packages
```bash
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    python3-dev \
    python3-pip \
    python3-venv \
    curl \
    wget \
    software-properties-common \
    pkg-config \
    libudev-dev \
    libusb-1.0-0-dev \
    libftdi1-dev \
    udev
```

### Hardware Interface Dependencies
```bash
# For Thorlabs LTS300 support
sudo apt install -y \
    libusb-1.0-0-dev \
    libftdi1-dev \
    python3-serial \
    python3-usb

# For network communications
sudo apt install -y \
    net-tools \
    netplan.io \
    iproute2
```

### Documentation and Development Tools
```bash
# Documentation tools
sudo apt install -y \
    doxygen \
    graphviz \
    python3-sphinx \
    python3-sphinx-rtd-theme

# Development tools
sudo apt install -y \
    gdb \
    valgrind \
    clang-format \
    python3-flake8 \
    python3-black
```

## Python Dependencies

### Core Python Packages
```bash
pip3 install --break-system-packages \
    numpy>=1.21.0 \
    scipy>=1.7.0 \
    matplotlib>=3.5.0 \
    pyyaml>=6.0 \
    setuptools>=65.0 \
    wheel>=0.37.0
```

### Hardware Control Libraries
```bash
# Thorlabs device control
pip3 install --break-system-packages \
    pylablib>=1.4.0 \
    pyserial>=3.5 \
    pyusb>=1.2.0

# General hardware interfaces
pip3 install --break-system-packages \
    pymodbus>=3.0.0 \
    python-can>=4.0.0
```

### ROS2 Python Utilities
```bash
pip3 install --break-system-packages \
    transforms3d>=0.4.0 \
    python-dotenv>=0.19.0 \
    psutil>=5.8.0
```

### Documentation Dependencies
```bash
pip3 install --break-system-packages \
    sphinx>=4.0.0 \
    sphinx-rtd-theme>=1.0.0 \
    myst-parser>=0.18.0 \
    sphinx-autodoc-typehints>=1.12.0
```

## ROS2 Package Dependencies

### Core ROS2 Packages
```bash
sudo apt install -y \
    ros-humble-control-msgs \
    ros-humble-controller-manager \
    ros-humble-controller-interface \
    ros-humble-hardware-interface \
    ros-humble-pluginlib \
    ros-humble-rclcpp \
    ros-humble-rclpy
```

### Simulation and Visualization
```bash
sudo apt install -y \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-gazebo-ros-control \
    ros-humble-joint-state-publisher \
    ros-humble-joint-state-publisher-gui \
    ros-humble-robot-state-publisher \
    ros-humble-rviz2 \
    ros-humble-xacro
```

### Testing and Quality Assurance
```bash
sudo apt install -y \
    ros-humble-launch-testing \
    ros-humble-launch-testing-ament-cmake \
    ros-humble-ament-cmake-gtest \
    ros-humble-ament-cmake-pytest \
    python3-pytest \
    python3-pytest-cov
```

## Proprietary Dependencies

### PMCLib (Planar Motor Control)
The planar motor system requires proprietary libraries:

```bash
# Create directory for proprietary libraries
mkdir -p ~/ros2_ws/src/promoc_assembly/local_libs

# Extract PMCLib (provided separately)
# tar -xzf PMCLib.tar.gz -C ~/ros2_ws/src/promoc_assembly/local_libs/
```

**Note**: PMCLib must be obtained separately from the planar motor vendor and is not included in this repository.

### Thorlabs Software (Optional)
For advanced Thorlabs features:

```bash
# Download and install Thorlabs APT software
# Follow instructions from Thorlabs website
# Usually installed to /opt/thorlabs/
```

## Development Dependencies (Optional)

### Code Quality Tools
```bash
# Install additional development tools
pip3 install --break-system-packages \
    pre-commit>=2.15.0 \
    black>=22.0.0 \
    isort>=5.10.0 \
    flake8>=4.0.0 \
    mypy>=0.910

# Install pre-commit hooks
cd ~/ros2_ws/src/promoc_assembly
pre-commit install
```

### Performance Profiling
```bash
# Install profiling tools
pip3 install --break-system-packages \
    cProfile \
    memory-profiler>=0.60.0 \
    line-profiler>=3.3.0

sudo apt install -y \
    valgrind \
    perf-tools-unstable
```

## Dependency Verification

### Check Installation Status
```bash
# Run the validation script
cd ~/ros2_ws/src/promoc_assembly/setup
./validate_setup_enhanced.sh
```

### Manual Verification Commands
```bash
# Check Python packages
python3 -c "import numpy, scipy, matplotlib, pylablib; print('Python packages OK')"

# Check ROS2 packages
ros2 pkg list | grep -E "(control|gazebo|joint)" | head -5

# Check system tools
which cmake gcc python3 pip3

# Check hardware access
ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB devices found"
```

## Troubleshooting Dependencies

### Common Issues

#### PIP Package Installation Failures
```bash
# If pip install fails, try updating pip
python3 -m pip install --upgrade pip

# For system packages, use --break-system-packages flag
pip3 install --break-system-packages package_name

# Alternative: use virtual environment
python3 -m venv ~/promoc_venv
source ~/promoc_venv/bin/activate
pip install package_name
```

#### USB Permission Issues
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Create udev rules for Thorlabs devices
sudo tee /etc/udev/rules.d/99-thorlabs.rules << EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="1313", MODE="0666", GROUP="dialout"
EOF

sudo udevadm control --reload-rules
```

#### ROS2 Package Not Found
```bash
# Update package database
sudo apt update

# Search for available packages
apt-cache search ros-humble-package-name

# Check ROS2 installation
echo $ROS_DISTRO
source /opt/ros/humble/setup.bash
```

#### Memory Issues During Compilation
```bash
# Limit parallel jobs during build
export MAKEFLAGS=-j2
colcon build --parallel-workers 2
```

### Dependency Conflicts

#### Python Package Conflicts
```bash
# Check for conflicting packages
pip3 list --outdated

# Force reinstall problematic packages
pip3 install --force-reinstall package_name

# Use virtual environment to isolate dependencies
python3 -m venv ~/clean_env
source ~/clean_env/bin/activate
```

#### Version Compatibility
```bash
# Check installed versions
python3 --version
ros2 --version
gcc --version

# Check package versions
pip3 show package_name
dpkg -l | grep ros-humble
```

## Next Steps
After installing all dependencies, proceed to {doc}`building` to build the ProMOC Assembly workspace.
