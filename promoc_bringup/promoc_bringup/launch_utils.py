"""
Launch helper functions for ProMOC Bringup

Provides reusable helper functions for launch files to reduce
code duplication and improve maintainability.

Usage:
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
    Find Thorlabs APT stepper motor controllers connected via USB.

    Searches `/dev/serial/by-id/` for Thorlabs APT controllers and returns
    a mapping of serial number to stable device path.

    Process:
        1. Scan `/dev/serial/by-id/` for Thorlabs APT controllers
        2. Extract serial number from device name
        3. Return mapping: `{serial_number: device_path}`

    Returns:
        Dictionary mapping serial number to device path.
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
        config_path: Full path to YAML file

    Returns:
        Tuple of (config_dict, error_message).
        `error_message` is None if loading succeeded.

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
    Get full path to config file in 'config/' folder.

    Args:
        package_share_dir: Result of get_package_share_directory()
        config_name: Config filename (e.g., 'mover_node_params.yaml')

    Returns:
        Full path to config file
    """
    return os.path.join(package_share_dir, 'config', config_name)


def get_launch_path(package_share_dir: str, launch_name: str) -> str:
    """
    Get full path to launch file in 'launch/' folder.

    Args:
        package_share_dir: Result of get_package_share_directory()
        launch_name: Launch filename (e.g., 'camera.launch.py')

    Returns:
        Full path to launch file
    """
    return os.path.join(package_share_dir, 'launch', launch_name)


# =============================================================================
# Optical Measurement System Helpers
# =============================================================================

def load_user_config(bringup_share_dir: str) -> dict:
    """
    Load user configuration with fallback to defaults.

    Args:
        bringup_share_dir: Path to promoc_bringup share directory

    Returns:
        Merged configuration dictionary
    """
    user_config_path = get_config_path(bringup_share_dir, 'user_config.yaml')

    defaults = {
        'user': {
            'name': 'default_user',
            'measurement_base_path': os.path.join(os.path.expanduser('~'), 'Dokumente', 'Messungen'),
        },
        'autofocus': {
            'refinement_samples': 51,
            'min_step_mm': 0.010,
            'refinement_shrink_factor': 0.25,
        },
        'autofocus_profiles': {
            'default': {},
            'profiles': {},
        },
        'fly_over': {
            'refinement_mode': 0,
            'refinement_strategy': 'linear',
        },
        'camera': {
            'pixel_size_um': 2.40,
            'mtf_csv_path': '/tmp/mtf_results.csv',
        },
        'mtf': {
            'profile': 'default',
            'debug_export_dir': '',
        },
        'measurement_conditions': {
            'coaxial_light_voltage': 0.0,
            'coaxial_light_current': 0.0,
            'camera_objective': 'unknown',
            'notes': '',
        }
    }

    if os.path.exists(user_config_path):
        try:
            config, error = load_yaml_config(user_config_path)
            if not error:
                for section in defaults:
                    if section in config:
                        defaults[section].update(config[section])
                print(f"✓ Loaded user config: {user_config_path}")
        except Exception as e:
            print(f"⚠ Failed to load user config: {e}")
    else:
        print(f"ℹ No user config at {user_config_path}, using defaults")

    return defaults


def load_camera_config(bringup_share_dir: str) -> dict:
    """
    Load camera configuration from ids_camera_params.yaml.

    Args:
        bringup_share_dir: Path to promoc_bringup share directory

    Returns:
        Camera parameters dictionary
    """
    config_path = get_config_path(bringup_share_dir, 'ids_camera_params.yaml')
    config, error = load_yaml_config(config_path)
    if error:
        print(f"⚠ Camera config error: {error}")
        return {}
    return config.get('camera_params', {})


def load_linear_axis_config(bringup_share_dir: str, axis_name: str) -> dict:
    """
    Load linear axis configuration for a specific axis.

    Args:
        bringup_share_dir: Path to promoc_bringup share directory
        axis_name: Axis name (e.g., 'lts300_x_axis')

    Returns:
        Axis parameters dictionary
    """
    config_path = get_config_path(bringup_share_dir, 'linear_axes_params.yaml')
    config, error = load_yaml_config(config_path)
    if error:
        print(f"⚠ Linear axis config error: {error}")
        return {}
    axis_config = config.get(axis_name, {})
    return axis_config.get('ros__parameters', {})
