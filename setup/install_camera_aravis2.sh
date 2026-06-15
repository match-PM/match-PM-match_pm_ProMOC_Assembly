#!/bin/bash

# ProMOC Assembly - camera_aravis2 Installation Script
# This script clones and builds the camera_aravis2 package from FraunhoferIOSB
# Required for IDS USB3 Vision camera integration

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default installation location (outside promoc_assembly to keep it separate)
DEFAULT_CAMERA_WS="$HOME/ros2_ws"
CAMERA_ARAVIS2_REPO="https://github.com/FraunhoferIOSB/camera_aravis2.git"

echo "================================================================"
echo "camera_aravis2 Installation Script"
echo "================================================================"
echo ""

# Detect ROS2 distribution
if [[ -z "$ROS_DISTRO" ]]; then
    # Try to source ROS2
    if [[ -f "/opt/ros/humble/setup.bash" ]]; then
        source /opt/ros/humble/setup.bash
        echo "✓ ROS2 Humble detected and sourced (authoritative target)"
    elif [[ -f "/opt/ros/jazzy/setup.bash" ]]; then
        source /opt/ros/jazzy/setup.bash
        echo "✓ ROS2 Jazzy detected and sourced (secondary local environment)"
    else
        echo "✗ No ROS2 installation found!"
        echo "Please install ROS2 Humble first."
        exit 1
    fi
else
    echo "✓ ROS2 $ROS_DISTRO already sourced"
fi

# Check for colcon
if ! command -v colcon &> /dev/null; then
    echo "Installing colcon build tools..."
    sudo apt-get update
    sudo apt-get install -y python3-colcon-common-extensions
fi

# Ask user for installation location
echo ""
echo "Where should camera_aravis2 be installed?"
echo "1) Default workspace: $DEFAULT_CAMERA_WS"
echo "2) Same workspace as promoc_assembly: $(dirname "$PROJECT_ROOT")"
echo "3) Custom location"
read -p "Choose option (1/2/3) [1]: " -r
echo

case $REPLY in
    2)
        CAMERA_WS="$(dirname "$PROJECT_ROOT")"
        ;;
    3)
        read -p "Enter custom workspace path: " -r
        CAMERA_WS="$REPLY"
        ;;
    *)
        CAMERA_WS="$DEFAULT_CAMERA_WS"
        ;;
esac

CAMERA_ARAVIS2_DIR="$CAMERA_WS/src/camera_aravis2"

echo "Installation location: $CAMERA_WS"
echo ""

# Create workspace if it doesn't exist
if [[ ! -d "$CAMERA_WS/src" ]]; then
    echo "Creating workspace directory..."
    mkdir -p "$CAMERA_WS/src"
fi

# Clone or update camera_aravis2
if [[ -d "$CAMERA_ARAVIS2_DIR" ]]; then
    echo "camera_aravis2 already exists, updating..."
    cd "$CAMERA_ARAVIS2_DIR"
    git pull origin main || git pull origin master || echo "⚠ Could not update, using existing version"
else
    echo "Cloning camera_aravis2 from FraunhoferIOSB..."
    cd "$CAMERA_WS/src"
    git clone "$CAMERA_ARAVIS2_REPO"
fi

# Install ROS2 dependencies via rosdep
echo ""
echo "Installing ROS2 dependencies..."
cd "$CAMERA_WS"
rosdep update || true
rosdep install --from-paths src --ignore-src -y --rosdistro $ROS_DISTRO || {
    echo "⚠ Some rosdep dependencies could not be installed automatically"
    echo "  Trying to install known dependencies manually..."
    sudo apt-get install -y \
        ros-${ROS_DISTRO}-camera-info-manager \
        ros-${ROS_DISTRO}-image-transport \
        ros-${ROS_DISTRO}-cv-bridge \
        ros-${ROS_DISTRO}-image-geometry || true
}

# Build camera_aravis2
echo ""
echo "Building camera_aravis2..."
cd "$CAMERA_WS"
colcon build --packages-select camera_aravis2 --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Source the workspace
echo ""
echo "Sourcing workspace..."
source "$CAMERA_WS/install/setup.bash"

# Verify installation
echo ""
echo "Verifying installation..."
if ros2 pkg list | grep -q camera_aravis2; then
    echo "✓ camera_aravis2 package installed successfully"
else
    echo "⚠ camera_aravis2 package not found in ros2 pkg list"
    echo "  Make sure to source the workspace: source $CAMERA_WS/install/setup.bash"
fi

# Test camera discovery
echo ""
echo "Testing camera discovery..."
if command -v arv-tool-0.8 &> /dev/null; then
    echo "Available cameras (via arv-tool-0.8):"
    arv-tool-0.8 || echo "  No cameras detected or aravis not working"
else
    echo "⚠ arv-tool-0.8 not found, cannot list cameras"
fi

echo ""
echo "================================================================"
echo "camera_aravis2 Installation Complete"
echo "================================================================"
echo ""
echo "To use camera_aravis2 with promoc_assembly, add this to your ~/.bashrc:"
echo ""
echo "  source $CAMERA_WS/install/setup.bash"
echo ""
echo "Then build and source promoc_assembly as well."
echo ""
echo "Quick start:"
echo "  # Find your camera"
echo "  ros2 run camera_aravis2 camera_finder"
echo ""
echo "  # Start camera driver (replace GUID with your camera's GUID)"
echo "  ros2 launch camera_aravis2 camera_aravis2.launch.py guid:='YourCameraGUID'"
echo ""
echo "Camera workspace: $CAMERA_WS"
