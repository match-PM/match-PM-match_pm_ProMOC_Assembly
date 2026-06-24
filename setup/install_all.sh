#!/bin/bash

# ================================================================
# ProMOC Assembly Master Installation Script
# ================================================================
# 
# This script orchestrates the complete installation of all dependencies
# for the ProMOC Assembly ROS2 system.
#
# Authoritative target platform:
#   - Ubuntu 22.04 (Jammy) with ROS2 Humble
# Secondary convenience environment:
#   - Ubuntu 24.04 (Noble) with ROS2 Jazzy
#
# Components installed:
#   - System dependencies (.NET SDK, Mono, Aravis, build tools)
#   - Python dependencies (pythonnet, pylablib, numba, etc.)
#   - USB/Serial device permissions (udev rules, dialout group)
#   - camera_aravis2 driver (optional, for IDS cameras)
#   - ROS2 workspace build
#
# Author: ProMOC Assembly Team
# Version: 2.0
# ================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Installation options (can be overridden via environment variables)
INSTALL_CAMERA_ARAVIS2=${INSTALL_CAMERA_ARAVIS2:-true}
CAMERA_WS="${CAMERA_WS:-$HOME/ros2_ws}"
SKIP_GROUP_CHECK=${SKIP_GROUP_CHECK:-false}

# ================================================================
# Logging Functions
# ================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ================================================================
# Header and Help
# ================================================================

print_header() {
    echo ""
    echo "================================================================"
    echo "  ProMOC Assembly System - Complete Installation Script v2.0"
    echo "================================================================"
    echo ""
    echo "This script will install:"
    echo "  • System dependencies (.NET SDK, Mono, Aravis, build tools)"
    echo "  • Python dependencies (pythonnet, pylablib, numba, etc.)"
    echo "  • USB/Serial device permissions (dialout group, udev rules)"
    echo "  • camera_aravis2 driver (for IDS USB3 Vision cameras)"
    echo "  • ROS2 workspace (colcon build)"
    echo ""
    echo "Project root: $PROJECT_ROOT"
    echo "Workspace:    $WORKSPACE_ROOT"
    echo ""
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --no-camera       Skip camera_aravis2 installation"
    echo "  --camera-ws PATH  Custom workspace for camera_aravis2"
    echo "  --skip-groups     Skip dialout/plugdev group check"
    echo "  --non-interactive Run without prompts (use defaults)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  INSTALL_CAMERA_ARAVIS2=true/false"
    echo "  CAMERA_WS=/path/to/camera/workspace"
    echo "  SKIP_GROUP_CHECK=true/false"
}

# ================================================================
# Prerequisite Checks
# ================================================================

check_prerequisites() {
    log_step "Step 1: Checking Prerequisites"
    
    # Check if running on Ubuntu
    if [[ ! -f /etc/os-release ]]; then
        log_error "This script is designed for Ubuntu systems"
        exit 1
    fi
    
    source /etc/os-release
    UBUNTU_VERSION="$VERSION_ID"
    log_info "Detected OS: $PRETTY_NAME"
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Detected Python: $PYTHON_VERSION"
    
    # Check if ROS2 is installed
    if ! command -v ros2 &> /dev/null; then
        # Try to source ROS2 automatically
        if [[ -f "/opt/ros/humble/setup.bash" ]]; then
            source /opt/ros/humble/setup.bash
            log_info "Sourced ROS2 Humble (authoritative target)"
        elif [[ -f "/opt/ros/jazzy/setup.bash" ]]; then
            source /opt/ros/jazzy/setup.bash
            log_info "Sourced ROS2 Jazzy (secondary local environment)"
        else
            log_error "ROS2 not found! Please install ROS2 first:"
            echo ""
            echo "  Authoritative target: Ubuntu 22.04 (Humble):"
            echo "    https://docs.ros.org/en/humble/Installation.html"
            echo ""
            echo "  For Ubuntu 24.04 (Jazzy):"
            echo "    https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html"
            exit 1
        fi
    fi
    
    ROS_DISTRO=$(printenv ROS_DISTRO)
    if [[ -z "$ROS_DISTRO" ]]; then
        log_error "ROS_DISTRO not set! Source your ROS2 setup first."
        exit 1
    fi
    
    log_success "ROS2 $ROS_DISTRO detected"
    
    # Verify colcon is available
    if ! command -v colcon &> /dev/null; then
        log_warning "colcon not found, will be installed with system dependencies"
    fi
    
    # Check if we're in the correct directory
    if [[ ! -f "$SCRIPT_DIR/dependencies.txt" ]]; then
        log_error "dependencies.txt not found! Run this script from the setup/ directory"
        exit 1
    fi
    
    # Check workspace structure
    if [[ ! -d "$PROJECT_ROOT/camera_nodes" ]] || [[ ! -d "$PROJECT_ROOT/linear_axis_nodes" ]]; then
        log_warning "Some package directories not found - workspace may be incomplete"
    fi
    
    log_success "Prerequisites check passed"
}

# ================================================================
# Installation Functions
# ================================================================

install_colcon() {
    if ! command -v colcon &> /dev/null; then
        log_info "Installing colcon build tools..."
        sudo apt-get update
        sudo apt-get install -y python3-colcon-common-extensions
        log_success "colcon installed"
    fi
}

run_setup_script() {
    local script_path="$1"

    if [[ ! -x "$script_path" ]]; then
        chmod +x "$script_path"
    fi

    bash "$script_path"
}

install_system_deps() {
    log_step "Step 2: Installing System Dependencies"
    run_setup_script "$SCRIPT_DIR/install_system_deps.sh"
    log_success "System dependencies installed"
}

install_python_deps() {
    log_step "Step 3: Installing Python Dependencies"
    run_setup_script "$SCRIPT_DIR/install_python_deps.sh"
    log_success "Python dependencies installed"
}

install_camera_aravis2() {
    log_step "Step 4: Installing camera_aravis2 Driver"
    
    if [[ "$INSTALL_CAMERA_ARAVIS2" != "true" ]]; then
        log_info "Skipping camera_aravis2 installation (--no-camera)"
        return 0
    fi
    
    CAMERA_WS="$CAMERA_WS" run_setup_script "$SCRIPT_DIR/install_camera_aravis2.sh"
    log_success "camera_aravis2 installed"
}

install_ros2_deps() {
    log_step "Step 5: Installing ROS2 Dependencies"
    
    log_info "Updating rosdep..."
    
    # Initialize rosdep if not already done
    if ! rosdep --version &> /dev/null; then
        log_info "Initializing rosdep..."
        sudo rosdep init 2>/dev/null || true  # Don't fail if already initialized
    fi
    rosdep update
    
    # Install dependencies for all packages
    log_info "Installing ROS2 package dependencies..."
    cd "$PROJECT_ROOT"
    rosdep install --from-paths . --ignore-src -y --rosdistro $ROS_DISTRO || {
        log_warning "Some rosdep dependencies could not be installed automatically"
    }
    
    log_success "ROS2 dependencies installed"
}

build_workspace() {
    log_step "Step 6: Building ROS2 Workspace"
    
    cd "$WORKSPACE_ROOT"
    
    # Clean previous build if requested
    if [[ -d "build" ]] || [[ -d "install" ]] || [[ -d "log" ]]; then
        if [[ "$NON_INTERACTIVE" != "true" ]]; then
            read -p "Remove previous build artifacts? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf build install log
                log_info "Previous build artifacts removed"
            fi
        fi
    fi
    
    # Build all packages
    log_info "Building with colcon..."
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
    
    log_success "Workspace built successfully"
}

validate_installation() {
    log_step "Step 7: Validating Installation"
    
    local validation_passed=true
    
    # Check Python imports
    log_info "Testing Python dependencies..."
    
    python3 -c "import pythonnet; print('✓ pythonnet')" 2>/dev/null || {
        log_warning "pythonnet import failed"
        validation_passed=false
    }
    
    python3 -c "import pylablib; print('✓ pylablib')" 2>/dev/null || {
        log_warning "pylablib import failed"
        validation_passed=false
    }
    
    python3 -c "import numba; print(f'✓ numba {numba.__version__}')" 2>/dev/null || {
        log_warning "numba import failed"
        validation_passed=false
    }
    
    # Check ROS2 packages
    log_info "Testing ROS2 packages..."
    source "$WORKSPACE_ROOT/install/setup.bash"
    
    ros2 pkg list | grep -q linear_axis_nodes && echo "✓ linear_axis_nodes" || {
        log_warning "linear_axis_nodes not found"
        validation_passed=false
    }
    
    ros2 pkg list | grep -q camera_nodes && echo "✓ camera_nodes" || {
        log_warning "camera_nodes not found"
        validation_passed=false
    }
    
    ros2 pkg list | grep -q planar_motor_nodes && echo "✓ planar_motor_nodes" || {
        log_warning "planar_motor_nodes not found"
        validation_passed=false
    }
    
    # Check group membership
    if [[ "$SKIP_GROUP_CHECK" != "true" ]]; then
        log_info "Checking group membership..."
        
        if groups $USER | grep -q dialout; then
            echo "✓ User in dialout group (serial ports)"
        else
            log_warning "User NOT in dialout group - serial devices may not work"
            log_warning "Run: sudo usermod -a -G dialout \$USER && logout"
            validation_passed=false
        fi
        
        if groups $USER | grep -q plugdev; then
            echo "✓ User in plugdev group (USB devices)"
        else
            log_warning "User NOT in plugdev group - USB devices may not work"
            validation_passed=false
        fi
    fi
    
    if [[ "$validation_passed" == "true" ]]; then
        log_success "All validation checks passed"
    else
        log_warning "Some validation checks failed - see warnings above"
    fi
}

generate_setup_summary() {
    log_step "Generating Installation Summary"
    
    local summary_file="$SCRIPT_DIR/INSTALLATION_SUMMARY.md"
    
    cat > "$summary_file" << EOF
# ProMOC Assembly Installation Summary

**Installation Date:** $(date)
**System:** $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")
**ROS2 Distro:** $ROS_DISTRO
**Python Version:** $PYTHON_VERSION

## Installation Status

### System Dependencies
- .NET SDK 8.0: $(command -v dotnet &> /dev/null && echo "✓ Installed ($(dotnet --version))" || echo "✗ Not available")
- Mono Runtime: $(command -v mono &> /dev/null && echo "✓ Installed" || echo "✗ Not available")
- Aravis Tools: $(command -v arv-tool-0.8 &> /dev/null && echo "✓ Installed" || echo "✗ Not available")

### Python Dependencies
- pythonnet: $(python3 -c "import pythonnet; print('✓ Installed')" 2>/dev/null || echo "✗ Not installed")
- pylablib: $(python3 -c "import pylablib; print('✓ Installed')" 2>/dev/null || echo "✗ Not installed")
- numba: $(python3 -c "import numba; print(f'✓ {numba.__version__}')" 2>/dev/null || echo "✗ Not installed")

### ROS2 Workspace
- Workspace: $WORKSPACE_ROOT
- Build Status: $(test -d "$WORKSPACE_ROOT/install" && echo "✓ Built" || echo "✗ Not built")

### User Permissions
- dialout group: $(groups $USER | grep -q dialout && echo "✓ Member" || echo "✗ Not member (REQUIRED for serial ports)")
- plugdev group: $(groups $USER | grep -q plugdev && echo "✓ Member" || echo "✗ Not member")

## Quick Start

\`\`\`bash
# Source the workspace
source $WORKSPACE_ROOT/install/setup.bash

# Start LTS300 linear axis node
ros2 run linear_axis_nodes lts300_node --ros-args \\
    -r __node:=lts300_x_axis \\
    -p serial_port:=/dev/ttyUSB0

# Start camera stack (hardware mode, requires camera_aravis2)
ros2 launch promoc_bringup camera.launch.py driver_mode:=hardware
\`\`\`

## Troubleshooting

### Serial Port Access Denied
\`\`\`bash
sudo usermod -a -G dialout \$USER
# Then logout and login again
\`\`\`

### Camera Not Detected
\`\`\`bash
# List available cameras
arv-tool-0.8

# Check udev rules
ls -la /etc/udev/rules.d/99-ids*
\`\`\`

### Python Import Errors (pylablib/numba)
\`\`\`bash
# Install correct numba version
pip install --break-system-packages numba==0.59.1 llvmlite==0.42.0 coverage\<7.4
\`\`\`

---
Generated by: install_all.sh v2.0
EOF
    
    log_success "Installation summary: $summary_file"
}

# ================================================================
# Main Installation Flow
# ================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-camera)
                INSTALL_CAMERA_ARAVIS2=false
                shift
                ;;
            --camera-ws)
                CAMERA_WS="$2"
                shift 2
                ;;
            --skip-groups)
                SKIP_GROUP_CHECK=true
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    print_header
    
    # Check if user wants to proceed
    if [[ "$NON_INTERACTIVE" != "true" ]]; then
        read -p "Proceed with complete installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installation cancelled by user"
            exit 0
        fi
    fi
    
    echo ""
    log_info "Starting complete ProMOC Assembly installation..."
    echo ""
    
    # Run installation steps
    check_prerequisites
    install_colcon
    install_system_deps
    install_python_deps
    
    if [[ "$INSTALL_CAMERA_ARAVIS2" == "true" ]]; then
        install_camera_aravis2
    fi
    
    install_ros2_deps
    build_workspace
    validate_installation
    generate_setup_summary
    
    echo ""
    echo "================================================================"
    log_success "ProMOC Assembly installation completed!"
    echo "================================================================"
    echo ""
    echo "📋 Installation summary: $SCRIPT_DIR/INSTALLATION_SUMMARY.md"
    echo ""
    echo "⚠️  IMPORTANT: Logout and login again for group changes to take effect!"
    echo ""
    echo "🚀 Quick start:"
    echo "   source $WORKSPACE_ROOT/install/setup.bash"
    echo ""
    echo "   # Test LTS300 linear axis"
    echo "   ros2 run linear_axis_nodes lts300_node"
    echo ""
    echo "   # Test camera stack (if installed)"
    echo "   ros2 launch promoc_bringup camera.launch.py driver_mode:=hardware"
    echo ""
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
