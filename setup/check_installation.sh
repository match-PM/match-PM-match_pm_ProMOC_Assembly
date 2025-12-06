#!/bin/bash

# ================================================================
# ProMOC Assembly - Dependency Check Script
# ================================================================
# 
# Prüft welche Dependencies bereits installiert sind und was noch fehlt.
# Gibt klare Empfehlungen, was zu tun ist.
#
# Usage: ./check_installation.sh
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "================================================================"
echo "  ProMOC Assembly - Installation Status Check"
echo "================================================================"
echo ""

MISSING_COUNT=0
INSTALLED_COUNT=0

# ================================================================
# Helper Functions
# ================================================================

check_installed() {
    local name="$1"
    local status="$2"
    
    if [[ "$status" == "true" ]]; then
        echo -e "  ${GREEN}✓${NC} $name"
        ((INSTALLED_COUNT++))
    else
        echo -e "  ${RED}✗${NC} $name"
        ((MISSING_COUNT++))
    fi
}

# ================================================================
# ROS2 Check
# ================================================================

echo -e "${BLUE}[ROS2]${NC}"

# Check if ROS2 is installed
if [[ -f "/opt/ros/jazzy/setup.bash" ]]; then
    check_installed "ROS2 Jazzy" "true"
    ROS_DISTRO="jazzy"
elif [[ -f "/opt/ros/humble/setup.bash" ]]; then
    check_installed "ROS2 Humble" "true"
    ROS_DISTRO="humble"
else
    check_installed "ROS2 (Jazzy/Humble)" "false"
    ROS_DISTRO=""
fi

# Source ROS2 if available
if [[ -n "$ROS_DISTRO" ]]; then
    source /opt/ros/$ROS_DISTRO/setup.bash 2>/dev/null
fi

# Check colcon
if command -v colcon &> /dev/null; then
    check_installed "colcon build tools" "true"
else
    check_installed "colcon build tools" "false"
fi

echo ""

# ================================================================
# System Dependencies
# ================================================================

echo -e "${BLUE}[System Dependencies]${NC}"

# .NET SDK
if command -v dotnet &> /dev/null; then
    VERSION=$(dotnet --version 2>/dev/null || echo "unknown")
    check_installed ".NET SDK ($VERSION)" "true"
else
    check_installed ".NET SDK 8.0" "false"
fi

# Mono
if command -v mono &> /dev/null; then
    check_installed "Mono runtime" "true"
else
    check_installed "Mono runtime" "false"
fi

# Aravis
if command -v arv-tool-0.8 &> /dev/null; then
    check_installed "Aravis tools (arv-tool-0.8)" "true"
else
    check_installed "Aravis tools" "false"
fi

# libaravis-dev
if pkg-config --exists aravis-0.8 2>/dev/null; then
    check_installed "libaravis-dev" "true"
else
    check_installed "libaravis-dev" "false"
fi

echo ""

# ================================================================
# Python Dependencies
# ================================================================

echo -e "${BLUE}[Python Dependencies]${NC}"

# pythonnet
if python3 -c "import pythonnet" 2>/dev/null; then
    check_installed "pythonnet" "true"
else
    check_installed "pythonnet" "false"
fi

# pylablib
if python3 -c "import pylablib" 2>/dev/null; then
    check_installed "pylablib" "true"
else
    check_installed "pylablib" "false"
fi

# numba (with version check)
NUMBA_VERSION=$(python3 -c "import numba; print(numba.__version__)" 2>/dev/null || echo "")
if [[ -n "$NUMBA_VERSION" ]]; then
    if [[ "$NUMBA_VERSION" == "0.59"* ]]; then
        check_installed "numba $NUMBA_VERSION (correct version)" "true"
    else
        echo -e "  ${YELLOW}⚠${NC} numba $NUMBA_VERSION (should be 0.59.1)"
        ((MISSING_COUNT++))
    fi
else
    check_installed "numba 0.59.1" "false"
fi

# llvmlite
LLVMLITE_VERSION=$(python3 -c "import llvmlite; print(llvmlite.__version__)" 2>/dev/null || echo "")
if [[ -n "$LLVMLITE_VERSION" ]]; then
    if [[ "$LLVMLITE_VERSION" == "0.42"* ]]; then
        check_installed "llvmlite $LLVMLITE_VERSION (correct version)" "true"
    else
        echo -e "  ${YELLOW}⚠${NC} llvmlite $LLVMLITE_VERSION (should be 0.42.0)"
        ((MISSING_COUNT++))
    fi
else
    check_installed "llvmlite 0.42.0" "false"
fi

# pyserial
if python3 -c "import serial" 2>/dev/null; then
    check_installed "pyserial" "true"
else
    check_installed "pyserial" "false"
fi

echo ""

# ================================================================
# User Permissions
# ================================================================

echo -e "${BLUE}[User Permissions]${NC}"

# dialout group
if groups $USER | grep -q dialout; then
    check_installed "dialout group (serial ports)" "true"
else
    check_installed "dialout group (serial ports)" "false"
fi

# plugdev group
if groups $USER | grep -q plugdev; then
    check_installed "plugdev group (USB devices)" "true"
else
    check_installed "plugdev group (USB devices)" "false"
fi

# udev rules
if [[ -f "/etc/udev/rules.d/99-ids-usb-cameras.rules" ]]; then
    check_installed "IDS camera udev rules" "true"
else
    check_installed "IDS camera udev rules" "false"
fi

echo ""

# ================================================================
# External Packages
# ================================================================

echo -e "${BLUE}[External ROS2 Packages]${NC}"

# camera_aravis2
if [[ -n "$ROS_DISTRO" ]] && ros2 pkg list 2>/dev/null | grep -q camera_aravis2; then
    check_installed "camera_aravis2" "true"
elif [[ -d "$HOME/ros2_ws/src/camera_aravis2" ]] || [[ -d "$HOME/Documents/Development/Ros2/camera_aravis2" ]]; then
    echo -e "  ${YELLOW}⚠${NC} camera_aravis2 (found but not sourced)"
    ((MISSING_COUNT++))
else
    check_installed "camera_aravis2" "false"
fi

echo ""

# ================================================================
# Hardware Detection
# ================================================================

echo -e "${BLUE}[Hardware Detection]${NC}"

# IDS Camera
if lsusb 2>/dev/null | grep -q "1409:"; then
    CAMERA_INFO=$(lsusb | grep "1409:" | head -1)
    echo -e "  ${GREEN}✓${NC} IDS USB Camera detected"
    echo -e "      $CAMERA_INFO"
else
    echo -e "  ${YELLOW}○${NC} No IDS USB Camera detected (not connected?)"
fi

# Thorlabs LTS300
if ls /dev/ttyUSB* 2>/dev/null | head -1 > /dev/null; then
    SERIAL_PORTS=$(ls /dev/ttyUSB* 2>/dev/null | tr '\n' ' ')
    echo -e "  ${GREEN}✓${NC} Serial ports found: $SERIAL_PORTS"
else
    echo -e "  ${YELLOW}○${NC} No serial ports detected (LTS300 not connected?)"
fi

echo ""

# ================================================================
# Summary and Recommendations
# ================================================================

echo "================================================================"
echo "  Summary"
echo "================================================================"
echo ""
echo -e "  Installed: ${GREEN}$INSTALLED_COUNT${NC}"
echo -e "  Missing:   ${RED}$MISSING_COUNT${NC}"
echo ""

if [[ $MISSING_COUNT -eq 0 ]]; then
    echo -e "${GREEN}✓ All dependencies are installed!${NC}"
    echo ""
    echo "You can start using the system:"
    echo "  source /opt/ros/$ROS_DISTRO/setup.bash"
    echo "  source ~/Documents/Development/Ros2/promoc_assembly/install/setup.bash"
    echo ""
else
    echo -e "${YELLOW}Some dependencies are missing. Recommendations:${NC}"
    echo ""
    
    # Check what needs to be done
    if ! command -v dotnet &> /dev/null && ! command -v mono &> /dev/null; then
        echo "  1. Install system dependencies:"
        echo "     ./install_system_deps.sh"
        echo ""
    fi
    
    if ! python3 -c "import pylablib" 2>/dev/null || [[ "$NUMBA_VERSION" != "0.59"* ]]; then
        echo "  2. Install/fix Python dependencies:"
        echo "     ./install_python_deps.sh"
        echo ""
        echo "     Or manually fix numba version:"
        echo "     pip install --break-system-packages numba==0.59.1 llvmlite==0.42.0"
        echo ""
    fi
    
    if ! groups $USER | grep -q dialout; then
        echo "  3. Add user to dialout group (for serial ports):"
        echo "     sudo usermod -a -G dialout \$USER"
        echo "     # Then logout and login again!"
        echo ""
    fi
    
    if [[ ! -f "/etc/udev/rules.d/99-ids-usb-cameras.rules" ]]; then
        echo "  4. Install udev rules for IDS cameras:"
        echo "     sudo tee /etc/udev/rules.d/99-ids-usb-cameras.rules > /dev/null << 'EOF'"
        echo "SUBSYSTEM==\"usb\", ATTRS{idVendor}==\"1409\", MODE=\"0666\", GROUP=\"plugdev\""
        echo "EOF"
        echo "     sudo udevadm control --reload-rules && sudo udevadm trigger"
        echo ""
    fi
    
    if ! ros2 pkg list 2>/dev/null | grep -q camera_aravis2; then
        echo "  5. Install camera_aravis2 (for IDS cameras):"
        echo "     ./install_camera_aravis2.sh"
        echo ""
    fi
    
    echo "  Or run the full installer to fix everything:"
    echo "     ./install_all.sh"
    echo ""
fi

echo "================================================================"
