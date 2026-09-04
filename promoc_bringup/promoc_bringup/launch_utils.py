"""Launch helper functions for ProMOC bringup."""

from __future__ import annotations

from copy import deepcopy
import glob
import os
import re
import tempfile
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
            "analysis_roi_x_px": -1,
            "analysis_roi_y_px": -1,
            "analysis_roi_width_px": 2048,
            "analysis_roi_height_px": 2048,
            "analysis_downsample_max_dim_px": 2048,
            "analysis_use_center_roi": True,
        },
        "autofocus_profiles": {"default": {}, "profiles": {}},
        "fly_over": {"refinement_mode": 0, "refinement_strategy": "linear"},
        "auto_exposure": {
            "target_level_fraction": 0.75,
            "tolerance_fraction": 0.02,
            "percentile": 95.0,
            "max_saturated_fraction": 0.001,
            "saturation_threshold_fraction": 0.98,
            "frames_per_iteration": 3,
            "max_iterations": 10,
            "stable_iterations": 2,
            "settle_frames_after_set": 2,
        },
        "camera": {
            "profile": "ids_u3_3800cp_m_gl_r22",
            "pixel_size_um": None,
        },
        # Kept as a free-form section so every calibrated tilt parameter from
        # the local user_config reaches the action node unchanged.
        "target_tilt": {},
        "mtf": {
            "profile": "default",
            "debug_export_dir": "",
            "use_raw_capture": True,
            "capture_required_raw": True,
            # 0 keeps the current live exposure during an MTF capture.
            "capture_exposure_us": 0.0,
            "min_edge_angle": 2.0,
            "max_edge_angle": 11.0,
            "capture_only_context_margin_px": 64,
        },
        "measurement_conditions": {
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
        legacy_user = normalized.get("user", {}) if isinstance(normalized.get("user"), dict) else {}
        measurement_cfg = normalized.setdefault("measurement", {})
        if not measurement_cfg.get("operator"):
            legacy_name = str(legacy_user.get("name", "")).strip()
            if legacy_name:
                measurement_cfg["operator"] = legacy_name
        if not measurement_cfg.get("base_path"):
            legacy_base_path = str(legacy_user.get("measurement_base_path", "")).strip()
            if legacy_base_path:
                measurement_cfg["base_path"] = legacy_base_path

        merged = deepcopy(defaults)
        for section in merged:
            if isinstance(normalized.get(section), dict):
                merged[section].update(normalized[section])

        print(f"Loaded user config: {user_config_path}")
        return merged
    except Exception as exc:
        print(f"Warning: failed to process user config: {exc}")
        return defaults


def load_target_tilt_config(bringup_share_dir: str, user_config: dict):
    """Resolve internal-default < imaging-profile < user-config precedence."""
    user_values = dict(user_config.get("target_tilt", {}) or {})
    profile_name = str(user_values.pop("imaging_profile", "")).strip()
    profile_values = {}
    error = None
    if profile_name:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", profile_name):
            error = f"invalid target_tilt.imaging_profile '{profile_name}'"
        else:
            path = get_config_path(
                bringup_share_dir,
                os.path.join("imaging_profiles", f"{profile_name}.yaml"),
            )
            profile, error = load_yaml_config(path)
            if not error:
                profile_values.update(profile.get("target_tilt", {}) or {})
                metadata = profile.get("imaging_profile", {}) or {}
                for name in ("object_um_per_pixel", "magnification"):
                    if name in metadata and name not in profile_values:
                        profile_values[name] = metadata[name]
    resolved = dict(profile_values)
    resolved.update(user_values)
    return resolved, profile_name, error


def load_linear_axis_config(bringup_share_dir: str, axis_name: str) -> dict:
    """Load linear axis configuration for a specific axis."""
    config_path = get_config_path(bringup_share_dir, "linear_axes_params.yaml")
    config, error = load_yaml_config(config_path)
    if error:
        print(f"Warning: linear axis config error: {error}")
        return {}
    axis_config = config.get(axis_name, {})
    return axis_config.get("ros__parameters", {})


def build_camera_info_payload(
    camera_info: dict,
    frame_id: str = "camera_frame",
    stream_name: str = "stream0",
) -> dict:
    """Build a camera_info_manager-compatible calibration payload."""
    payload = deepcopy(camera_info or {})
    payload["image_width"] = int(payload.get("image_width", 0) or 0)
    payload["image_height"] = int(payload.get("image_height", 0) or 0)
    payload["camera_name"] = f"{frame_id}_{stream_name}"
    return payload


def materialize_camera_info_yaml(
    camera_info: dict,
    frame_id: str = "camera_frame",
    stream_name: str = "stream0",
    target_path: str | None = None,
) -> str:
    """Write the runtime camera-info YAML and return its path."""
    payload = build_camera_info_payload(
        camera_info,
        frame_id=frame_id,
        stream_name=stream_name,
    )
    if target_path is None:
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", payload["camera_name"])
        target_path = os.path.join(
            tempfile.gettempdir(),
            f"{safe_name}_camera_info.yaml",
        )

    with open(target_path, "w", encoding="utf-8") as file_handle:
        yaml.safe_dump(payload, file_handle, sort_keys=False)
    return target_path


def materialize_dynamic_parameters_yaml(
    dynamic_parameters: list[dict] | None,
    camera_name: str = "promoc_camera",
    target_path: str | None = None,
) -> str:
    """Write camera_aravis2 dynamic-parameter YAML and return its path."""
    # camera_aravis2 documents Description as optional, but the Humble driver
    # reads it unconditionally for every available feature. Always materialize
    # it as a string to prevent YAML::TypedBadConversion during driver startup.
    payload = []
    for item in dynamic_parameters or []:
        if not isinstance(item, dict):
            continue
        normalized = deepcopy(item)
        feature_name = str(normalized.get("FeatureName", "")).strip()
        description = normalized.get("Description")
        if description is None:
            description = f"Dynamic GenICam feature {feature_name}."
        normalized["Description"] = str(description)
        payload.append(normalized)
    if target_path is None:
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", camera_name)
        target_path = os.path.join(
            tempfile.gettempdir(),
            f"{safe_name}_dynamic_parameters.yaml",
        )

    with open(target_path, "w", encoding="utf-8") as file_handle:
        yaml.safe_dump(payload, file_handle, sort_keys=False)
    return target_path
