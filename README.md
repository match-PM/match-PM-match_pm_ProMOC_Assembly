# ProMOC Assembly ROS2 Package

This repository contains the ProMOC Assembly system ROS2 packages for controlling linear axis and planar motor nodes.

## Repository Setup for ROS2 Workspace

This repository is designed to be cloned directly into the `src` folder of an existing ROS2 workspace.

### Prerequisites

- ROS2 Humble installed
- Python 3.8+
- Git
- Ubuntu 20.04 or later

### Installation

1. **Navigate to your ROS2 workspace src directory:**
   ```bash
   cd ~/your_ros2_workspace/src
   ```

2. **Clone this repository:**
   ```bash
   git clone <repository-url> promoc_assembly
   ```

3. **Install system dependencies (Ubuntu/Linux only):**
   ```bash
   cd promoc_assembly/setup
   ./install_system_deps.sh
   ```

4. **Install Python dependencies:**
   ```bash
   ./install_python_deps.sh
   ```
   This script will:
   - Install all Python packages from `dependencies.txt`
   - Test .NET runtime compatibility (.NET Core preferred, Mono as fallback)
   - Configure PMCLib for the best available runtime

### Quick Start Alternative

For experienced users, see `setup/QUICKSTART.md` for abbreviated instructions.

### Manual Installation (Advanced)

If using automated installation (`setup/install_python_deps.sh`), simply extract the PMCLib directory to `local_libs/` before running the script:
   ```bash
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
