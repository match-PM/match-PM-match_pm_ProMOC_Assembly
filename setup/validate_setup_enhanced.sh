#!/bin/bash

# ProMOC Assembly System Validation Script
# Enhanced version with comprehensive system checks
# Author: ProMOC Assembly Team

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

log_fail() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((WARNING_CHECKS++))
}

check_item() {
    ((TOTAL_CHECKS++))
}

print_header() {
    echo ""
    echo "================================================================"
    echo "  ProMOC Assembly System Validation"
    echo "================================================================"
    echo ""
}

# Check ROS2 environment
check_ros2_environment() {
    log_info "Checking ROS2 environment..."
    
    check_item
    if [[ -n "$ROS_DISTRO" ]]; then
        log_success "ROS_DISTRO set to: $ROS_DISTRO"
    else
        log_fail "ROS_DISTRO not set - source ROS2 setup"
        return
    fi
    
    check_item
    if command -v ros2 &> /dev/null; then
        log_success "ros2 command available"
    else
        log_fail "ros2 command not found"
        return
    fi
    
    check_item
    if command -v colcon &> /dev/null; then
        log_success "colcon build tool available"
    else
        log_fail "colcon build tool not found"
    fi
    
    check_item
    if command -v rosdep &> /dev/null; then
        log_success "rosdep dependency manager available"
    else
        log_warning "rosdep not found - may need manual dependency management"
    fi
}

# Check system dependencies
check_system_dependencies() {
    log_info "Checking system dependencies..."
    
    # .NET Runtime
    check_item
    if command -v dotnet &> /dev/null; then
        local dotnet_version=$(dotnet --version 2>/dev/null || echo "unknown")
        log_success ".NET SDK available (version: $dotnet_version)"
    else
        log_warning ".NET SDK not available - checking Mono..."
        
        check_item
        if command -v mono &> /dev/null; then
            local mono_version=$(mono --version | head -1 | awk '{print $5}')
            log_success "Mono runtime available (version: $mono_version)"
        else
            log_fail "Neither .NET nor Mono runtime available - PMCLib will not work"
        fi
    fi
    
    # Build tools
    check_item
    if command -v gcc &> /dev/null; then
        log_success "GCC compiler available"
    else
        log_fail "GCC compiler not found"
    fi
    
    check_item
    if command -v pkg-config &> /dev/null; then
        log_success "pkg-config available"
    else
        log_fail "pkg-config not found"
    fi
    
    # Python development
    check_item
    if python3-config --includes &> /dev/null; then
        log_success "Python development headers available"
    else
        log_fail "Python development headers not found"
    fi
}

# Check Python dependencies
check_python_dependencies() {
    log_info "Checking Python dependencies..."
    
    # Core dependencies
    local core_deps=("numpy" "wheel" "setuptools")
    for dep in "${core_deps[@]}"; do
        check_item
        if python3 -c "import $dep" &> /dev/null; then
            local version=$(python3 -c "import $dep; print($dep.__version__)" 2>/dev/null || echo "unknown")
            log_success "$dep available (version: $version)"
        else
            log_fail "$dep not available"
        fi
    done
    
    # Hardware dependencies
    check_item
    if python3 -c "import pythonnet" &> /dev/null; then
        local version=$(python3 -c "import pythonnet; print(pythonnet.__version__)" 2>/dev/null || echo "unknown")
        log_success "pythonnet available (version: $version)"
    else
        log_warning "pythonnet not available - PMCLib integration will not work"
    fi
    
    check_item
    if python3 -c "import pylablib" &> /dev/null; then
        local version=$(python3 -c "import pylablib; print(pylablib.__version__)" 2>/dev/null || echo "unknown")
        log_success "pylablib available (version: $version)"
    else
        log_warning "pylablib not available - Thorlabs hardware control will not work"
    fi
    
    check_item
    if python3 -c "import serial" &> /dev/null; then
        local version=$(python3 -c "import serial; print(serial.__version__)" 2>/dev/null || echo "unknown")
        log_success "pyserial available (version: $version)"
    else
        log_warning "pyserial not available - serial communication will not work"
    fi
    
    # ROS2 Python
    check_item
    if python3 -c "import rclpy" &> /dev/null; then
        log_success "rclpy (ROS2 Python) available"
    else
        log_fail "rclpy not available - ROS2 Python nodes will not work"
    fi
}

# Check workspace build
check_workspace_build() {
    log_info "Checking workspace build..."
    
    cd "$PROJECT_ROOT"
    
    check_item
    if [[ -d "install" ]]; then
        log_success "Workspace has been built (install/ directory exists)"
    else
        log_fail "Workspace not built - run 'colcon build'"
        return
    fi
    
    # Check if setup files exist
    check_item
    if [[ -f "install/setup.bash" ]]; then
        log_success "Setup script available (install/setup.bash)"
    else
        log_fail "Setup script not found"
    fi
    
    # Check individual packages
    local packages=("linear_axis_nodes" "planar_motor_nodes" "promoc_assembly_interfaces" "promoc_bringup")
    for pkg in "${packages[@]}"; do
        check_item
        if [[ -d "install/$pkg" ]]; then
            log_success "Package $pkg built successfully"
        else
            log_warning "Package $pkg not found in install directory"
        fi
    done
}

# Check PMCLib
check_pmclib() {
    log_info "Checking PMCLib availability..."
    
    check_item
    if python3 -c "import pmclib" &> /dev/null; then
        local version=$(python3 -c "import pmclib; print(pmclib.__version__)" 2>/dev/null || echo "unknown")
        log_success "PMCLib available (version: $version)"
    else
        log_warning "PMCLib not available - using mock implementation for development"
    fi
    
    # Check local PMCLib checkout (current + legacy locations)
    check_item
    if [[ -d "$PROJECT_ROOT/planar_motor_nodes/planar_motor_nodes/drivers/pmclib" ]]; then
        log_success "PMCLib local checkout found in planar_motor_nodes/.../drivers/pmclib"
    elif [[ -d "$PROJECT_ROOT/local_libs/pmclib" ]]; then
        log_warning "Legacy PMCLib location found in local_libs/pmclib (supported, but deprecated)"
    else
        log_warning "No local PMCLib checkout found (optional if pmclib is installed via pip wheel)"
    fi
}

# Test basic functionality
test_basic_functionality() {
    log_info "Testing basic functionality..."
    
    # Source workspace if built
    if [[ -f "$PROJECT_ROOT/install/setup.bash" ]]; then
        source "$PROJECT_ROOT/install/setup.bash"
    fi
    
    # Test package imports
    check_item
    if python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/linear_axis_nodes')
from linear_axis_nodes.drivers.linear_axis_driver import LinearAxisDriver
print('LinearAxisDriver import successful')
" &> /dev/null; then
        log_success "Linear axis driver imports correctly"
    else
        log_warning "Linear axis driver import failed"
    fi
    
    check_item
    if python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/planar_motor_nodes')
from planar_motor_nodes.drivers.mock_pmclib import MockPMCLib
print('MockPMCLib import successful')
" &> /dev/null; then
        log_success "Mock PMCLib imports correctly"
    else
        log_warning "Mock PMCLib import failed"
    fi
    
    # Test ROS2 interface generation
    check_item
    if ros2 interface list | grep -q "promoc_assembly_interfaces" 2>/dev/null; then
        log_success "Custom ROS2 interfaces are available"
    else
        log_warning "Custom ROS2 interfaces not found - rebuild workspace"
    fi
}

# Generate validation report
generate_report() {
    local report_file="$SCRIPT_DIR/VALIDATION_REPORT.md"
    
    log_info "Generating validation report..."
    
    cat > "$report_file" << EOF
# ProMOC Assembly Validation Report

**Validation Date:** $(date)
**System:** $(lsb_release -d | cut -f2 2>/dev/null || echo "Unknown")
**ROS2 Distro:** ${ROS_DISTRO:-"Not set"}
**Workspace:** $PROJECT_ROOT

## Summary

- **Total Checks:** $TOTAL_CHECKS
- **Passed:** $PASSED_CHECKS ✓
- **Failed:** $FAILED_CHECKS ✗
- **Warnings:** $WARNING_CHECKS ⚠

$(if [[ $FAILED_CHECKS -eq 0 ]]; then
    echo "**Status:** 🟢 READY FOR OPERATION"
elif [[ $FAILED_CHECKS -le 3 ]]; then
    echo "**Status:** 🟡 READY WITH WARNINGS"
else
    echo "**Status:** 🔴 NOT READY - CRITICAL ISSUES"
fi)

## Environment Status

### ROS2 Environment
- ROS_DISTRO: ${ROS_DISTRO:-"❌ Not set"}
- ros2 command: $(command -v ros2 &> /dev/null && echo "✅ Available" || echo "❌ Missing")
- colcon: $(command -v colcon &> /dev/null && echo "✅ Available" || echo "❌ Missing")
- rosdep: $(command -v rosdep &> /dev/null && echo "✅ Available" || echo "⚠️ Missing")

### System Dependencies
- .NET SDK: $(command -v dotnet &> /dev/null && echo "✅ $(dotnet --version 2>/dev/null)" || echo "❌ Missing")
- Mono: $(command -v mono &> /dev/null && echo "✅ Available" || echo "❌ Missing")
- GCC: $(command -v gcc &> /dev/null && echo "✅ Available" || echo "❌ Missing")
- Python Dev: $(python3-config --includes &> /dev/null && echo "✅ Available" || echo "❌ Missing")

### Python Dependencies
- pythonnet: $(python3 -c "import pythonnet; print('✅', pythonnet.__version__)" 2>/dev/null || echo "❌ Missing")
- pylablib: $(python3 -c "import pylablib; print('✅', pylablib.__version__)" 2>/dev/null || echo "❌ Missing")
- pyserial: $(python3 -c "import serial; print('✅', serial.__version__)" 2>/dev/null || echo "❌ Missing")
- rclpy: $(python3 -c "import rclpy; print('✅ Available')" 2>/dev/null || echo "❌ Missing")

### Workspace Build
- Built: $(test -d "$PROJECT_ROOT/install" && echo "✅ Yes" || echo "❌ No")
- Setup script: $(test -f "$PROJECT_ROOT/install/setup.bash" && echo "✅ Available" || echo "❌ Missing")

### PMCLib Status
- PMCLib: $(python3 -c "import pmclib; print('✅ Available')" 2>/dev/null || echo "⚠️ Using mock")
- Local checkout: $(test -d "$PROJECT_ROOT/planar_motor_nodes/planar_motor_nodes/drivers/pmclib" && echo "✅ Found (drivers/pmclib)" || test -d "$PROJECT_ROOT/local_libs/pmclib" && echo "⚠️ Found (legacy local_libs/pmclib)" || echo "❌ Not found")

## Recommendations

$(if [[ $FAILED_CHECKS -gt 0 ]]; then
cat << 'FIXES'
### Critical Issues to Fix:
1. Install missing dependencies: `./install_all.sh`
2. Source ROS2 environment: `source /opt/ros/$ROS_DISTRO/setup.bash`
3. Build workspace: `colcon build --symlink-install`
4. Install Python dependencies: `pip install -r dependencies.txt`

FIXES
fi)

$(if [[ $WARNING_CHECKS -gt 0 ]]; then
cat << 'WARNINGS'
### Warnings to Address:
1. For PMCLib: install wheel (`pip install /path/to/pmclib-*.whl`) or add local checkout to planar_motor_nodes/.../drivers/pmclib
2. For hardware: Install pylablib and pythonnet
3. Update system packages: `sudo apt update && sudo apt upgrade`

WARNINGS
fi)

### Quick Test Commands:
\`\`\`bash
# Source workspace
source $PROJECT_ROOT/install/setup.bash

# Test simulation
ros2 launch promoc_bringup system.launch.py runtime_mode:=sim

# Test basic functionality
python3 $SCRIPT_DIR/test_basic_functionality.py
\`\`\`

---
Generated by: ProMOC Assembly Validation Script
EOF
    
    log_success "Validation report generated: $report_file"
}

# Print summary
print_summary() {
    echo ""
    echo "================================================================"
    echo "  Validation Summary"
    echo "================================================================"
    echo ""
    echo "Total checks: $TOTAL_CHECKS"
    echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
    echo -e "Warnings: ${YELLOW}$WARNING_CHECKS${NC}"
    echo ""
    
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}🟢 System ready for operation!${NC}"
    elif [[ $FAILED_CHECKS -le 3 ]]; then
        echo -e "${YELLOW}🟡 System ready with warnings${NC}"
        echo "  Address warnings for optimal performance"
    else
        echo -e "${RED}🔴 System has critical issues${NC}"
        echo "  Run ./install_all.sh to fix dependencies"
    fi
    
    echo ""
    echo "📋 Detailed report: $SCRIPT_DIR/VALIDATION_REPORT.md"
}

# Main validation flow
main() {
    print_header
    
    check_ros2_environment
    check_system_dependencies  
    check_python_dependencies
    check_workspace_build
    check_pmclib
    test_basic_functionality
    generate_report
    print_summary
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
