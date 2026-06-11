# ProMOC Setup

Single canonical installation guide for this repository.

## Expected Checkout Layout

The installer assumes the repository lives inside a ROS2 workspace, for example:

```text
<workspace>/
  src/
    promoc_assembly/
```

`install_all.sh` installs dependencies from the repository, then builds the parent workspace.

## What This Folder Contains

Main scripts:

- `install_all.sh`: full install for a fresh machine
- `install_system_deps.sh`: system packages, build tools, permissions
- `install_python_deps.sh`: Python environment and Python packages
- `install_camera_aravis2.sh`: optional camera driver install
- `check_installation.sh`: quick install status check
- `validate_setup_enhanced.sh`: deeper validation and diagnostics
- `repair.sh`: rebuild or repair the Python environment

Support files:

- `dependencies.txt`: pinned Python dependency list used by the installer
- `check_dotnet_runtime.py`: .NET runtime check helper
- `test_basic_functionality.py`: basic runtime sanity checks

## Supported Base Systems

The setup scripts target:

- Ubuntu 22.04 with ROS2 Humble
- Ubuntu 24.04 with ROS2 Jazzy

## Official Install Path

From the repository root:

```bash
cd setup
./install_all.sh
```

What this does:

- checks the ROS2 environment
- installs system dependencies
- installs Python dependencies
- installs optional camera support when enabled
- runs `rosdep`
- builds the workspace
- runs validation

## After Installation

If you are back in the repository root after running `./install_all.sh`, source the parent workspace:

```bash
# 1. Obtain PMCLib wheel from Match/IEMCA (version 117.1.1 or newer)
# 2. Install PMCLib wheel (recommended: create/use the venv created by install_all.sh)
pip install /path/to/pmclib-*.whl

# 3. OPTIONAL (advanced / legacy): place a PMCLib repo checkout here
#    so the nodes can import via the local drivers path:
#    planar_motor_nodes/planar_motor_nodes/drivers/pmclib

# 4. OPTIONAL: the helper modules are now shipped in this repo under
#    planar_motor_nodes/planar_motor_nodes/drivers/match_pm_xBot
#    (Older docs referenced setup/local_libraries/match_pm_xBot)

# 5. Validate
./validate_setup_enhanced.sh
```

### Notes about PMCLib locations

The mover node loads PMCLib in this order:

1. **Mock implementation** (simulation): `planar_motor_nodes/planar_motor_nodes/drivers/mock_pmclib.py`
2. **Local drivers checkout** (recommended for dev): `planar_motor_nodes/planar_motor_nodes/drivers/pmclib`
3. **System/venv install**: `pip install pmclib-*.whl`

The folder `setup/local_libraries/` is kept for legacy documentation only.
New setups should not rely on it.

**PMCLib Prerequisites:**
- **.NET Runtime**: .NET 8.0 SDK (automatically installed by `install_system_deps.sh`)
- **Python Packages**: `pythonnet>=3.0.0`, `wheel` (automatically installed)
- **Hardware**: PMC controller connected via network (IP: 192.168.10.100)

**Alternative for Mock Development:**
```bash
# Use built-in mock implementation (no PMCLib needed)
export USE_MOCK_PMC=true
ros2 launch promoc_bringup system.launch.py runtime_mode:=sim
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

# Test complete system (planar motor + linear axes)
ros2 launch promoc_bringup system.launch.py runtime_mode:=sim

# Official hardware runtime
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware

# Test individual components
ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true
ros2 run linear_axis_nodes lts300_node --ros-args -p use_sim_time:=true```

Recommended first checks:

```bash
make doctor-hw
make hw
```

Optional simulation path:

```bash
make sim
```

For day-to-day development directly from the repository root, you can also use the repo-local workflow:

```bash
make build
source install/setup.bash
```

## Manual Install Path

Use this only if you need step-by-step control:

```bash
cd setup
./install_system_deps.sh
./install_python_deps.sh
./install_camera_aravis2.sh   # optional, IDS camera only
cd ..
rosdep install --from-paths . --ignore-src -y
cd ..
colcon build --symlink-install
source install/setup.bash
cd src/promoc_assembly/setup
./validate_setup_enhanced.sh
```

## Hardware-Specific Notes

### Planar Motor / PMCLib

Real planar-motor hardware needs a PMCLib wheel provided separately.

Typical install:

```bash
pip install /path/to/pmclib-*.whl
```

If PMCLib is not available, use simulation or mock-based development instead.

### Camera Driver

`install_camera_aravis2.sh` is only needed for camera hardware setups that use `camera_aravis2`.

### Permissions

Some hardware access requires group or udev changes.
If the installer changes group membership, log out and log back in before testing hardware.

## Validation And Repair

Quick status check:

```bash
cd setup
./check_installation.sh
```

Full validation:

```bash
cd setup
./validate_setup_enhanced.sh
```

Repair Python environment:

```bash
cd setup
./repair.sh
```

Force full rebuild of the Python environment:

```bash
cd setup
./repair.sh --force
```

## Common Problems

ROS2 not sourced:

```bash
source /opt/ros/jazzy/setup.bash
```

or

```bash
source /opt/ros/humble/setup.bash
```

Build tools missing:

```bash
sudo apt install python3-colcon-common-extensions
```

Permissions not applied yet:

- log out and log back in
- then rerun `./check_installation.sh`

Python environment broken:

```bash
cd setup
./repair.sh
```

## What To Read Next

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
├── linear_axis_nodes/          # Thorlabs LTS300 control (README.md)
├── planar_motor_nodes/         # Planar motor with PMCLib (README.md)
├── promoc_assembly_interfaces/ # Custom ROS2 messages/services (README.md)
├── promoc_bringup/            # Launch files and configurations (README.md)
├── setup/ (this directory)    # Installation and validation
└── local_libraries/           # Proprietary libraries (PMCLib + docs)
    └── match_pm_xBot/         # PMCLib Python modules and documentation
```

## 🌐 Network Configuration

**For Hardware Operation:**
- **PMC Controller**: Must be accessible at `192.168.10.100`
- **Linear Axes**: Connected via USB (auto-detected at `/dev/serial/by-id/`)
- **Firewall**: Ensure ports are open for PMC communication

**Network Test:**
```bash
# Test PMC connectivity
ping 192.168.10.100

# Test USB device detection  
ls -la /dev/serial/by-id/usb-Thorlabs*
```

## 📝 Notes

- All scripts are designed to be run from the `setup/` directory
- The master installer (`install_all.sh`) handles most edge cases automatically
- For development without hardware, mock implementations are used automatically
- PMCLib is proprietary and must be obtained separately from Match/IEMCA
