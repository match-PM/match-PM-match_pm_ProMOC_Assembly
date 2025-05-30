#!/bin/bash

# ProMOC Assembly System Dependencies Installation Script
# This script installs all necessary system dependencies for Ubuntu

set -e  # Exit on error

echo "Installing ProMOC Assembly System Dependencies..."
echo "=================================================="

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Install .NET SDK 8.0 for PMCLib support
echo "Installing .NET SDK 8.0..."
if sudo apt-get install -y dotnet-sdk-8.0 aspnetcore-runtime-8.0; then
    echo "✓ .NET SDK 8.0 installed successfully"
else
    echo "⚠ .NET SDK installation failed, will rely on Mono as fallback"
fi

# Install Mono as fallback for .NET runtime
echo "Installing Mono runtime as fallback..."
sudo apt-get install -y mono-complete mono-devel

# Install system dependencies for pythonnet
echo "Installing system dependencies for pythonnet..."
sudo apt-get install -y zlib1g clang libglib2.0-dev

# Install build tools
echo "Installing build tools..."
sudo apt-get install -y build-essential pkg-config

# Install Python development headers (if not already installed)
echo "Installing Python development headers and pip..."
sudo apt-get install -y python3-dev python3-pip python3-venv

# Verify .NET installation
echo "Verifying .NET installation..."
if command -v dotnet &> /dev/null; then
    echo "✓ .NET SDK installed successfully:"
    dotnet --version
    DOTNET_AVAILABLE=true
else
    echo "⚠ .NET SDK not available"
    DOTNET_AVAILABLE=false
fi

# Verify Mono installation
echo "Verifying Mono installation..."
if command -v mono &> /dev/null; then
    echo "✓ Mono runtime installed successfully:"
    mono --version | head -1
    MONO_AVAILABLE=true
else
    echo "✗ Mono runtime installation failed"
    MONO_AVAILABLE=false
fi

# Check if at least one runtime is available
if [ "$DOTNET_AVAILABLE" = false ] && [ "$MONO_AVAILABLE" = false ]; then
    echo "✗ Neither .NET nor Mono runtime is available!"
    echo "PMCLib functionality will not work without a .NET runtime."
    exit 1
fi

echo ""
echo "System dependencies installed successfully!"
echo ""
echo "Available .NET runtimes:"
if [ "$DOTNET_AVAILABLE" = true ]; then
    echo "✓ .NET Core/SDK 8.0"
fi
if [ "$MONO_AVAILABLE" = true ]; then
    echo "✓ Mono runtime"
fi
echo ""
echo "Next steps:"
echo "1. Install Python dependencies: ./install_python_deps.sh"
echo "2. Copy PMCLib wheel file to local_libs/ directory"
echo "3. Install PMCLib: pip install local_libs/pmclib-*.whl"
echo "4. Build ROS2 workspace: colcon build"
echo ""
echo "Note: PMCLib will automatically choose the best available .NET runtime."
