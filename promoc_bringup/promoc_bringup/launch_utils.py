"""Launch helper functions for ProMOC bringup."""

from __future__ import annotations

from copy import deepcopy
import glob
import os
import re
from typing import Dict, Optional, Tuple

import yaml


def resolve_runtime_mode(context, logger) -> str:
    """
    Resolve canonical runtime mode.

    Supported value:
    - runtime_mode:=hardware

    Compatibility:
    - runtime_mode:=sim falls back to hardware with a warning
    """
    from launch.substitutions import LaunchConfiguration

    runtime_mode = LaunchConfiguration("runtime_mode").perform(context).strip().lower()
    if runtime_mode == "hardware":
        return runtime_mode

    if runtime_mode == "sim":
        logger.warn(
            "runtime_mode='sim' is no longer supported on the messstand branch; "
            "falling back to 'hardware'."
        )
        return "hardware"

    if runtime_mode:
        logger.warn(
            f"Invalid runtime_mode='{runtime_mode}', falling back to 'hardware'."
        )
    return "hardware"


def discover_thorlabs_devices() -> Dict[str, str]:
    """
    Find connected Thorlabs APT stepper motor controllers by stable USB path.

    Returns mapping: {serial_number: device_path}.
    """
    port_map: Dict[str, str] = {}
    search_pattern = "/dev/serial/by-id/usb-Thorlabs_APT_Stepper_Motor_Controller_*"

    print("Scanning for Thorlabs devices...")
    for device_path in glob.glob(search_pattern):
        try:
            filename = os.path.basename(device_path)
            match = re.search(
                r"usb-Thorlabs_APT_Stepper_Motor_Controller_([0-9]+)",
                filename,
            )
            if not match:
                print(f"  Warning: unrecognized device name format: {filename}")
                continue
            serial = match.group(1)
            port_map[serial] = device_path
            print(f"  Found: {serial} -> {device_path}")
        except Exception as exc:
            print(f"  Error processing {device_path}: {exc}")

    if port_map:
        print(f"Found {len(port_map)} device(s).")
    else:
        print("No devices found.")

    return port_map


def load_yaml_config(config_path: str) -> Tuple[dict, Optional[str]]:
    """Load YAML file and return (config, error)."""
    try:
        with open(config_path, "r", encoding="utf-8") as file_handle:
            config = yaml.safe_load(file_handle)
        return config, None
    except FileNotFoundError:
        return {}, f"File not found: {config_path}"
    except yaml.YAMLError as exc:
        return {}, f"YAML parse error: {exc}"
    except Exception as exc:
        return {}, f"Error loading config: {exc}"


def get_config_path(package_share_dir: str, config_name: str) -> str:
    """Get absolute path to a config file inside package `config/`."""
    return os.path.join(package_share_dir, "config", config_name)


def get_launch_path(package_share_dir: str, launch_name: str) -> str:
    """Get absolute path to a launch file inside package `launch/`."""
    return os.path.join(package_share_dir, "launch", launch_name)


def load_user_config(bringup_share_dir: str) -> dict:
    """
    Load and merge user config with defaults.

    Returns a normalized runtime config used by bringup launch files.
    """
    user_config_path = get_config_path(bringup_share_dir, "user_config.yaml")

    defaults = {
        "measurement": {
            "operator": "default_user",
            "base_path": os.path.join(
                os.path.expanduser("~"), "Dokumente", "Messungen"
            ),
        },
        "runtime": {"mode": "hardware"},
        "autofocus": {
            "refinement_samples": 51,
            "min_step_mm": 0.010,
            "refinement_shrink_factor": 0.25,
        },
        "autofocus_profiles": {"default": {}, "profiles": {}},
        "fly_over": {"refinement_mode": 0, "refinement_strategy": "linear"},
        "camera": {"pixel_size_um": 2.40},
        "mtf": {"profile": "default", "debug_export_dir": ""},
        "measurement_conditions": {
            "coaxial_light_voltage": 0.0,
            "coaxial_light_current": 0.0,
            "camera_objective": "unknown",
            "notes": "",
        },
    }

    if not os.path.exists(user_config_path):
        print(f"Info: no user config at {user_config_path}, using defaults.")
        return defaults

    try:
        config, error = load_yaml_config(user_config_path)
        if error:
            print(f"Warning: failed to load user config: {error}")
            return defaults

        normalized = config or {}
        merged = deepcopy(defaults)
        for section in merged:
            if isinstance(normalized.get(section), dict):
                merged[section].update(normalized[section])

        print(f"Loaded user config: {user_config_path}")
        return merged
    except Exception as exc:
        print(f"Warning: failed to process user config: {exc}")
        return defaults
def load_linear_axis_config(bringup_share_dir: str, axis_name: str) -> dict:
    """Load linear axis configuration for a specific axis."""
    config_path = get_config_path(bringup_share_dir, "linear_axes_params.yaml")
    config, error = load_yaml_config(config_path)
    if error:
        print(f"Warning: linear axis config error: {error}")
        return {}
    axis_config = config.get(axis_name, {})
    return axis_config.get("ros__parameters", {})
