# ProMOC Assembly ROS2 System

[![Documentation Status](https://img.shields.io/badge/docs-latest-brightgreen.svg)](./docs/)
[![ROS2](https://img.shields.io/badge/ROS2-Humble+-blue.svg)](https://docs.ros.org/en/humble/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A modular ROS2 system for high-precision assembly tasks using linear axes (Thorlabs LTS300) and planar motor systems.

## 🚀 Quick Start

```bash
# 1. Clone to ROS2 workspace
cd ~/ros2_ws/src
git clone <repository-url> promoc_assembly

# 2. One-command installation
cd promoc_assembly/setup
./install_all.sh

# 3. Launch simulation
source ../install/setup.bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py
```

## 📖 Documentation

**Complete documentation is available in the [`docs/`](./docs/) directory.**

### Quick Links
- **[Installation Guide](./docs/installation/)** - Complete setup instructions
- **[Quick Start](./docs/quickstart/)** - Get running in 5 minutes  
- **[API Reference](./docs/api/)** - Detailed API documentation
- **[Architecture](./docs/architecture/)** - System design overview
- **[Tutorials](./docs/tutorials/)** - Step-by-step guides

### Build Documentation Locally
```bash
cd docs/
make install    # Install documentation dependencies
make live       # Start auto-rebuilding server at http://localhost:8000
```

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Assembly Tasks  │  │ Motion Planning │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     ROS2 Service Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Linear Axis     │  │ Planar Motor    │                  │
│  │ Service Nodes   │  │ Service Nodes   │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Hardware Abstraction Layer                 │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ LTS300 Drivers  │  │ PMCLib Drivers  │                  │
│  │ (Real/Sim/Mock) │  │ (Real/Mock)     │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Package Overview

### Core Packages
- **[`linear_axis_nodes`](./linear_axis_nodes/)** - Thorlabs LTS300 linear positioning
- **[`planar_motor_nodes`](./planar_motor_nodes/)** - 2D planar motor control  
- **[`promoc_assembly_interfaces`](./promoc_assembly_interfaces/)** - Custom ROS2 messages/services
- **[`promoc_bringup`](./promoc_bringup/)** - System integration and launch files

### Support Directories
- **[`setup/`](./setup/)** - Installation and validation scripts
- **[`docs/`](./docs/)** - Comprehensive documentation
- **[`local_libs/`](./local_libs/)** - Proprietary libraries (PMCLib)

## 🎯 Key Features

- ✅ **Modular Architecture** - Easy to extend and maintain
- ✅ **Hardware Abstraction** - Seamless sim-to-real transfer  
- ✅ **Safety Systems** - Collision detection and limits
- ✅ **High Precision** - Sub-micrometer positioning
- ✅ **ROS2 Native** - Standard interfaces and tools
- ✅ **Simulation Ready** - Full Gazebo integration

## 🔧 System Requirements

- **OS**: Ubuntu 20.04/22.04/24.04 LTS
- **ROS2**: Humble Hawksbill or newer
- **Python**: 3.8+  
- **Hardware**: Thorlabs LTS300, PMCLib-compatible planar motor (optional)

## 📋 Installation Options

### Option 1: Automated Installation (Recommended)
```bash
cd setup/
./install_all.sh
```

### Option 2: Manual Step-by-Step
```bash
./install_system_deps.sh    # System dependencies
./install_python_deps.sh    # Python packages
cd .. && rosdep install --from-paths . --ignore-src -y  # ROS2 deps
colcon build --symlink-install  # Build workspace
```

### Option 3: Development Setup
```bash
cd docs/
make dev-setup  # Documentation + development tools
```

## 🧪 Testing & Validation

### System Validation
```bash
cd setup/
./validate_setup_enhanced.sh
```

### Basic Functionality Test
```bash
python3 setup/test_basic_functionality.py
```

### Simulation Tests
```bash
# Dual axis system
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py

# Single axis test
ros2 launch promoc_bringup test_single_lts300.launch.py test_axis:=x
```

## 🔌 Hardware Integration

### For PMCLib (Planar Motor)
```bash
# 1. Obtain PMCLib wheel from Match/IEMCA
# 2. Copy to local_libs/
cp /path/to/pmclib-*.whl local_libs/

# 3. Install
pip install local_libs/pmclib-*.whl
```

### For Thorlabs LTS300
- Configure serial numbers in launch files
- Set appropriate permissions for serial ports
- See [Hardware Documentation](./docs/hardware/) for details

## 🛠️ Development

### Contributing
See [Development Guide](./docs/development/) for:
- Coding standards
- Testing procedures  
- Pull request process
- Architecture guidelines

### Adding New Hardware
1. Implement driver interface
2. Create ROS2 service node
3. Add URDF description
4. Create launch files
5. Update documentation

## 📞 Support

- 📖 **Documentation**: [`docs/`](./docs/) directory
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions  
- 📧 **Contact**: ProMOC Assembly Team

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**For detailed instructions, please refer to the [complete documentation](./docs/).**
   # Extract PMCLib to local_libs directory
   unzip /path/to/pmclib.zip -d local_libs/
   # or copy PMCLib directory manually
   cp -r /path/to/pmclib/ local_libs/
   cd setup
   ./install_python_deps.sh
   ```

### Manual Installation (Advanced)

**System Dependencies:**
   - .NET SDK 8.0 (preferred) OR Mono runtime (fallback)
   - pythonnet build dependencies
   - Development tools

**Python Dependencies:**
   ```bash
   pip install -r setup/dependencies.txt
   python3 setup/check_dotnet_runtime.py  # Test .NET runtime compatibility
   ```

**Hardware Dependencies:**
   **For Planar Motor (PMCLib):**
   ```bash
   # Extract PMCLib directory to local_libs
   unzip /path/to/pmclib.zip -d local_libs/
   # or copy PMCLib directory manually
   cp -r /path/to/pmclib/ local_libs/
   # PMCLib will be imported automatically via Python path
   ```

   **For Linear Axis:**
   - pylablib (included in dependencies.txt)

5. **Build the workspace:**
   ```bash
   cd ~/your_ros2_workspace
   colcon build --packages-select promoc_assembly_interfaces linear_axis_nodes planar_motor_nodes promoc_bringup
   ```

6. **Source the workspace:**
   ```bash
   source install/setup.bash
   ```

### Package Structure

```
promoc_assembly/
├── promoc_assembly_interfaces/    # Service and message definitions
├── linear_axis_nodes/            # Linear axis control nodes (Thorlabs LTS300)
├── planar_motor_nodes/           # Planar motor control nodes (PMCLib)
├── promoc_bringup/              # Launch files and configurations
├── local_libs/                  # Local libraries (gitignored)
│   └── pmclib/                  # PMC Python library for planar motors
├── setup/                       # Installation and setup scripts
│   ├── dependencies.txt         # Python dependencies
│   ├── install_system_deps.sh   # System dependencies installation script
│   ├── install_python_deps.sh   # Python dependencies installation script
│   ├── check_dotnet_runtime.py  # .NET runtime compatibility checker
│   ├── validate_setup.sh        # System validation script
│   ├── test_basic_functionality.py # Basic functionality test
│   ├── QUICKSTART.md            # Quick start guide
│   ├── SETUP_SUMMARY.md         # Project overview
│   └── VALIDATION_REPORT.md     # Testing results
├── .gitignore                   # Git ignore file
└── README.md                    # This file
```

### Usage

#### Running with Mock Services (Development/Testing)
```bash
# Launch all services in mock mode
ros2 launch promoc_bringup promoc_assembly_launch.py
```

#### Running with Real Hardware
```bash
# Ensure PMCLib is installed in local_libs/
# Launch with hardware integration
ros2 launch promoc_bringup promoc_assembly_hardware_launch.py
```

### Available Services

#### Linear Axis Services
- `/linear_axis/move_absolute` - Move to absolute position
- `/linear_axis/move_relative` - Move relative distance
- `/linear_axis/stop` - Stop movement
- `/linear_axis/home` - Home the axis
- `/linear_axis/get_position` - Get current position

#### Planar Motor Services
- `/planar_motor/move_absolute` - Move to absolute position
- `/planar_motor/move_relative` - Move relative distance
- `/planar_motor/move_circular` - Circular movement
- `/planar_motor/stop` - Stop movement
- `/planar_motor/home` - Home the mover
- `/planar_motor/get_position` - Get current position

### Service Response Format

All services return a standardized response:
```
bool success          # True if operation succeeded
string status_message # Detailed status or error message
```

### Development

#### Mock Mode
The system includes mock implementations for development without hardware:
- All services return success responses with simulated behavior
- Useful for testing integration and developing higher-level applications

#### Hardware Integration
- Place PMCLib in `local_libs/` directory
- The system automatically detects and uses real hardware drivers
- Ensure proper permissions and hardware connections

### Troubleshooting

1. **System Dependencies:**
   - **Dotnet not found:** Run `sudo apt-get install -y dotnet-sdk-8.0`
   - **Pythonnet build fails:** Install build dependencies: `sudo apt-get install -y clang libglib2.0-dev`
   - **Permission denied on install_system_deps.sh:** Run `chmod +x setup/install_system_deps.sh`

2. **Python Dependencies:**
   - **Pylablib import error:** Ensure pyserial and pyusb are installed: `pip install pyserial pyusb`
   - **Pythonnet import error:** Run `python3 setup/check_dotnet_runtime.py` to diagnose
   - **PMCLib import fails:** Try different runtime: see troubleshooting below

3. **.NET Runtime Issues:**
   - **"No .NET runtime found":** Install .NET SDK: `sudo apt-get install dotnet-sdk-8.0`
   - **".NET Core fails":** Try Mono fallback: `sudo apt-get install mono-complete`
   - **Both runtimes fail:** Check `python3 setup/check_dotnet_runtime.py` output
   - **PMCLib runtime error:** Delete `local_libs/pmclib_runtime_config.py` and rerun setup

4. **Hardware Connection:**
   - **Linear Axis:** Check USB connection and permissions: `ls -la /dev/ttyUSB*`
   - **Planar Motor:** Verify PMCLib installation and .NET runtime

5. **Build Errors:**
   - Ensure all ROS2 dependencies are installed
   - Check that workspace is properly sourced

6. **Service Not Available:**
   - Verify nodes are running: `ros2 node list`
   - Check service availability: `ros2 service list`

6. **Hardware Connection Issues:**
   - **Linear Axis:** Check device permissions: `sudo chmod 666 /dev/ttyUSB*`
   - **Planar Motor:** Verify PMCLib and PMCLIB.dll are accessible
   - Review logs: `ros2 log info`

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both mock and hardware modes
5. Submit a pull request

### License

[Add your license information here]

### Support

For questions and support, please [add contact information or issue tracker].
