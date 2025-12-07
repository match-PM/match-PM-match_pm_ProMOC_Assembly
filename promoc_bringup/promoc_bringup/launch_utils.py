"""
Launch Utilities for ProMOC Bringup
===================================

This module provides helper functions for launch files to reduce
code duplication and improve maintainability.

Usage in launch files:
    from promoc_bringup.launch_utils import (
        discover_thorlabs_devices,
        load_yaml_config,
        create_node_with_params
    )
"""

import os
import re
import glob
import yaml
from typing import Dict, Optional, Tuple


def discover_thorlabs_devices() -> Dict[str, str]:
    """
    Discover Thorlabs APT stepper motor controllers connected via USB.

    Scans /dev/serial/by-id/ for Thorlabs devices and returns a mapping
    of serial numbers to stable device paths.

    How it works:
        1. Scan /dev/serial/by-id/ for Thorlabs APT controllers
        2. Extract serial number from device path
        3. Return mapping: {serial_number: device_path}

    Returns:
        Dictionary mapping serial numbers to device paths.
        Empty dict if no devices found.

    Example:
        >>> devices = discover_thorlabs_devices()
        >>> print(devices)
        {'45407924': '/dev/serial/by-id/usb-Thorlabs_APT_...'}
    """
    port_map = {}
    search_pattern = '/dev/serial/by-id/usb-Thorlabs_APT_Stepper_Motor_Controller_*'

    print("🛰️  Scanning for Thorlabs devices...")

    for device_path in glob.glob(search_pattern):
        try:
            filename = os.path.basename(device_path)
            match = re.search(
                r'usb-Thorlabs_APT_Stepper_Motor_Controller_([0-9]+)',
                filename
            )

            if match:
                serial = match.group(1)
                port_map[serial] = device_path
                print(f"  ✅ Found: {serial} → {device_path}")
            else:
                print(f"  ⚠️ Unrecognized format: {filename}")

        except Exception as e:
            print(f"  ❌ Error processing {device_path}: {e}")

    if port_map:
        print(f"  → Found {len(port_map)} device(s)")
    else:
        print("  → No devices found")

    return port_map


def load_yaml_config(config_path: str) -> Tuple[dict, Optional[str]]:
    """
    Load a YAML configuration file.

    Args:
        config_path: Full path to the YAML file

    Returns:
        Tuple of (config_dict, error_message)
        error_message is None if successful

    Example:
        >>> config, error = load_yaml_config('/path/to/config.yaml')
        >>> if error:
        ...     print(f"Failed: {error}")
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config, None
    except FileNotFoundError:
        return {}, f"File not found: {config_path}"
    except yaml.YAMLError as e:
        return {}, f"YAML parse error: {e}"
    except Exception as e:
        return {}, f"Error loading config: {e}"


def get_config_path(package_share_dir: str, config_name: str) -> str:
    """
    Get full path to a config file in the package's config directory.

    Args:
        package_share_dir: Result of get_package_share_directory()
        config_name: Name of the config file (e.g., 'mover_node_params.yaml')

    Returns:
        Full path to the config file
    """
    return os.path.join(package_share_dir, 'config', config_name)


def get_launch_path(package_share_dir: str, launch_name: str) -> str:
    """
    Get full path to a launch file in the package's launch directory.

    Args:
        package_share_dir: Result of get_package_share_directory()
        launch_name: Name of the launch file (e.g., 'camera.launch.py')

    Returns:
        Full path to the launch file
    """
    return os.path.join(package_share_dir, 'launch', launch_name)
