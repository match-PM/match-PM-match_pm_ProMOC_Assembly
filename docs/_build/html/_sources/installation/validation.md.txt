# Installation Validation

## Quick Validation

### Run Automated Validation Script
```bash
# Navigate to setup directory
cd ~/ros2_ws/src/promoc_assembly/setup

# Run comprehensive validation
./validate_setup_enhanced.sh

# Check validation report
cat VALIDATION_REPORT.md
```

This script performs comprehensive system checks and generates a detailed report.

## Manual Validation Steps

### 1. Environment Validation
```bash
# Check ROS2 environment
echo "ROS_DISTRO: $ROS_DISTRO"
echo "ROS_VERSION: $ROS_VERSION"
echo "ROS_PYTHON_VERSION: $ROS_PYTHON_VERSION"

# Check workspace sourcing
echo "AMENT_PREFIX_PATH: $AMENT_PREFIX_PATH"

# Verify ROS2 commands work
ros2 --version
ros2 node list
```

### 2. Package Validation
```bash
# Check ProMOC packages are installed
ros2 pkg list | grep promoc

# Expected output:
# linear_axis_nodes
# planar_motor_nodes  
# promoc_assembly_interfaces
# promoc_bringup

# Check package executables
ros2 pkg executables linear_axis_nodes
ros2 pkg executables planar_motor_nodes
ros2 pkg executables promoc_bringup
```

### 3. Interface Validation
```bash
# Check custom messages and services
ros2 interface list | grep promoc_assembly_interfaces

# Check specific interfaces
ros2 interface show promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute
ros2 interface show promoc_assembly_interfaces/srv/linear_axis/GetPosition
ros2 interface show promoc_assembly_interfaces/msg/linear_axis/LinearAxisInfo
```

### 4. Launch File Validation
```bash
# Check launch files are accessible
ros2 launch promoc_bringup --show-launch-files

# Validate launch file syntax
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py --show-args
ros2 launch promoc_bringup test_single_lts300.launch.py --show-args
```

### 5. Node Validation
```bash
# Test node imports (without running)
python3 -c "
from linear_axis_nodes.lts300_service_node import main
from planar_motor_nodes.mover_service_node import main
print('Node imports successful')
"

# Check node help messages
ros2 run linear_axis_nodes lts300_service_node --help
ros2 run planar_motor_nodes mover_service_node --help
```

## Hardware Validation

### USB Device Detection
```bash
# Check for connected Thorlabs devices
lsusb | grep -i thorlabs

# Check USB permissions
ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB serial devices found"

# Test USB access permissions
groups $USER | grep -q dialout && echo "User in dialout group" || echo "User NOT in dialout group"
```

### Network Configuration
```bash
# Check network interfaces for planar motor communication
ip addr show

# Test network connectivity (if planar motor IP is known)
# ping -c 3 192.168.1.10  # Replace with actual IP
```

## Simulation Validation

### Gazebo Integration Test
```bash
# Test Gazebo availability
which gazebo
gazebo --version

# Test Gazebo-ROS integration
ros2 pkg list | grep gazebo

# Quick Gazebo launch test (will open Gazebo)
timeout 10s ros2 launch gazebo_ros gazebo.launch.py &
sleep 5
pkill -f gazebo
echo "Gazebo launch test completed"
```

### URDF Validation
```bash
# Check URDF files syntax
cd ~/ros2_ws/src/promoc_assembly/promoc_bringup/urdf

# Validate main assembly URDF
check_urdf assemblies/dual_lts300_system.urdf.xacro 2>/dev/null && echo "URDF syntax valid" || echo "URDF has syntax errors"

# Test URDF processing
ros2 run xacro xacro assemblies/dual_lts300_system.urdf.xacro > /tmp/test_urdf.xml
echo "URDF processing test completed"
```

## Functional Validation

### Launch System Test
```bash
# Test dual LTS300 launch (simulation mode)
timeout 15s ros2 launch promoc_bringup dual_lts300_gazebo.launch.py &
LAUNCH_PID=$!

# Wait for system to start
sleep 10

# Check if nodes are running
ros2 node list | grep -E "(x_axis|z_axis|gazebo)"

# Check if services are available
ros2 service list | grep -E "(move_absolute|get_position|home)"

# Stop the launch
kill $LAUNCH_PID 2>/dev/null
sleep 2
pkill -f ros2 2>/dev/null

echo "Launch system test completed"
```

### Service Interface Test
```bash
# Start system in background for testing
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py &
LAUNCH_PID=$!

# Wait for startup
sleep 10

# Test service calls (with simulation data)
echo "Testing get_position service..."
timeout 5s ros2 service call /promoc_assembly/x_axis/get_position \
    promoc_assembly_interfaces/srv/linear_axis/GetPosition || echo "Service call failed"

echo "Testing move_absolute service..."
timeout 5s ros2 service call /promoc_assembly/x_axis/move_absolute \
    promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute \
    "{target_position: 0.01, velocity: 0.005}" || echo "Service call failed"

# Stop the system
kill $LAUNCH_PID 2>/dev/null
sleep 2
pkill -f ros2 2>/dev/null

echo "Service interface test completed"
```

## Dependencies Validation

### System Dependencies
```bash
# Check essential system tools
command -v cmake >/dev/null && echo "✓ CMake installed" || echo "✗ CMake missing"
command -v git >/dev/null && echo "✓ Git installed" || echo "✗ Git missing"
command -v python3 >/dev/null && echo "✓ Python3 installed" || echo "✗ Python3 missing"
command -v pip3 >/dev/null && echo "✓ Pip3 installed" || echo "✗ Pip3 missing"

# Check build tools
dpkg -l | grep -q build-essential && echo "✓ Build tools installed" || echo "✗ Build tools missing"
```

### Python Dependencies
```bash
# Test critical Python imports
python3 -c "
import sys
import numpy
import scipy  
import matplotlib
print(f'✓ Core Python packages available (Python {sys.version})')
" 2>/dev/null || echo "✗ Core Python packages missing"

# Test hardware control libraries
python3 -c "
try:
    import pylablib
    print('✓ pylablib available')
except ImportError:
    print('⚠ pylablib not available (Thorlabs support limited)')
" 2>/dev/null

# Test ROS2 Python integration
python3 -c "
import rclpy
import rclpy.node
print('✓ ROS2 Python integration working')
" 2>/dev/null || echo "✗ ROS2 Python integration failed"
```

### ROS2 Dependencies
```bash
# Check critical ROS2 packages
ros2 pkg list | grep -q "controller_manager" && echo "✓ Controller framework available" || echo "✗ Controller framework missing"
ros2 pkg list | grep -q "gazebo_ros" && echo "✓ Gazebo integration available" || echo "✗ Gazebo integration missing"
ros2 pkg list | grep -q "joint_state" && echo "✓ Robot state packages available" || echo "✗ Robot state packages missing"
```

## Performance Validation

### Build Performance Test
```bash
# Measure build time
cd ~/ros2_ws
time colcon build --packages-select linear_axis_nodes planar_motor_nodes

# Check build output sizes
du -sh build/ install/
```

### Runtime Performance Test
```bash
# Start system and measure resource usage
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py &
LAUNCH_PID=$!

# Wait for startup
sleep 10

# Check memory usage
ps aux | grep -E "(ros2|gazebo)" | awk '{sum+=$6} END {print "Memory usage: " sum/1024 " MB"}'

# Check CPU usage
top -bn1 | grep -E "(ros2|gazebo)" | awk '{sum+=$9} END {print "CPU usage: " sum "%"}'

# Stop system
kill $LAUNCH_PID 2>/dev/null
sleep 2
pkill -f ros2 2>/dev/null
```

## Validation Report

### Generate Comprehensive Report
```bash
# Run the enhanced validation script
cd ~/ros2_ws/src/promoc_assembly/setup
./validate_setup_enhanced.sh

# View the generated report
less VALIDATION_REPORT.md

# Or generate a simple summary
echo "=== ProMOC Assembly Validation Summary ==="
echo "Date: $(date)"
echo "User: $USER"
echo "ROS_DISTRO: $ROS_DISTRO"
echo "Workspace: $(pwd)"
echo ""
echo "Packages installed:"
ros2 pkg list | grep promoc | sed 's/^/  - /'
echo ""
echo "Hardware devices:"
lsusb | grep -i thorlabs | sed 's/^/  - /' || echo "  - No Thorlabs devices detected"
echo ""
echo "System status: Ready for operation"
```

## Troubleshooting Failed Validation

### Common Issues and Solutions

#### Environment Not Sourced
```bash
# Problem: ROS2 commands not found
# Solution: Source the environment
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

#### Package Not Found
```bash
# Problem: promoc packages not listed
# Solution: Rebuild workspace
cd ~/ros2_ws
colcon build
source install/setup.bash
```

#### Permission Errors
```bash
# Problem: USB device access denied
# Solution: Fix permissions
sudo usermod -a -G dialout $USER
# Log out and log back in
```

#### Import Errors
```bash
# Problem: Python modules not found
# Solution: Install missing dependencies
cd ~/ros2_ws/src/promoc_assembly/setup
./install_python_deps.sh
```

#### Launch Failures
```bash
# Problem: Launch files fail to start
# Solution: Check dependencies and rebuild
rosdep install --from-paths src --ignore-src -r -y
cd ~/ros2_ws
colcon build
```

## Next Steps

After successful validation:

1. **Ready for Operation**: System is ready for use
2. **Try Quick Start**: Follow the {doc}`../quickstart/index` guide
3. **Run Tutorials**: Explore system capabilities
4. **Hardware Integration**: Connect real hardware if available
5. **Development**: Start developing custom applications

For any persistent validation issues, check the troubleshooting section or seek support through the project documentation.
