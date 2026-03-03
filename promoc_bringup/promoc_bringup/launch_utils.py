"""Launch helper functions for ProMOC bringup."""

from __future__ import annotations

from copy import deepcopy
import glob
import os
import re
from typing import Dict, Optional, Tuple

import yaml


def _parse_bool_like(value: str) -> bool | None:
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return None


def resolve_runtime_mode(context, logger, legacy_arg_names: tuple[str, ...]) -> str:
    """
    Resolve canonical runtime mode with Release N legacy argument compatibility.

    Canonical argument:
    - runtime_mode:=hardware|sim

    Legacy arguments:
    - e.g. sim_mode, use_simulator
    """
    from launch.substitutions import LaunchConfiguration

    runtime_mode_text = LaunchConfiguration("runtime_mode").perform(context).strip()
    runtime_mode_raw = runtime_mode_text.lower()
    if runtime_mode_raw:
        if runtime_mode_raw not in ("hardware", "sim"):
            logger.warn(
                f"Invalid runtime_mode='{runtime_mode_raw}', falling back to 'hardware'."
            )
            runtime_mode_raw = "hardware"
    else:
        runtime_mode_raw = "hardware"

    legacy_values: list[bool] = []
    for arg_name in legacy_arg_names:
        raw_value = LaunchConfiguration(arg_name).perform(context).strip().lower()
        if not raw_value:
            continue
        parsed = _parse_bool_like(raw_value)
        if parsed is None:
            logger.warn(
                f"Ignoring invalid legacy argument {arg_name}='{raw_value}'. "
                "Use runtime_mode:=hardware|sim."
            )
            continue
        legacy_values.append(parsed)

    if not legacy_values:
        return runtime_mode_raw

    first_legacy = legacy_values[0]
    if any(value != first_legacy for value in legacy_values[1:]):
        logger.warn(
            f"Conflicting legacy arguments {', '.join(legacy_arg_names)} detected. "
            "Using runtime_mode if provided, otherwise hardware."
        )
        return runtime_mode_raw

    if runtime_mode_text:
        logger.warn(
            f"Both runtime_mode and legacy {', '.join(legacy_arg_names)} were provided. "
            "Ignoring legacy arguments and using runtime_mode."
        )
        return runtime_mode_raw

    logger.warn(
        f"Deprecated launch argument(s) {', '.join(legacy_arg_names)} detected. "
        "Use 'runtime_mode:=sim|hardware' instead."
    )
    return "sim" if first_legacy else "hardware"


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


def _normalize_user_config(config: dict) -> dict:
    """
    Normalize v2 and legacy user config schemas.

    Release N compatibility:
    - Accepts canonical keys: `measurement.operator`, `measurement.base_path`, `runtime.mode`.
    - Accepts legacy keys: `user.*`, `camera.mtf_csv_path` with warning output.
    """
    normalized = deepcopy(config or {})

    measurement = normalized.get("measurement")
    if isinstance(measurement, dict):
        normalized.setdefault("user", {})
        if "operator" in measurement:
            normalized["user"]["name"] = measurement["operator"]
        if "base_path" in measurement:
            normalized["user"]["measurement_base_path"] = measurement["base_path"]

    if "user" in normalized:
        print(
            "Warning: legacy key 'user.*' detected. Prefer 'measurement.operator/base_path'."
        )

    camera_cfg = normalized.get("camera")
    if isinstance(camera_cfg, dict) and "mtf_csv_path" in camera_cfg:
        print(
            "Warning: deprecated key 'camera.mtf_csv_path' detected and ignored. "
            "Use 'mtf.debug_export_dir' instead."
        )

    return normalized


def load_user_config(bringup_share_dir: str) -> dict:
    """
    Load and merge user config with defaults.

    Returns a normalized runtime config used by bringup launch files.
    """
    user_config_path = get_config_path(bringup_share_dir, "user_config.yaml")

    defaults = {
        "user": {
            "name": "default_user",
            "measurement_base_path": os.path.join(
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

        normalized = _normalize_user_config(config)
        merged = deepcopy(defaults)
        for section in merged:
            if isinstance(normalized.get(section), dict):
                merged[section].update(normalized[section])

        print(f"Loaded user config: {user_config_path}")
        return merged
    except Exception as exc:
        print(f"Warning: failed to process user config: {exc}")
        return defaults


def load_camera_config(bringup_share_dir: str) -> dict:
    """Load camera configuration from ids_camera_params.yaml."""
    config_path = get_config_path(bringup_share_dir, "ids_camera_params.yaml")
    config, error = load_yaml_config(config_path)
    if error:
        print(f"Warning: camera config error: {error}")
        return {}
    return config.get("camera_params", {})


def load_linear_axis_config(bringup_share_dir: str, axis_name: str) -> dict:
    """Load linear axis configuration for a specific axis."""
    config_path = get_config_path(bringup_share_dir, "linear_axes_params.yaml")
    config, error = load_yaml_config(config_path)
    if error:
        print(f"Warning: linear axis config error: {error}")
        return {}
    axis_config = config.get(axis_name, {})
    return axis_config.get("ros__parameters", {})
