#!/bin/bash

# ================================================================
# ProMOC Assembly Python Environment Repair Script
# ================================================================
# 
# This script repairs/recreates the Python virtual environment
# when dependencies are broken or outdated.
#
# Features:
#   - Backup existing venv before deletion
#   - Clean recreation of virtual environment
#   - Reinstall all Python dependencies
#   - Verify installation after repair
#
# Usage:
#   ./repair.sh              Interactive mode
#   ./repair.sh --force      Skip confirmations, delete and recreate
#   ./repair.sh --keep-venv  Only reinstall packages, keep venv
#
# Author: ProMOC Assembly Team
# Version: 1.0
# ================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default venv location
DEFAULT_VENV_PATH="$HOME/ros2_promoc_venv"
VENV_PATH="${PROMOC_VENV:-$DEFAULT_VENV_PATH}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Options
FORCE_MODE=false
KEEP_VENV=false
BACKUP_ENABLED=true

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
    echo "  ProMOC Assembly - Python Environment Repair Tool v1.0"
    echo "================================================================"
    echo ""
    echo "This script will:"
    echo "  • Check current Python environment status"
    echo "  • Optionally backup and delete existing virtual environment"
    echo "  • Create a fresh virtual environment"
    echo "  • Reinstall all Python dependencies"
    echo "  • Verify the installation"
    echo ""
    echo "Current venv path: $VENV_PATH"
    echo ""
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --force          Skip all confirmations, delete and recreate venv"
    echo "  --keep-venv      Only reinstall packages, don't delete venv"
    echo "  --no-backup      Don't create backup before deleting venv"
    echo "  --venv PATH      Use custom venv path (default: ~/ros2_promoc_venv)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  PROMOC_VENV      Custom venv path (alternative to --venv)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Interactive repair"
    echo "  $0 --force            # Force complete recreation"
    echo "  $0 --keep-venv        # Only reinstall packages"
    echo "  $0 --venv /path/venv  # Use custom venv location"
}

# ================================================================
# Parse Arguments
# ================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                FORCE_MODE=true
                shift
                ;;
            --keep-venv)
                KEEP_VENV=true
                shift
                ;;
            --no-backup)
                BACKUP_ENABLED=false
                shift
                ;;
            --venv)
                if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                    VENV_PATH="$2"
                    shift 2
                else
                    log_error "--venv requires a path argument"
                    exit 1
                fi
                ;;
            -h|--help)
                print_header
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
}

# ================================================================
# Environment Status Check
# ================================================================

check_current_status() {
    log_step "Step 1: Checking Current Environment Status"
    
    echo ""
    echo "Virtual Environment:"
    echo "  Path: $VENV_PATH"
    
    if [[ -d "$VENV_PATH" ]]; then
        echo -e "  Status: ${GREEN}EXISTS${NC}"
        
        # Check if venv is functional
        if [[ -f "$VENV_PATH/bin/python" ]]; then
            local venv_python_version=$("$VENV_PATH/bin/python" --version 2>&1 || echo "ERROR")
            echo "  Python: $venv_python_version"
            
            # Check key packages
            echo ""
            echo "Key Packages Status:"
            
            check_package() {
                local pkg=$1
                if "$VENV_PATH/bin/pip" show "$pkg" >/dev/null 2>&1; then
                    local version=$("$VENV_PATH/bin/pip" show "$pkg" 2>/dev/null | grep "^Version:" | cut -d' ' -f2)
                    echo -e "  • $pkg: ${GREEN}$version${NC}"
                    return 0
                else
                    echo -e "  • $pkg: ${RED}NOT INSTALLED${NC}"
                    return 1
                fi
            }
            
            local issues=0
            check_package "pythonnet" || ((issues++))
            check_package "pylablib" || ((issues++))
            check_package "numba" || ((issues++))
            check_package "llvmlite" || ((issues++))
            check_package "numpy" || ((issues++))
            check_package "opencv-python" || ((issues++))
            check_package "pyserial" || ((issues++))
            
            if [[ $issues -gt 0 ]]; then
                echo ""
                log_warning "$issues packages are missing or broken"
                NEEDS_REPAIR=true
            else
                echo ""
                log_success "All key packages appear to be installed"
                NEEDS_REPAIR=false
            fi
        else
            echo -e "  Status: ${RED}BROKEN (no python binary)${NC}"
            NEEDS_REPAIR=true
        fi
        
        # Check venv size
        local venv_size=$(du -sh "$VENV_PATH" 2>/dev/null | cut -f1)
        echo ""
        echo "  Size: $venv_size"
        
    else
        echo -e "  Status: ${YELLOW}DOES NOT EXIST${NC}"
        NEEDS_CREATION=true
    fi
    
    echo ""
}

# ================================================================
# User Confirmation
# ================================================================

confirm_action() {
    if [[ "$FORCE_MODE" == "true" ]]; then
        return 0
    fi
    
    local message="$1"
    local default="${2:-n}"
    
    if [[ "$default" == "y" ]]; then
        read -p "$message [Y/n]: " -n 1 -r
    else
        read -p "$message [y/N]: " -n 1 -r
    fi
    echo
    
    if [[ "$default" == "y" ]]; then
        [[ ! $REPLY =~ ^[Nn]$ ]]
    else
        [[ $REPLY =~ ^[Yy]$ ]]
    fi
}

# ================================================================
# Backup Virtual Environment
# ================================================================

backup_venv() {
    if [[ ! -d "$VENV_PATH" ]]; then
        return 0
    fi
    
    if [[ "$BACKUP_ENABLED" != "true" ]]; then
        log_info "Backup disabled, skipping..."
        return 0
    fi
    
    log_step "Step 2: Backing Up Existing Environment"
    
    local backup_dir="${VENV_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
    
    log_info "Creating backup: $backup_dir"
    
    # Only backup pip freeze output, not entire venv (too large)
    mkdir -p "$backup_dir"
    
    if [[ -f "$VENV_PATH/bin/pip" ]]; then
        "$VENV_PATH/bin/pip" freeze > "$backup_dir/requirements_backup.txt" 2>/dev/null || true
        log_success "Package list backed up to $backup_dir/requirements_backup.txt"
    fi
    
    # Save some metadata
    cat > "$backup_dir/backup_info.txt" << EOF
Backup created: $(date)
Original path: $VENV_PATH
Python version: $("$VENV_PATH/bin/python" --version 2>&1 || echo "unknown")
Reason: ProMOC repair.sh script
EOF
    
    log_success "Backup metadata saved"
}

# ================================================================
# Delete Virtual Environment
# ================================================================

delete_venv() {
    if [[ ! -d "$VENV_PATH" ]]; then
        log_info "No existing venv to delete"
        return 0
    fi
    
    log_step "Step 3: Removing Existing Virtual Environment"
    
    if [[ "$FORCE_MODE" != "true" ]]; then
        log_warning "This will delete: $VENV_PATH"
        if ! confirm_action "Are you sure you want to delete the virtual environment?"; then
            log_info "Deletion cancelled"
            exit 0
        fi
    fi
    
    log_info "Deleting $VENV_PATH..."
    rm -rf "$VENV_PATH"
    log_success "Virtual environment deleted"
}

# ================================================================
# Create Virtual Environment
# ================================================================

create_venv() {
    log_step "Step 4: Creating New Virtual Environment"
    
    if [[ -d "$VENV_PATH" ]]; then
        if [[ "$KEEP_VENV" == "true" ]]; then
            log_info "Keeping existing venv (--keep-venv mode)"
            return 0
        else
            log_warning "Venv already exists at $VENV_PATH"
            return 0
        fi
    fi
    
    log_info "Creating virtual environment at $VENV_PATH..."
    
    # Detect Python version
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Using Python $python_version"
    
    # Create venv
    python3 -m venv "$VENV_PATH"
    
    if [[ ! -f "$VENV_PATH/bin/python" ]]; then
        log_error "Failed to create virtual environment!"
        exit 1
    fi
    
    log_success "Virtual environment created"
    
    # Upgrade pip
    log_info "Upgrading pip..."
    "$VENV_PATH/bin/pip" install --upgrade pip setuptools wheel
    log_success "pip upgraded"
}

# ================================================================
# Install Dependencies
# ================================================================

install_dependencies() {
    log_step "Step 5: Installing Python Dependencies"
    
    # Activate venv for this script's context
    source "$VENV_PATH/bin/activate"
    
    log_info "Installing dependencies (this may take a few minutes)..."
    
    # Core dependencies with pins used on the Humble target and secondary Python 3.12 environments
    local packages=(
        # Core scientific
        "numpy>=1.26.0"
        "scipy"
        "matplotlib"
        
        # Image processing
        "opencv-python>=4.8.0"
        "Pillow"
        
        # Hardware interfaces
        "pyserial"
        "pyusb"
        
        # .NET integration (for PMCLib)
        "pythonnet>=3.0.0"
        
        # Thorlabs LTS300 driver
        "pylablib>=1.4.0"
        
        # CRITICAL: Version pins for pylablib compatibility across supported environments
        # numba 0.59.1 and llvmlite 0.42.0 are required for pylablib
        "numba==0.59.1"
        "llvmlite==0.42.0"
        
        # Coverage tool version pin (avoid 7.x incompatibility)
        "coverage<7.0"
        
        # Utilities
        "pyyaml"
        "tqdm"
    )
    
    local failed_packages=()
    
    for pkg in "${packages[@]}"; do
        echo -n "  Installing $pkg... "
        if pip install "$pkg" >/dev/null 2>&1; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${YELLOW}RETRY${NC}"
            # Retry with verbose output
            if ! pip install "$pkg" 2>&1 | tail -3; then
                echo -e "${RED}FAILED${NC}"
                failed_packages+=("$pkg")
            fi
        fi
    done
    
    # Deactivate venv
    deactivate 2>/dev/null || true
    
    if [[ ${#failed_packages[@]} -gt 0 ]]; then
        log_warning "Some packages failed to install:"
        for pkg in "${failed_packages[@]}"; do
            echo "  • $pkg"
        done
        echo ""
        log_info "You may need to install these manually or check system dependencies"
    else
        log_success "All dependencies installed successfully"
    fi
}

# ================================================================
# Verify Installation
# ================================================================

verify_installation() {
    log_step "Step 6: Verifying Installation"
    
    local python="$VENV_PATH/bin/python"
    local errors=0
    
    echo ""
    echo "Testing Python imports..."
    echo ""
    
    # Test critical imports
    test_import() {
        local module=$1
        local display_name=${2:-$1}
        echo -n "  Testing $display_name... "
        
        if "$python" -c "import $module" 2>/dev/null; then
            echo -e "${GREEN}OK${NC}"
            return 0
        else
            echo -e "${RED}FAILED${NC}"
            return 1
        fi
    }
    
    test_import "numpy" "numpy" || ((errors++))
    test_import "cv2" "opencv" || ((errors++))
    test_import "serial" "pyserial" || ((errors++))
    test_import "clr" "pythonnet" || ((errors++))
    test_import "pylablib" "pylablib" || ((errors++))
    test_import "numba" "numba" || ((errors++))
    
    echo ""
    
    if [[ $errors -gt 0 ]]; then
        log_warning "$errors import tests failed"
        log_info "Some modules may require additional system dependencies"
        return 1
    else
        log_success "All import tests passed!"
        return 0
    fi
}

# ================================================================
# Print Completion Message
# ================================================================

print_completion() {
    echo ""
    echo "================================================================"
    echo -e "${GREEN}  Repair Complete!${NC}"
    echo "================================================================"
    echo ""
    echo "To use the repaired environment:"
    echo ""
    echo -e "  ${CYAN}source $VENV_PATH/bin/activate${NC}"
    echo ""
    echo "Add to your ~/.bashrc for automatic activation:"
    echo ""
    echo "  echo 'source $VENV_PATH/bin/activate' >> ~/.bashrc"
    echo ""
    echo "Then build the ROS2 workspace:"
    echo ""
    echo "  cd $PROJECT_ROOT/.."
    echo "  colcon build --symlink-install"
    echo ""
}

# ================================================================
# Quick Reinstall (--keep-venv mode)
# ================================================================

quick_reinstall() {
    log_step "Quick Reinstall Mode (--keep-venv)"
    
    if [[ ! -d "$VENV_PATH" ]]; then
        log_error "Virtual environment not found at $VENV_PATH"
        log_info "Run without --keep-venv to create a new environment"
        exit 1
    fi
    
    log_info "Reinstalling packages in existing venv..."
    
    # Upgrade pip first
    "$VENV_PATH/bin/pip" install --upgrade pip setuptools wheel
    
    # Force reinstall key packages
    "$VENV_PATH/bin/pip" install --force-reinstall \
        "numba==0.59.1" \
        "llvmlite==0.42.0" \
        "pylablib>=1.4.0" \
        "pythonnet>=3.0.0"
    
    log_success "Key packages reinstalled"
}

# ================================================================
# Main Function
# ================================================================

main() {
    parse_arguments "$@"
    print_header
    
    # Check current status
    check_current_status
    
    # Handle different modes
    if [[ "$KEEP_VENV" == "true" ]]; then
        quick_reinstall
    else
        # Ask for confirmation in interactive mode
        if [[ "$FORCE_MODE" != "true" && -d "$VENV_PATH" ]]; then
            echo "Options:"
            echo "  1) Full repair (delete and recreate venv)"
            echo "  2) Quick reinstall (keep venv, reinstall packages)"
            echo "  3) Cancel"
            echo ""
            read -p "Choose option (1/2/3): " -n 1 -r
            echo
            
            case $REPLY in
                1)
                    backup_venv
                    delete_venv
                    create_venv
                    install_dependencies
                    ;;
                2)
                    quick_reinstall
                    ;;
                3|*)
                    log_info "Repair cancelled"
                    exit 0
                    ;;
            esac
        else
            # Force mode or no existing venv
            if [[ -d "$VENV_PATH" ]]; then
                backup_venv
                delete_venv
            fi
            create_venv
            install_dependencies
        fi
    fi
    
    # Verify
    verify_installation
    
    # Done
    print_completion
}

# Run main
main "$@"
