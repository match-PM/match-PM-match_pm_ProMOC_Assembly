# ProMOC Assembly Setup Scripts

This directory contains all installation and validation scripts for the ProMOC Assembly system.

## Files Overview

- **`install_system_deps.sh`** - Installs system dependencies (.NET SDK, Mono, build tools)
- **`install_python_deps.sh`** - Installs Python dependencies with PEP 668 compatibility
- **`check_dotnet_runtime.py`** - Tests .NET runtime compatibility and configuration
- **`validate_setup.sh`** - Comprehensive system validation script
- **`test_basic_functionality.py`** - Basic functionality tests for development
- **`dependencies.txt`** - Python package requirements
- **`QUICKSTART.md`** - Quick installation guide for experienced users
- **`SETUP_SUMMARY.md`** - Detailed project overview and architecture
- **`VALIDATION_REPORT.md`** - Testing results and system status

## Usage

1. **Run from the setup directory:**
   ```bash
   cd setup/
   ```

2. **Install system dependencies:**
   ```bash
   ./install_system_deps.sh
   ```

3. **Install Python dependencies:**
   ```bash
   ./install_python_deps.sh
   ```

4. **Validate installation:**
   ```bash
   ./validate_setup.sh
   ```

## Note

All scripts are designed to be run from within the `setup/` directory and will correctly reference files in the parent directory structure.
