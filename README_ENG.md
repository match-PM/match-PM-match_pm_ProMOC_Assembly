ProMOC Assembly ROS2 System
A modular ROS2 system for high-precision assembly tasks using linear axes (Thorlabs LTS300) and planar motor systems.

🚀 Quick Start
# 1. Clone the repository into your ROS2 workspace
cd ~/ros2_ws/src
git clone <repository-url> promoc_assembly

# 2. Install external dependencies
cd promoc_assembly
vcs import ~/ros2_ws/src < dependencies.repos

# 3. Run the automated installation
cd setup
./install_all.sh

# 4. Launch the simulation
source ../install/setup.bash
ros2 launch promoc_bringup system.launch.py sim_mode:=true

# For demo with automated sequences
ros2 launch promoc_bringup promoc_assembly_demo_launch.py

📖 Documentation
Comprehensive documentation for each package:

- **[Setup & Installation](setup/README.md)** – Complete setup instructions with hardware integration
- **[Planar Motor Nodes](planar_motor_nodes/README.md)** – XBot control and PMCLib integration
- **[Linear Axis Nodes](linear_axis_nodes/README.md)** – Thorlabs LTS300 control with collision detection
- **[Camera Nodes](camera_nodes/README.md)** - Camera setup and operations
- **[Camera Callback Guide (DE)](camera_nodes/docs/callbacks_user_guide_de.md)** - Step-by-step service guide
- **[Camera Callback Guide (EN)](camera_nodes/docs/callbacks_user_guide_en.md)** - Plain-language service guide
- **[Camera Integration](camera_integration/README.md)** – IDS camera integration using camera_aravis2
- **[Core Library](promoc_core/README.md)** – Shared logic, error handling, and utilities
- **[Interface Definitions](promoc_assembly_interfaces/README.md)** – ROS2 messages and services
- **[Launch & Configuration](promoc_bringup/README.md)** – System startup and parameter management

🎯 Key Features
✅ Modular Architecture – Easy to extend and maintain.

✅ Hardware Abstraction – Seamlessly switch between simulation and real hardware.

✅ Safety Systems – Software limits and collision detection.

✅ High Precision – Sub-micrometer positioning.

✅ Camera Integration – IDS industrial cameras via GenICam/Aravis.

✅ ROS2 Native – Utilizes standard ROS2 interfaces and tools.

✅ Simulation Ready – Full Gazebo integration.

🔧 System Requirements
Operating System: Ubuntu 22.04 LTS (Recommended), 20.04/24.04 compatible

ROS2: Humble Hawksbill (or newer)

Python: 3.8+

Hardware (Optional):

Thorlabs LTS300 linear axes
IDS industrial cameras (GigEVision/USB3Vision)
PMC planar motor controller

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
PMCLib is integrated in the package, hardware-specific installation:

```bash
# 1. Obtain PMCLib wheel from Match/IEMCA (version 117.1.1+)
# 2. Install Python wheel (recommended: inside the venv created by install_all.sh)
pip install /path/to/pmclib-*.whl

# Optional (development): clone the PMCLib repo into the local drivers path
# so the planar motor nodes can import it directly:
# planar_motor_nodes/planar_motor_nodes/drivers/pmclib

# 4. Validate installation
./setup/validate_setup_enhanced.sh
```

**PMC Hardware Requirements:**
- PMC Controller accessible at `192.168.10.100`
- .NET 8.0 SDK (automatically installed)
- Network connectivity

**Mock Development (no hardware):**
```bash
export USE_MOCK_PMC=true
ros2 launch promoc_bringup system.launch.py sim_mode:=true
```

Linear Axes (Thorlabs LTS300)
**Hardware Auto-Discovery:** The system automatically detects connected Thorlabs devices.

```bash
# Grant user permissions for USB access
sudo usermod -a -G dialout $USER

# Test hardware detection
ls -la /dev/serial/by-id/usb-Thorlabs*

# Launch shows detected devices:
# 🛰️ Detected device: usb-Thorlabs_APT_Stepper_Motor_Controller_45407924
```

Serial numbers are configured in `promoc_bringup/config/linear_axes_params.yaml`.

🧪 Testing & Validation
Comprehensive testing capabilities for all system components:

```bash
# 1. Run comprehensive system validation
./setup/validate_setup_enhanced.sh

# 2. Test complete system (simulation)
source install/setup.bash
ros2 launch promoc_bringup system.launch.py sim_mode:=true

# 3. Demo with automated sequences
ros2 launch promoc_bringup promoc_assembly_demo_launch.py

# 4. Test individual components
ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true
ros2 run linear_axis_nodes lts300_node --ros-args -p use_sim_time:=true

# 5. Service tests
ros2 service call /mover_node/activate_xbots promoc_assembly_interfaces/srv/ActivateXbots "{activation_status: true}"
ros2 service call /lts300_x_axis/get_position promoc_assembly_interfaces/srv/GetPosition "{}"
```

🐛 Troubleshooting
If you encounter issues during installation or execution, please refer to our detailed troubleshooting guide:

➡️ TROUBLESHOOTING.md

Common Issues:

.NET Runtime not found: Ensure ./setup/install_system_deps.sh ran successfully, or install the .NET SDK manually.

Permission denied for /dev/ttyUSB*: Check user permissions (see Hardware Integration section).

PMCLib import error: Make sure the library was placed correctly in `local_libraries/` and installed.

Hardware not detected: Check USB connections and run `lsusb | grep Thorlabs`.

Service calls failing: Ensure all nodes are running with `ros2 node list`.

🛠️ Development & Contributing
Contributions to improve the project are welcome! Please follow our development guidelines.

Coding Standards & Pull Requests: Development Guide

ROS2 API: The available services and topics are documented in the API Reference.

