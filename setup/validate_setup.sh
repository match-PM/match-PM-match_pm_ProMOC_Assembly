#!/bin/bash

# ProMOC Assembly System Validation Script
# This script tests the complete installation and setup

# Removed set -e to allow all tests to run

echo "ProMOC Assembly System Validation"
echo "================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

test_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

echo "1. Testing System Dependencies..."
echo "--------------------------------"

# Test .NET Core
if command -v dotnet &> /dev/null; then
    DOTNET_VERSION=$(dotnet --version 2>/dev/null)
    test_status 0 ".NET Core available (version: $DOTNET_VERSION)"
else
    test_status 1 ".NET Core not available"
fi

# Test Mono
if command -v mono &> /dev/null; then
    MONO_VERSION=$(mono --version 2>/dev/null | head -1)
    test_status 0 "Mono runtime available ($MONO_VERSION)"
else
    test_status 1 "Mono runtime not available"
fi

# Test build tools
if command -v clang &> /dev/null; then
    test_status 0 "Clang compiler available"
else
    test_status 1 "Clang compiler not available"
fi

echo ""
echo "2. Testing Python Environment..."
echo "-------------------------------"

# Test Python version
PYTHON_VERSION=$(python3 --version 2>&1)
test_status 0 "Python available ($PYTHON_VERSION)"

# Test pip
if command -v pip &> /dev/null; then
    PIP_VERSION=$(pip --version 2>&1)
    test_status 0 "pip available ($PIP_VERSION)"
else
    test_status 1 "pip not available"
fi

# Test virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
    test_status 0 "Virtual environment active ($VIRTUAL_ENV)"
else
    test_status 1 "No virtual environment (recommended but not required)"
fi

echo ""
echo "3. Testing Python Dependencies..."
echo "--------------------------------"

# Test core dependencies
# Note: import names may differ from package names
declare -A PYTHON_DEPS
PYTHON_DEPS["numpy"]="numpy"
PYTHON_DEPS["pyserial"]="serial"
PYTHON_DEPS["pyusb"]="usb"
PYTHON_DEPS["rclpy"]="rclpy"

for package_name in "${!PYTHON_DEPS[@]}"; do
    import_name="${PYTHON_DEPS[$package_name]}"
    if python3 -c "import $import_name" 2>/dev/null; then
        test_status 0 "$package_name import successful"
    else
        test_status 1 "$package_name import failed"
    fi
done

# Test pythonnet (special case)
if python3 -c "import pythonnet" 2>/dev/null; then
    test_status 0 "pythonnet import successful"
    
    # Test .NET runtime loading
    if python3 check_dotnet_runtime.py >/dev/null 2>&1; then
        test_status 0 ".NET runtime configuration successful"
    else
        test_status 1 ".NET runtime configuration failed"
    fi
else
    test_status 1 "pythonnet import failed"
fi

# Test pylablib
if python3 -c "import pylablib" 2>/dev/null; then
    test_status 0 "pylablib import successful (linear axis support)"
else
    test_status 1 "pylablib import failed"
fi

echo ""
echo "4. Testing Hardware-Specific Dependencies..."
echo "-------------------------------------------"

# Test PMCLib directory
if [[ -d "../local_libs/pmclib" && -f "../local_libs/pmclib/__init__.py" ]]; then
    test_status 0 "PMCLib directory structure found (local_libs/pmclib/)"
    
    # Test PMCLib import by adding local_libs to path
    if python3 -c "import sys; sys.path.insert(0, '../local_libs'); import pmclib" 2>/dev/null; then
        test_status 0 "PMCLib import successful (planar motor support)"
    else
        test_status 1 "PMCLib import failed"
    fi
else
    test_status 1 "PMCLib directory not found (extract to local_libs/pmclib/)"
fi

echo ""
echo "5. Testing File Structure..."
echo "---------------------------"

# Test required files
REQUIRED_FILES=(
    "dependencies.txt"
    "install_system_deps.sh"
    "install_python_deps.sh"
    "check_dotnet_runtime.py"
    "../.gitignore"
    "../README.md"
    "QUICKSTART.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        test_status 0 "$file exists"
    else
        test_status 1 "$file missing"
    fi
done

# Test directory structure
REQUIRED_DIRS=(
    "../promoc_assembly_interfaces"
    "../linear_axis_nodes"
    "../planar_motor_nodes"
    "../promoc_bringup"
    "../local_libs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        test_status 0 "$dir/ directory exists"
    else
        test_status 1 "$dir/ directory missing"
    fi
done

echo ""
echo "6. Testing ROS2 Integration..."
echo "-----------------------------"

# Test ROS2 sourcing
if [ -f "/opt/ros/humble/setup.bash" ]; then
    test_status 0 "ROS2 Humble installation found"
    # Source ROS2 and test
    source /opt/ros/humble/setup.bash 2>/dev/null
elif [ -f "/opt/ros/jazzy/setup.bash" ]; then
    test_status 0 "ROS2 Jazzy installation found"
    # Source ROS2 and test
    source /opt/ros/jazzy/setup.bash 2>/dev/null
else
    test_status 1 "ROS2 installation not found"
fi

if command -v ros2 &> /dev/null; then
    test_status 0 "ros2 command available"
    
    # Test ROS_DISTRO
    if [[ -n "$ROS_DISTRO" ]]; then
        test_status 0 "ROS2 environment sourced (ROS_DISTRO=$ROS_DISTRO)"
    else
        test_status 1 "ROS2 environment not properly sourced"
    fi
else
    test_status 1 "ros2 command not available"
fi

if command -v colcon &> /dev/null; then
    test_status 0 "colcon build tool available"
else
    test_status 1 "colcon build tool not available"
fi

echo ""
echo "================================="
echo "Validation Summary"
echo "================================="
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! System is ready for ProMOC Assembly.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. cd ~/your_ros2_workspace && colcon build"
    echo "2. source install/setup.bash"
    echo "3. ros2 launch promoc_bringup promoc_assembly_launch.py"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Please address the issues above.${NC}"
    echo ""
    echo "Common solutions:"
    echo "- Run ./install_system_deps.sh for system dependencies"
    echo "- Run ./install_python_deps.sh for Python dependencies"
    echo "- Extract PMCLib to local_libs/pmclib/ for planar motor support"
    echo "- Install ROS2 Humble if not available"
    exit 1
fi
