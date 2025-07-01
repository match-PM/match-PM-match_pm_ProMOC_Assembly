# Building the Project

## Workspace Setup

### Clone the Repository
```bash
# Navigate to ROS2 workspace source directory
cd ~/ros2_ws/src

# Clone the ProMOC Assembly repository
git clone <repository-url> promoc_assembly

# Navigate to the workspace root
cd ~/ros2_ws
```

### Install Package Dependencies
```bash
# Use rosdep to install ROS2 package dependencies
rosdep install --from-paths src --ignore-src -r -y

# Alternatively, run the automated setup
cd src/promoc_assembly/setup
./install_all.sh
```

## Building the Workspace

### Clean Build (Recommended for First Build)
```bash
# Navigate to workspace root
cd ~/ros2_ws

# Remove any existing build artifacts
rm -rf build install log

# Build all packages
colcon build

# Source the workspace
source install/setup.bash
```

### Build with Options
```bash
# Build with debug information
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug

# Build with optimizations
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release

# Build only specific packages
colcon build --packages-select linear_axis_nodes planar_motor_nodes

# Build with parallel jobs (adjust number based on your system)
colcon build --parallel-workers 4

# Build with verbose output for debugging
colcon build --event-handlers console_direct+
```

### Incremental Builds
```bash
# Build only changed packages
colcon build --packages-up-to promoc_bringup

# Build with symbolic links (faster for Python packages)
colcon build --symlink-install

# Build and install only modified packages
colcon build --cmake-clean-cache
```

## Build Configuration

### CMake Configuration
For C++ packages, you can configure CMake options:

```bash
# Set specific CMake flags
colcon build --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DBUILD_TESTING=ON
```

### Python Package Configuration
For Python packages, ensure proper setup:

```bash
# Verify Python environment
python3 --version
which python3

# Install Python dependencies if not already done
cd src/promoc_assembly/setup
./install_python_deps.sh
```

## Testing the Build

### Run Package Tests
```bash
# Run all tests
colcon test

# Run tests for specific packages
colcon test --packages-select linear_axis_nodes

# Run tests with verbose output
colcon test --event-handlers console_direct+

# Get test results
colcon test-result --all
colcon test-result --verbose
```

### Verify Installation
```bash
# Source the workspace
source install/setup.bash

# Check if packages are found
ros2 pkg list | grep promoc

# Verify nodes can be found
ros2 run linear_axis_nodes lts300_service_node --help
ros2 run planar_motor_nodes mover_service_node --help

# Check launch files
ros2 launch promoc_bringup --show-launch-file
```

## Build Troubleshooting

### Common Build Errors

#### Missing Dependencies
```bash
# Error: Package 'xxx' not found
# Solution: Install missing ROS2 packages
sudo apt install ros-humble-<package-name>

# Or install using rosdep
rosdep install --from-paths src --ignore-src -r -y
```

#### Python Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'xxx'
# Solution: Install Python dependencies
pip3 install --break-system-packages <package-name>

# Or run the dependency installer
cd src/promoc_assembly/setup
./install_python_deps.sh
```

#### CMake Configuration Errors
```bash
# Error: CMake configuration failed
# Solution: Clean and rebuild
rm -rf build install log
colcon build --cmake-clean-cache
```

#### Compilation Errors
```bash
# Error: Compilation failed
# Solution: Check compiler and dependencies
gcc --version
g++ --version

# Install missing development packages
sudo apt install build-essential cmake
```

#### Memory Issues
```bash
# Error: Virtual memory exhausted
# Solution: Reduce parallel jobs
colcon build --parallel-workers 1

# Or increase swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Advanced Troubleshooting

#### Debug Build Issues
```bash
# Build with maximum verbosity
colcon build --event-handlers console_direct+ --cmake-args -DCMAKE_VERBOSE_MAKEFILE=ON

# Check specific package build
colcon build --packages-select <package-name> --event-handlers console_direct+

# Manually invoke CMake for debugging
cd build/<package-name>
cmake --build . --verbose
```

#### Package Dependency Issues
```bash
# Check package dependencies
rosdep check --from-paths src --ignore-src

# Show detailed dependency information
rosdep keys --from-paths src --ignore-src

# Force dependency reinstallation
rosdep install --from-paths src --ignore-src -r -y --reinstall
```

#### Workspace Environment Issues
```bash
# Check ROS2 environment
printenv | grep ROS

# Verify workspace sourcing
echo $AMENT_PREFIX_PATH
echo $CMAKE_PREFIX_PATH

# Re-source environment
source /opt/ros/humble/setup.bash
source install/setup.bash
```

## Build Optimization

### Faster Builds
```bash
# Use ninja build system (if available)
colcon build --cmake-args -GNinja

# Use compiler cache (if ccache is installed)
colcon build --cmake-args -DCMAKE_CXX_COMPILER_LAUNCHER=ccache

# Build only necessary packages
colcon build --packages-up-to promoc_bringup

# Use symbolic links for Python packages
colcon build --symlink-install
```

### Continuous Integration
For automated builds:

```bash
# Create build script
cat > build.sh << 'EOF'
#!/bin/bash
set -e

# Clean previous build
rm -rf build install log

# Install dependencies
rosdep install --from-paths src --ignore-src -r -y

# Build workspace
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release

# Run tests
colcon test

# Check test results
colcon test-result --all
EOF

chmod +x build.sh
./build.sh
```

## Post-Build Setup

### Environment Configuration
Add to your `~/.bashrc`:

```bash
# ProMOC Assembly workspace
export PROMOC_WS=~/ros2_ws
source $PROMOC_WS/install/setup.bash

# Convenience aliases
alias promoc_ws='cd $PROMOC_WS'
alias promoc_build='cd $PROMOC_WS && colcon build'
alias promoc_test='cd $PROMOC_WS && colcon test'
```

### Validation
```bash
# Run the complete validation script
cd ~/ros2_ws/src/promoc_assembly/setup
./validate_setup_enhanced.sh

# Quick validation
source install/setup.bash
ros2 pkg list | grep promoc
ros2 launch promoc_bringup --show-args
```

## Next Steps
After successfully building the project, proceed to {doc}`validation` to validate your installation and run system tests.
