ProMOC Assembly ROS2 System
A modular ROS2 system for high-precision assembly tasks using linear axes (Thorlabs LTS300) and planar motor systems.

🚀 Quick Start
# 1. Clone the repository into your ROS2 workspace
cd ~/ros2_ws/src
git clone <repository-url> promoc_assembly

# 2. Run the automated installation
cd promoc_assembly/setup
./install_all.sh

# 3. Launch the simulation
source ../install/setup.bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py

📖 Documentation
The complete documentation is available in the docs/ directory.

There you will find detailed instructions, tutorials, and the API reference.

Installation Guide – Complete setup instructions

Architecture Overview – Details on the system design

Tutorials – Step-by-step guides

🎯 Key Features
✅ Modular Architecture – Easy to extend and maintain.

✅ Hardware Abstraction – Seamlessly switch between simulation and real hardware.

✅ Safety Systems – Software limits and collision detection.

✅ High Precision – Sub-micrometer positioning.

✅ ROS2 Native – Utilizes standard ROS2 interfaces and tools.

✅ Simulation Ready – Full Gazebo integration.

🔧 System Requirements
Operating System: Ubuntu 22.04 LTS (Recommended), 20.04/24.04 compatible

ROS2: Humble Hawksbill (or newer)

Python: 3.8+

Hardware (Optional):

Thorlabs LTS300 linear axes

PMCLib-compatible planar motor

Critical Dependency for Planar Motor:

.NET SDK 8.0 (preferred) or Mono Runtime (fallback). Required by the pythonnet library to interface with the PMCLib.dll.

📋 Installation
Option 1: Automated Installation (Recommended)
This script installs all system and Python dependencies, sets up ROS2 dependencies, and builds the workspace.

cd setup/
./install_all.sh

Option 2: Manual Installation
Follow these steps for more control over the installation process.

# 1. Install system dependencies (incl. .NET SDK)
./setup/install_system_deps.sh

# 2. Install Python dependencies
./setup/install_python_deps.sh

# 3. Resolve ROS2 dependencies
cd ..
rosdep install --from-paths . --ignore-src -y

# 4. Build the workspace
colcon build --symlink-install

🔌 Hardware Integration
Planar Motor (PMCLib)
The proprietary PMCLib must be added to the project manually.

# 1. Obtain the PMCLib from your vendor (e.g., as a .whl or .zip file)

# 2. Copy the library into the `local_libs/` directory
#    (this directory is ignored by Git)
cp /path/to/pmclib-*.whl local_libs/

# 3. Install the Python wheel file
pip install local_libs/pmclib-*.whl

Linear Axes (Thorlabs LTS300)
Ensure the user has the necessary permissions to access the serial port.

# Grant the current user permanent access to serial devices
sudo usermod -a -G dialout $USER

# Verify permissions (after logging out and back in, or rebooting)
ls -l /dev/ttyUSB*

The serial numbers of the axes can be configured in the respective launch files.

🧪 Testing & Validation
A set of scripts and launch files is available to verify the setup and functionality.

# 1. Run a comprehensive validation of the entire setup
./setup/validate_setup_enhanced.sh

# 2. Test the Gazebo simulation with two axes
source install/setup.bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py

# 3. Test a single axis
ros2 launch promoc_bringup test_single_lts300.launch.py test_axis:=x

🐛 Troubleshooting
If you encounter issues during installation or execution, please refer to our detailed troubleshooting guide:

➡️ TROUBLESHOOTING.md

Common Issues:

.NET Runtime not found: Ensure ./setup/install_system_deps.sh ran successfully, or install the .NET SDK manually.

Permission denied for /dev/ttyUSB*: Check user permissions (see Hardware Integration section).

PMCLib import error: Make sure the library was placed correctly in local_libs/ and installed.

🛠️ Development & Contributing
Contributions to improve the project are welcome! Please follow our development guidelines.

Coding Standards & Pull Requests: Development Guide

ROS2 API: The available services and topics are documented in the API Reference.

📞 Support
Report Issues: Please create a new Issue on GitHub.

Questions & Discussions: Use GitHub Discussions.

