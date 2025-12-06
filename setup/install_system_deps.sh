#!/bin/bash

# ProMOC Assembly System Dependencies Installation Script
# This script installs all necessary system dependencies for Ubuntu
# Supports: Ubuntu 22.04 (Jammy), Ubuntu 24.04 (Noble)
# ROS2 Distros: Humble (22.04), Jazzy (24.04)

set -e  # Exit on error

echo "Installing ProMOC Assembly System Dependencies..."
echo "=================================================="

# Detect Ubuntu version
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    UBUNTU_VERSION="$VERSION_ID"
    echo "Detected Ubuntu $UBUNTU_VERSION"
else
    echo "⚠ Could not detect OS version, assuming Ubuntu 24.04"
    UBUNTU_VERSION="24.04"
fi

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# ================================================================
# .NET Runtime Installation (for PMCLib)
# ================================================================
echo ""
echo "Installing .NET SDK 8.0..."
if sudo apt-get install -y dotnet-sdk-8.0 aspnetcore-runtime-8.0; then
    echo "✓ .NET SDK 8.0 installed successfully"
else
    echo "⚠ .NET SDK installation failed, will rely on Mono as fallback"
fi

# Install Mono as fallback for .NET runtime
echo "Installing Mono runtime as fallback..."
sudo apt-get install -y mono-complete mono-devel

# ================================================================
# Build Tools and Python Development
# ================================================================
echo ""
echo "Installing build tools..."
sudo apt-get install -y build-essential pkg-config cmake git

echo "Installing Python development headers and pip..."
sudo apt-get install -y python3-dev python3-pip python3-venv python3-full

# System dependencies for pythonnet
echo "Installing system dependencies for pythonnet..."
sudo apt-get install -y zlib1g clang libglib2.0-dev

# ================================================================
# Aravis Camera Library (for camera_aravis2)
# ================================================================
echo ""
echo "Installing Aravis camera library and tools..."
sudo apt-get install -y \
    libaravis-dev \
    aravis-tools \
    gir1.2-aravis-0.8 \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev

# ================================================================
# OpenCV and Image Processing
# ================================================================
echo ""
echo "Installing OpenCV and image processing dependencies..."
sudo apt-get install -y python3-opencv libopencv-dev

# ================================================================
# USB Device Permissions (for cameras and serial devices)
# ================================================================
echo ""
echo "Setting up USB device permissions..."

# Add current user to dialout group for serial port access (LTS300)
if groups $USER | grep -q dialout; then
    echo "✓ User already in dialout group"
else
    echo "Adding user to dialout group for serial port access..."
    sudo usermod -a -G dialout $USER
    echo "✓ User added to dialout group (logout/login required)"
fi

# Add current user to plugdev group for USB device access
if groups $USER | grep -q plugdev; then
    echo "✓ User already in plugdev group"
else
    echo "Adding user to plugdev group for USB device access..."
    sudo usermod -a -G plugdev $USER
    echo "✓ User added to plugdev group (logout/login required)"
fi

# ================================================================
# udev Rules for IDS USB3 Vision Cameras
# ================================================================
echo ""
echo "Installing udev rules for IDS USB cameras..."

UDEV_RULES_FILE="/etc/udev/rules.d/99-ids-usb-cameras.rules"

sudo tee $UDEV_RULES_FILE > /dev/null << 'EOF'
# IDS Imaging Development Systems USB3 Vision Cameras
# Vendor ID: 0x1409 (IDS Imaging Development Systems GmbH)

# Allow all users to access IDS USB3 Vision cameras
SUBSYSTEM=="usb", ATTRS{idVendor}=="1409", MODE="0666", GROUP="plugdev"

# Specific product IDs for different camera models
# U3-380xCP-C (USB3 Vision)
SUBSYSTEM=="usb", ATTRS{idVendor}=="1409", ATTRS{idProduct}=="8000", MODE="0666", GROUP="plugdev"

# Generic USB3 Vision device class
SUBSYSTEM=="usb", ATTRS{bDeviceClass}=="ef", ATTRS{bDeviceSubClass}=="02", MODE="0666", GROUP="plugdev"

# Ensure proper buffer size for USB3 cameras
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="1409", RUN+="/bin/sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'" 2>/dev/null || true
EOF

echo "✓ udev rules installed: $UDEV_RULES_FILE"

# Reload udev rules
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "✓ udev rules reloaded"

# ================================================================
# Verify Installations
# ================================================================
echo ""
echo "Verifying installations..."

# Check .NET
if command -v dotnet &> /dev/null; then
    echo "✓ .NET SDK installed: $(dotnet --version)"
    DOTNET_AVAILABLE=true
else
    echo "⚠ .NET SDK not available"
    DOTNET_AVAILABLE=false
fi

# Check Mono
if command -v mono &> /dev/null; then
    echo "✓ Mono runtime installed: $(mono --version | head -1)"
    MONO_AVAILABLE=true
else
    echo "✗ Mono runtime not available"
    MONO_AVAILABLE=false
fi

# Check Aravis
if command -v arv-tool-0.8 &> /dev/null; then
    echo "✓ Aravis tools installed: arv-tool-0.8 available"
else
    echo "⚠ arv-tool-0.8 not found in PATH"
fi

# Check Python
echo "✓ Python $(python3 --version | cut -d' ' -f2) installed"

# Check if at least one .NET runtime is available
if [ "$DOTNET_AVAILABLE" = false ] && [ "$MONO_AVAILABLE" = false ]; then
    echo "✗ Neither .NET nor Mono runtime is available!"
    echo "PMCLib functionality will not work without a .NET runtime."
    exit 1
fi

echo ""
echo "================================================================"
echo "System dependencies installed successfully!"
echo "================================================================"
echo ""
echo "Available .NET runtimes:"
if [ "$DOTNET_AVAILABLE" = true ]; then
    echo "  ✓ .NET Core/SDK 8.0"
fi
if [ "$MONO_AVAILABLE" = true ]; then
    echo "  ✓ Mono runtime"
fi
echo ""
echo "⚠ IMPORTANT: You must logout and login again for group changes to take effect!"
echo "   (dialout group for serial ports, plugdev group for USB devices)"
echo ""
echo "Next steps:"
echo "1. Logout and login again (for group membership)"
echo "2. Install Python dependencies: ./install_python_deps.sh"
echo "3. Build camera_aravis2: ./install_camera_aravis2.sh"
echo "4. Build ROS2 workspace: colcon build"
