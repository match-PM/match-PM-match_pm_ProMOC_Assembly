#!/bin/bash

# ProMOC Assembly Python Dependencies Installation Script
# This script installs Python dependencies for both development and hardware modes
# Authoritative target platform: Ubuntu 22.04 / ROS 2 Humble / Python 3.10
# Also handles Ubuntu 24.04 / Python 3.12 PEP 668 restrictions for secondary
# local environments
# 
# CRITICAL: Includes version pins for numba/llvmlite/coverage to fix pylablib compatibility

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing ProMOC Assembly Python Dependencies..."
echo "================================================="

# Detect Ubuntu version and Python version
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    UBUNTU_VERSION="$VERSION_ID"
    echo "Detected Ubuntu $UBUNTU_VERSION"
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Detected Python $PYTHON_VERSION"

# Secondary local environments on Ubuntu 24.04 / Python 3.12 have PEP 668 restrictions
if [[ "$UBUNTU_VERSION" == "24.04" ]] || [[ "$PYTHON_VERSION" == "3.12" ]]; then
    echo "⚠ Ubuntu 24.04 / Python 3.12 detected - PEP 668 externally-managed environment"
    PEP668_MODE=true
fi

# Check if we're in a virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "✓ Virtual environment detected: $VIRTUAL_ENV"
    USE_VENV=true
elif [[ "$PEP668_MODE" == "true" ]]; then
    echo "⚠ This secondary local environment requires a virtual environment or --break-system-packages"
    echo "Recommendation: Use virtual environment for clean isolation"
    echo ""
    echo "Options:"
    echo "1) Create and use virtual environment (recommended)"
    echo "2) Install with --break-system-packages (not recommended)"
    echo "3) Use system packages where available"
    read -p "Choose option (1/2/3): " -n 1 -r
    echo
    case $REPLY in
        1)
            echo "Creating virtual environment..."
            if [[ ! -d ~/ros2_promoc_venv ]]; then
                python3 -m venv ~/ros2_promoc_venv
            fi
            echo "Activate with: source ~/ros2_promoc_venv/bin/activate"
            echo "Then re-run this script."
            exit 0
            ;;
        2)
            BREAK_SYSTEM_PACKAGES="--break-system-packages"
            echo "⚠ Using --break-system-packages (may affect system Python)"
            ;;
        3)
            echo "Will try system packages first, pip with --break-system-packages as fallback"
            SYSTEM_PACKAGES_FIRST=true
            BREAK_SYSTEM_PACKAGES="--break-system-packages"
            ;;
        *)
            echo "Aborted. Recommended approach:"
            echo "python3 -m venv ~/ros2_promoc_venv"
            echo "source ~/ros2_promoc_venv/bin/activate"
            echo "Then re-run this script."
            exit 1
            ;;
    esac
else
    echo "✓ System allows pip installation"
fi

# Function to install system packages first for the secondary PEP 668 path
install_system_packages() {
    echo "Trying system packages first..."
    local packages_installed=false
    
    # Try installing some dependencies via apt
    if command -v apt-get >/dev/null 2>&1; then
        echo "Installing available system Python packages..."
        sudo apt-get update
        
        # Install what's available via apt
        if apt-cache show python3-numpy >/dev/null 2>&1; then
            sudo apt-get install -y python3-numpy && echo "✓ numpy (system package)"
            packages_installed=true
        fi
        
        if apt-cache show python3-serial >/dev/null 2>&1; then
            sudo apt-get install -y python3-serial && echo "✓ pyserial (system package)"
            packages_installed=true
        fi
        
        if apt-cache show python3-usb >/dev/null 2>&1; then
            sudo apt-get install -y python3-usb && echo "✓ pyusb (system package)"
            packages_installed=true
        fi
    fi
    
    return $packages_installed
}

# Function to install via pip with appropriate flags
pip_install() {
    local package="$1"
    local extra_args="$2"
    
    if [[ -n "$BREAK_SYSTEM_PACKAGES" ]]; then
        pip install $BREAK_SYSTEM_PACKAGES $extra_args "$package"
    else
        pip install $extra_args "$package"
    fi
}

# Install system packages first if requested
if [[ "$SYSTEM_PACKAGES_FIRST" == "true" ]]; then
    install_system_packages || true  # Don't fail if system packages aren't available
fi

# Upgrade pip first
echo "Upgrading pip..."
pip_install "pip" "--upgrade"

# Install wheel first (needed for pythonnet)
echo "Installing wheel..."
pip_install "wheel"

# Install basic dependencies first
echo "Installing core dependencies..."
pip_install "numpy" "" || echo "⚠ numpy installation failed (may already be installed as system package)"
pip_install "pyserial" "" || echo "⚠ pyserial installation failed (may already be installed as system package)"
pip_install "pyusb" "" || echo "⚠ pyusb installation failed (may already be installed as system package)"

# Install pythonnet (may take time to build)
echo "Installing pythonnet (this may take a few minutes)..."
if ! pip_install "pythonnet"; then
    echo "⚠ pythonnet installation failed. Trying with additional build tools..."
    pip_install "setuptools" "--upgrade"
    pip_install "pythonnet"
fi

# Install pylablib with required numba/llvmlite version pins
echo ""
echo "Installing pylablib with compatible numba/llvmlite versions..."
echo "⚠ CRITICAL: numba 0.59.1 is required - newer versions conflict with coverage"

# First install llvmlite (specific version required by numba 0.59.1)
pip_install "llvmlite==0.42.0" "" || echo "⚠ llvmlite installation failed"

# Install numba (pinned to 0.59.1 for coverage compatibility)
pip_install "numba==0.59.1" "" || echo "⚠ numba installation failed"

# Install coverage with version constraint (>=7.4 conflicts with numba 0.59.1)
pip_install "coverage<7.4" "" || echo "⚠ coverage installation failed"

# Now install pylablib
pip_install "pylablib>=1.4.0"
echo "✓ pylablib installed with compatible numba version"

# Run .NET runtime detection and configuration
echo "Checking .NET runtime compatibility..."
if python3 check_dotnet_runtime.py; then
    echo "✓ .NET runtime configuration successful"
else
    echo "⚠ .NET runtime configuration failed - PMCLib may not work properly"
fi

# Check if PMCLib directory exists (optional)
#
# PMCLib ist proprietär und wird (optional) direkt in dieses Repo geklont, damit
# die Nodes die Bibliothek über den lokalen drivers/-Pfad finden können.
PMCLIB_DIR_REL="../planar_motor_nodes/planar_motor_nodes/drivers/pmclib"
if [[ -d "$PMCLIB_DIR_REL" ]]; then
    echo "✓ PMCLib directory found in $PMCLIB_DIR_REL"
    echo "  PMCLib kann von den Nodes über den lokalen drivers/-Pfad verwendet werden"
else
    echo "⚠ PMCLib directory not found in $PMCLIB_DIR_REL"
    echo "  Für Planarmotor-Funktionalität: PMCLib Repo klonen/ablegen unter:"
    echo "    planar_motor_nodes/planar_motor_nodes/drivers/pmclib"
fi

echo ""
echo "Python dependencies installation completed!"
echo ""
echo "Summary:"
echo "✓ Core Python packages installed"
echo "✓ pythonnet installed (for .NET interop)"
echo "✓ pylablib installed (for Thorlabs hardware)"
if [[ -d "$PMCLIB_DIR_REL" ]]; then
    echo "✓ PMCLib directory available (drivers/pmclib)"
elif [[ -d "local_libs/pmclib" ]]; then
    echo "✓ PMCLib directory available (legacy local_libs/pmclib)"
else
    echo "⚠ PMCLib directory not found (optional; expected under planar_motor_nodes/.../drivers/pmclib)"
fi
echo ""
echo "Next steps:"
echo "1. Build ROS2 workspace: cd ~/your_ros2_workspace && colcon build"
echo "2. Source workspace: source install/setup.bash"
echo "3. Test services: ros2 launch promoc_bringup system.launch.py driver_mode:=hardware"
