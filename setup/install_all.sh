#!/bin/bash

# ProMOC Assembly Master Installation Script
# This script orchestrates the complete installation of all dependencies and setup
# Author: ProMOC Assembly Team
# Version: 1.0

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

print_header() {
    echo ""
    echo "================================================================"
    echo "  ProMOC Assembly System - Complete Installation Script"
    echo "================================================================"
    echo ""
    echo "This script will install:"
    echo "• System dependencies (.NET SDK, Mono, build tools)"
    echo "• Python dependencies (pythonnet, pylablib, etc.)"
    echo "• ROS2 dependencies via rosdep"
    echo "• Validate the complete installation"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running on Ubuntu
    if [[ ! -f /etc/os-release ]]; then
        log_error "This script is designed for Ubuntu systems"
        exit 1
    fi
    
    source /etc/os-release
    log_info "Detected OS: $PRETTY_NAME"
    
    # Check if ROS2 is installed
    if ! command -v ros2 &> /dev/null; then
        log_error "ROS2 not found! Please install ROS2 first:"
        echo "  https://docs.ros.org/en/humble/Installation.html"
        exit 1
    fi
    
    local ros_distro=$(printenv ROS_DISTRO)
    if [[ -z "$ros_distro" ]]; then
        log_error "ROS_DISTRO not set! Source your ROS2 setup:"
        echo "  source /opt/ros/humble/setup.bash"
        exit 1
    fi
    
    log_success "ROS2 $ros_distro detected"
    
    # Check if we're in the correct directory
    if [[ ! -f "$SCRIPT_DIR/dependencies.txt" ]]; then
        log_error "dependencies.txt not found! Run this script from the setup/ directory"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    if [[ -x "$SCRIPT_DIR/install_system_deps.sh" ]]; then
        bash "$SCRIPT_DIR/install_system_deps.sh"
        log_success "System dependencies installed"
    else
        log_error "install_system_deps.sh not found or not executable"
        exit 1
    fi
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    if [[ -x "$SCRIPT_DIR/install_python_deps.sh" ]]; then
        bash "$SCRIPT_DIR/install_python_deps.sh"
        log_success "Python dependencies installed"
    else
        log_error "install_python_deps.sh not found or not executable"
        exit 1
    fi
}

# Install ROS2 dependencies
install_ros2_deps() {
    log_info "Installing ROS2 dependencies with rosdep..."
    
    cd "$PROJECT_ROOT"
    
    # Initialize rosdep if not already done
    if ! rosdep --version &> /dev/null; then
        log_info "Initializing rosdep..."
        sudo rosdep init || true  # Don't fail if already initialized
        rosdep update
    else
        log_info "Updating rosdep..."
        rosdep update
    fi
    
    # Install dependencies for all packages
    log_info "Installing ROS2 package dependencies..."
    rosdep install --from-paths . --ignore-src -y --rosdistro $ROS_DISTRO
    
    log_success "ROS2 dependencies installed"
}

# Build the workspace
build_workspace() {
    log_info "Building ROS2 workspace..."
    
    cd "$PROJECT_ROOT"
    
    # Clean previous build (optional)
    if [[ -d "build" ]] || [[ -d "install" ]] || [[ -d "log" ]]; then
        read -p "Remove previous build artifacts? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf build install log
            log_info "Previous build artifacts removed"
        fi
    fi
    
    # Build all packages
    log_info "Building with colcon..."
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
    
    log_success "Workspace built successfully"
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."
    
    if [[ -x "$SCRIPT_DIR/validate_setup.sh" ]]; then
        bash "$SCRIPT_DIR/validate_setup.sh"
    else
        log_warning "validate_setup.sh not found, skipping validation"
    fi
}

# Create local_libs directory for PMCLib
setup_pmclib_directory() {
    log_info "Setting up PMCLib directory structure..."
    
    local local_libs_dir="$PROJECT_ROOT/local_libs"
    
    if [[ ! -d "$local_libs_dir" ]]; then
        mkdir -p "$local_libs_dir"
        log_info "Created local_libs directory: $local_libs_dir"
    fi
    
    # Create a README for the local_libs directory
    cat > "$local_libs_dir/README.md" << 'EOF'
# Local Libraries Directory

This directory contains proprietary libraries that are not publicly available.

## PMCLib Installation

1. Obtain the PMCLib wheel file from Match/IEMCA:
   ```
   pmclib-X.X.X-py3-none-any.whl
   ```

2. Copy it to this directory:
   ```bash
   cp /path/to/pmclib-*.whl local_libs/
   ```

3. Install it in your Python environment:
   ```bash
   pip install local_libs/pmclib-*.whl
   ```

## Note

- This directory is included in .gitignore to prevent accidental commits
- The PMCLib is proprietary and should not be shared publicly
- For development without hardware, the mock_pmclib.py will be used automatically
EOF
    
    log_success "PMCLib directory structure created"
}

# Generate setup summary
generate_setup_summary() {
    local summary_file="$SCRIPT_DIR/INSTALLATION_SUMMARY.md"
    
    log_info "Generating installation summary..."
    
    cat > "$summary_file" << EOF
# ProMOC Assembly Installation Summary

**Installation Date:** $(date)
**System:** $(lsb_release -d | cut -f2)
**ROS2 Distro:** $ROS_DISTRO

## Installation Status

### ✅ System Dependencies
- .NET SDK 8.0: $(command -v dotnet &> /dev/null && echo "✓ Installed" || echo "✗ Not available")
- Mono Runtime: $(command -v mono &> /dev/null && echo "✓ Installed" || echo "✗ Not available") 
- Build Tools: ✓ Installed
- Python Dev Headers: ✓ Installed

### ✅ Python Dependencies
- pythonnet: $(pip show pythonnet &> /dev/null && echo "✓ Installed" || echo "⚠ Check required")
- pylablib: $(pip show pylablib &> /dev/null && echo "✓ Installed" || echo "⚠ Check required")
- pyserial: $(pip show pyserial &> /dev/null && echo "✓ Installed" || echo "⚠ Check required")

### ✅ ROS2 Dependencies
- Workspace built: $(test -d "$PROJECT_ROOT/install" && echo "✓ Yes" || echo "✗ No")
- rosdep updated: ✓ Yes

## Next Steps

1. **Source the workspace:**
   \`\`\`bash
   source $PROJECT_ROOT/install/setup.bash
   \`\`\`

2. **For PMCLib (if available):**
   \`\`\`bash
   # Copy wheel file to local_libs/
   cp /path/to/pmclib-*.whl $PROJECT_ROOT/local_libs/
   
   # Install PMCLib
   pip install $PROJECT_ROOT/local_libs/pmclib-*.whl
   \`\`\`

3. **Test the installation:**
   \`\`\`bash
   cd $SCRIPT_DIR
   python3 test_basic_functionality.py
   \`\`\`

4. **Run simulation:**
   \`\`\`bash
   ros2 launch promoc_bringup dual_lts300_gazebo.launch.py
   \`\`\`

## Troubleshooting

- For .NET issues: Run \`$SCRIPT_DIR/check_dotnet_runtime.py\`
- For validation: Run \`$SCRIPT_DIR/validate_setup.sh\`
- For detailed logs: Check colcon build output

## Project Structure

\`\`\`
$PROJECT_ROOT/
├── linear_axis_nodes/          # Thorlabs LTS300 control
├── planar_motor_nodes/         # Planar motor with PMCLib
├── promoc_assembly_interfaces/ # Custom ROS2 messages/services
├── promoc_bringup/            # Launch files and configurations
├── setup/                     # Installation and validation scripts
└── local_libs/               # Proprietary libraries (PMCLib)
\`\`\`

Generated by: ProMOC Assembly Master Installer
EOF
    
    log_success "Installation summary generated: $summary_file"
}

# Main installation flow
main() {
    print_header
    
    # Check if user wants to proceed
    read -p "Do you want to proceed with the complete installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled by user"
        exit 0
    fi
    
    # Step-by-step installation
    echo ""
    log_info "Starting complete ProMOC Assembly installation..."
    echo ""
    
    check_prerequisites
    setup_pmclib_directory
    install_system_deps
    install_python_deps
    install_ros2_deps
    build_workspace
    validate_installation
    generate_setup_summary
    
    echo ""
    echo "================================================================"
    log_success "ProMOC Assembly installation completed successfully!"
    echo "================================================================"
    echo ""
    echo "📋 Installation summary: $SCRIPT_DIR/INSTALLATION_SUMMARY.md"
    echo ""
    echo "🚀 Quick start:"
    echo "   source $PROJECT_ROOT/install/setup.bash"
    echo "   ros2 launch promoc_bringup dual_lts300_gazebo.launch.py"
    echo ""
    echo "📝 For detailed next steps, see the installation summary above."
    echo ""
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
