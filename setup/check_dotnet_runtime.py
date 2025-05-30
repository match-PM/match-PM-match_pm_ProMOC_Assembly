#!/usr/bin/env python3
"""
.NET Runtime Detection and Configuration for PMCLib

This script detects available .NET runtimes and configures PMCLib accordingly.
It can be used to troubleshoot .NET/Mono runtime issues with pythonnet.
"""

import sys
import subprocess
import os


def check_dotnet():
    """Check if .NET Core/SDK is available."""
    try:
        result = subprocess.run(['dotnet', '--version'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ .NET Core/SDK found: {version}")
            return True, version
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    print("✗ .NET Core/SDK not available")
    return False, None


def check_mono():
    """Check if Mono runtime is available."""
    try:
        result = subprocess.run(['mono', '--version'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ Mono runtime found: {version_line}")
            return True, version_line
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    print("✗ Mono runtime not available")
    return False, None


def test_pythonnet_runtime(runtime_name):
    """Test pythonnet with specified runtime."""
    print(f"\nTesting pythonnet with {runtime_name}...")

    try:
        from pythonnet import load

        # Try to load the specified runtime
        if runtime_name == "coreclr":
            load("coreclr")
        elif runtime_name == "mono":
            load("mono")
        else:
            print(f"Unknown runtime: {runtime_name}")
            return False

        # Try to import CLR
        import clr
        print(f"✓ pythonnet successfully loaded with {runtime_name}")
        return True

    except Exception as e:
        print(f"✗ pythonnet failed with {runtime_name}: {e}")
        return False


def create_pmclib_config():
    """Create a configuration file for PMCLib runtime selection."""
    config_content = """# PMCLib Runtime Configuration
# This file helps PMCLib choose the appropriate .NET runtime

import sys
import os
from pythonnet import load

def configure_runtime():
    \"\"\"Configure the best available .NET runtime for PMCLib.\"\"\"
    
    # Try .NET Core first (preferred)
    try:
        load("coreclr")
        print("PMCLib using .NET Core runtime")
        return True
    except Exception as e:
        print(f"Failed to load .NET Core: {e}")
    
    # Fallback to Mono
    try:
        load("mono")
        print("PMCLib using Mono runtime")
        return True
    except Exception as e:
        print(f"Failed to load Mono: {e}")
    
    # If both fail, raise an error
    raise RuntimeError("No compatible .NET runtime found. Install .NET SDK or Mono.")

# Auto-configure when imported
if __name__ != "__main__":
    configure_runtime()
"""

    config_path = os.path.join("local_libs", "pmclib_runtime_config.py")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, 'w') as f:
        f.write(config_content)

    print(f"✓ Created runtime configuration: {config_path}")


def main():
    """Main runtime detection and configuration."""
    print("ProMOC Assembly .NET Runtime Detection")
    print("=" * 40)

    # Check available runtimes
    dotnet_available, dotnet_version = check_dotnet()
    mono_available, mono_version = check_mono()

    if not dotnet_available and not mono_available:
        print("\n✗ ERROR: No .NET runtime found!")
        print("Please install either:")
        print("  - .NET SDK: sudo apt-get install dotnet-sdk-8.0")
        print("  - Mono: sudo apt-get install mono-complete")
        sys.exit(1)

    # Test pythonnet with available runtimes
    print("\n" + "=" * 40)
    print("Testing pythonnet compatibility...")

    successful_runtimes = []

    if dotnet_available:
        if test_pythonnet_runtime("coreclr"):
            successful_runtimes.append("coreclr (.NET Core)")

    if mono_available:
        if test_pythonnet_runtime("mono"):
            successful_runtimes.append("mono")

    if not successful_runtimes:
        print("\n✗ ERROR: pythonnet failed with all available runtimes!")
        print("Try reinstalling pythonnet: pip install --force-reinstall pythonnet")
        sys.exit(1)

    print(f"\n✓ pythonnet compatible with: {', '.join(successful_runtimes)}")

    # Create configuration
    create_pmclib_config()

    print("\n" + "=" * 40)
    print("✓ .NET runtime configuration completed!")
    print("\nRecommendations:")
    if "coreclr (.NET Core)" in successful_runtimes:
        print("  - .NET Core is available and preferred")
    if "mono" in successful_runtimes:
        print("  - Mono is available as fallback")

    print("\nNext steps:")
    print("  1. Install PMCLib: pip install local_libs/pmclib-*.whl")
    print("  2. Test PMCLib import: python3 -c 'import pmclib'")


if __name__ == "__main__":
    main()
