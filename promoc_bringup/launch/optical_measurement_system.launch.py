#!/usr/bin/env python3
"""Optical measurement launch for the hardware-only messstand."""

from __future__ import annotations

import json
import os
import re

from ament_index_python import get_package_share_directory
import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from promoc_bringup.launch_utils import (
    discover_thorlabs_devices,
    get_config_path,
    load_linear_axis_config,
    load_target_tilt_config,
    load_user_config,
    load_yaml_config,
    materialize_camera_info_yaml,
    materialize_dynamic_parameters_yaml,
    resolve_runtime_mode,
)

os.environ["RCUTILS_CONSOLE_OUTPUT_FORMAT"] = "{time}: [{name}] [{severity}]\t{message}"

X_AXIS_NAME = "lts300_x_axis"
DEFAULT_CAMERA_PROFILE = "ids_u3_3800cp_m_gl_r22"
CAMERA_PROFILE_ALIASES = {
    "ids_u3_3800cp_hq": "ids_u3_3800cp_m_gl_r22",
}
SUPPORTED_CAMERA_DRIVERS = {
    "usb3vision": "camera_driver_uv",
    "gigevision": "camera_driver_gv",
}


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "runtime_mode",
                default_value="hardware",
                description="Canonical runtime mode. Only 'hardware' is supported.",
            ),
            DeclareLaunchArgument(
                "camera_type",
                default_value="profile",
                description=(
                    "Camera profile filename in config/cameras without extension. "
                    "The default 'profile' reads camera.profile from user_config.yaml."
                ),
            ),
            DeclareLaunchArgument(
                "mtf_analysis_channel",
                default_value="profile",
                description=(
                    "MTF sampling channel: profile, auto, mono, or green. "
                    "Use green only with a raw Bayer color-camera profile."
                ),
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    runtime_mode = resolve_runtime_mode(context, logger=launch.logging.get_logger())
    camera_type_override = LaunchConfiguration("camera_type").perform(context).strip()
    mtf_analysis_channel_override = LaunchConfiguration(
        "mtf_analysis_channel"
    ).perform(context).strip()
    bringup_share = get_package_share_directory("promoc_bringup")
    logger = launch.logging.get_logger()

    user_config = load_user_config(bringup_share)
    axis_config = load_linear_axis_config(bringup_share, X_AXIS_NAME)
    camera_type = _resolve_camera_profile_name(
        camera_type_override,
        user_config,
        logger,
    )
    camera_profile = _load_camera_profile(bringup_share, camera_type, logger)
    if not camera_profile:
        return [LogInfo(msg=f"Optical measurement runtime_mode={runtime_mode}")]

    camera_params = camera_profile.get("camera_params", {})
    camera_info = camera_profile.get("camera_info", {})
    exposure_config = camera_profile.get("exposure_time", {})
    camera_mtf_params = camera_profile.get("mtf_params", {})
    target_tilt_config, target_tilt_profile, tilt_profile_error = load_target_tilt_config(
        bringup_share, user_config
    )
    if tilt_profile_error:
        logger.warn(
            f"Target-tilt imaging profile could not be loaded: {tilt_profile_error}; "
            "using user_config and node defaults."
        )
    elif target_tilt_profile:
        logger.info(
            f"Target-tilt configuration: imaging profile '{target_tilt_profile}' "
            "overridden by user_config.yaml"
        )
    driver_type = str(camera_params.get("driver", "")).strip().lower()
    if driver_type not in SUPPORTED_CAMERA_DRIVERS:
        driver_note = str(camera_params.get("driver_note", "")).strip()
        logger.error(
            f"Camera profile '{camera_type}' requires driver '{driver_type or 'unknown'}', "
            "but this launch currently supports only USB3 Vision and GigE Vision."
            + (f" {driver_note}" if driver_note else "")
        )
        return [
            LogInfo(msg=f"Optical measurement runtime_mode={runtime_mode}"),
            LogInfo(msg=f"Camera profile: {camera_type} (not started)"),
        ]

    pixel_size_um = _resolve_camera_pixel_size_um(
        user_config,
        camera_params,
        camera_mtf_params,
        logger,
    )
    mtf_analysis_channel = _resolve_mtf_analysis_channel(
        mtf_analysis_channel_override,
        camera_mtf_params,
        logger,
    )
    dynamic_parameters = camera_profile.get("dynamic_parameters", [])
    driver_declared_parameter_names = [
        str(item.get("FeatureName", "")).strip()
        for item in dynamic_parameters
        if isinstance(item, dict) and str(item.get("FeatureName", "")).strip()
    ]
    serial_port = _resolve_axis_port(axis_config)
    camera_name = str(camera_params.get("cameraname", "promoc_camera")).strip()
    driver_camera_info_path = materialize_camera_info_yaml(
        camera_info,
        frame_id="camera_frame",
        stream_name="stream0",
    )
    driver_dynamic_parameters_path = materialize_dynamic_parameters_yaml(
        dynamic_parameters,
        camera_name=camera_name,
    )

    return [
        LogInfo(msg=f"Optical measurement runtime_mode={runtime_mode}"),
        LogInfo(msg=f"Camera profile: {camera_type}"),
        _create_startup_info(),
        LogInfo(
            msg=(
                "Camera stream target: "
                f"{camera_params.get('sensor_resolution_h', camera_info.get('image_width', 5536))}x"
                f"{camera_params.get('sensor_resolution_v', camera_info.get('image_height', 3692))}, "
                f"exposure={float(exposure_config.get('default_ms', 30.0)):.2f} ms"
            )
        ),
        LogInfo(
            msg=(
                f"MTF analysis channel: {mtf_analysis_channel}, "
                f"sensor pixel size: {pixel_size_um:.3f} um"
            )
        ),
        _create_camera_driver_node(
            camera_params,
            camera_info,
            exposure_config,
            driver_camera_info_path,
            driver_dynamic_parameters_path,
        ),
        _create_x_axis_node(axis_config, serial_port),
        TimerAction(
            period=2.0,
            actions=[
                _create_camera_node(
                    user_config,
                    camera_params,
                    camera_info,
                    camera_mtf_params,
                    exposure_config,
                    driver_declared_parameter_names,
                    mtf_analysis_channel,
                    pixel_size_um,
                ),
                _create_target_tilt_node(
                    camera_params,
                    target_tilt_config,
                    pixel_size_um,
                ),
            ],
        ),
    ]


def _resolve_camera_profile_name(override: str, user_config: dict, logger) -> str:
    """Resolve the profile selected in user_config with a launch-time override."""
    configured = str(
        user_config.get("camera", {}).get("profile", DEFAULT_CAMERA_PROFILE)
    ).strip()
    requested = str(override or "profile").strip()
    resolved = configured if requested.lower() in {"", "profile"} else requested
    if not resolved:
        resolved = DEFAULT_CAMERA_PROFILE
    if resolved in CAMERA_PROFILE_ALIASES:
        replacement = CAMERA_PROFILE_ALIASES[resolved]
        logger.warn(
            f"Camera profile '{resolved}' is deprecated; using '{replacement}'."
        )
        resolved = replacement
    if not re.fullmatch(r"[A-Za-z0-9_-]+", resolved):
        logger.warn(
            f"Invalid camera profile name '{resolved}', falling back to "
            f"'{DEFAULT_CAMERA_PROFILE}'."
        )
        return DEFAULT_CAMERA_PROFILE
    return resolved


def _load_camera_profile(bringup_share: str, camera_type: str, logger) -> dict:
    config_path = get_config_path(bringup_share, os.path.join("cameras", f"{camera_type}.yaml"))
    config, error = load_yaml_config(config_path)
    if error:
        logger.error(f"Failed to load camera profile '{camera_type}': {error}")
        return {}
    return config or {}


def _resolve_camera_pixel_size_um(
    user_config: dict,
    camera_params: dict,
    camera_mtf_params: dict,
    logger,
) -> float:
    """Use the selected camera's pitch unless a positive user override is set."""
    override = user_config.get("camera", {}).get("pixel_size_um")
    if override is not None and override != "":
        try:
            override_value = float(override)
            if override_value > 0:
                logger.warn(
                    "camera.pixel_size_um overrides the selected camera profile; "
                    "remove it to use the profile value."
                )
                return override_value
        except (TypeError, ValueError):
            logger.warn(
                f"Ignoring invalid camera.pixel_size_um={override!r}; using profile value."
            )

    candidates = (
        (camera_params.get("pixelsize"), 1.0),
        (camera_mtf_params.get("pixel_size_mm"), 1000.0),
    )
    for candidate, scale in candidates:
        try:
            value = float(candidate) * scale
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    raise ValueError("Selected camera profile has no positive sensor pixel size")


def _resolve_axis_port(axis_config: dict) -> str | None:
    serial = str(axis_config.get("serial_number", "")).strip()
    if not serial:
        return None
    connected = discover_thorlabs_devices()
    return connected.get(serial)


def _resolve_mtf_analysis_channel(
    override: str,
    camera_mtf_params: dict,
    logger,
) -> str:
    """Resolve the per-camera MTF channel with an optional launch override."""
    profile_value = str(
        camera_mtf_params.get("analysis_channel", "auto")
    ).strip().lower()
    requested = str(override or "profile").strip().lower()
    resolved = profile_value if requested in {"", "profile"} else requested
    if resolved not in {"auto", "mono", "green"}:
        logger.warn(
            f"Invalid mtf_analysis_channel='{resolved}', falling back to 'auto'."
        )
        return "auto"
    return resolved


def _create_startup_info():
    return LogInfo(
        msg="\n"
        "=== ProMOC Measurement Stand ===\n"
        "Services: /promoc/camera/autofocus, /promoc/camera/measure_tenengrad_roi, /promoc/camera/measure_mtf, /promoc/camera/measure_mtf_center, /promoc/camera/measure_mtf_roi, /promoc/camera/set_exposure\n"
        "Tilt service (rqt): /promoc/promoc_camera/estimate_target_tilt_service\n"
        "Tilt action: /promoc/promoc_camera/estimate_target_tilt\n"
      )


def _create_camera_driver_node(
    camera_params: dict,
    camera_info: dict,
    exposure_config: dict,
    camera_info_path: str,
    dynamic_parameters_path: str,
):
    camera_name = str(camera_params.get("cameraname", "promoc_camera")).strip()
    driver_type = camera_params.get("driver", "usb3vision")
    executable = SUPPORTED_CAMERA_DRIVERS[driver_type]
    target_width = int(
        camera_params.get("sensor_resolution_h", camera_info.get("image_width", 5536))
    )
    target_height = int(
        camera_params.get("sensor_resolution_v", camera_info.get("image_height", 3692))
    )
    target_exposure_us = float(exposure_config.get("default_ms", 30.0)) * 1000.0
    return Node(
        name=camera_name,
        namespace="promoc",
        package="camera_aravis2",
        executable=executable,
        output="screen",
        emulate_tty=True,
        parameters=[
            {
                "guid": camera_params.get("guid", ""),
                "frame_id": "camera_frame",
                "stream_names": ["stream0"],
                "camera_info_urls": [camera_info_path],
                "dynamic_parameters_yaml_url": dynamic_parameters_path,
                "verbose": False,
                "ImageFormatControl": {
                    "PixelFormat": [camera_params.get("pixel_format", "RGB8")],
                    "Width": target_width,
                    "Height": target_height,
                    "OffsetX": 0,
                    "OffsetY": 0,
                    "BinningHorizontal": 1,
                    "BinningVertical": 1,
                },
                "AcquisitionControl": {
                    "AcquisitionFrameRateEnable": True,
                    "AcquisitionFrameRate": 10.0,
                    "ExposureAuto": "Off",
                    "ExposureTime": target_exposure_us,
                },
            }
        ],
    )


def _create_x_axis_node(axis_config: dict, serial_port: str | None):
    parameters = [{"serial_number": axis_config.get("serial_number", "45456044")}]
    if serial_port:
        parameters.append({"serial_port": serial_port})

    return Node(
        package="linear_axis_nodes",
        executable="lts300_node",
        name=X_AXIS_NAME,
        output="screen",
        emulate_tty=True,
        parameters=parameters,
    )


def _create_camera_node(
    config: dict,
    camera_params: dict,
    camera_info: dict,
    camera_mtf_params: dict,
    exposure_config: dict,
    driver_declared_parameter_names: list[str],
    mtf_analysis_channel: str,
    pixel_size_um: float,
):
    camera_name = str(camera_params.get("cameraname", "promoc_camera")).strip()
    image_topic = f"/promoc/{camera_name}/stream0/image_raw"
    camera_info_topic = f"/promoc/{camera_name}/stream0/camera_info"
    param_set_service_primary = f"/promoc/{camera_name}/set_parameters"
    param_set_service_secondary = f"/promoc/{camera_name}_controller/set_parameters"
    base_dir = config.get("measurement", {}).get("base_path") or os.path.join(
        os.path.expanduser("~"), "Dokumente", "Messungen"
    )
    base_dir = os.path.expanduser(str(base_dir))

    mtf_config = config.get("mtf", {})
    mtf_profile = str(mtf_config.get("profile", "default"))
    mtf_debug_dir = str(mtf_config.get("debug_export_dir", "") or "")
    af_profile_json = json.dumps(config.get("autofocus_profiles", {}))

    return Node(
        package="camera_nodes",
        executable="camera_node",
        name="camera_node",
        namespace="promoc",
        output="screen",
        emulate_tty=True,
        parameters=[
            {
                "measurement.username": config["measurement"]["operator"],
                "measurement.base_path": base_dir,
                "pixel_size_um": pixel_size_um,
                "camera.image_topic": image_topic,
                "camera.camera_info_topic": camera_info_topic,
                "camera.param_set_service_primary": param_set_service_primary,
                "camera.param_set_service_secondary": param_set_service_secondary,
                "camera.driver_declared_parameters_json": json.dumps(
                    driver_declared_parameter_names
                ),
                "camera.expected_width": camera_params.get(
                    "sensor_resolution_h",
                    camera_info.get("image_width", 5536),
                ),
                "camera.expected_height": camera_params.get(
                    "sensor_resolution_v",
                    camera_info.get("image_height", 3692),
                ),
                "camera.default_pixel_format": camera_params.get(
                    "pixel_format",
                    "RGB8",
                ),
                "camera.default_exposure_us": float(
                    exposure_config.get("default_ms", 30.0)
                )
                * 1000.0,
                "camera.min_exposure_us": float(
                    exposure_config.get("min_val", 0.0)
                ),
                "camera.max_exposure_us": float(
                    exposure_config.get("max_val", 0.0)
                ),
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": bool(mtf_config.get("use_raw_capture", True)),
                "mtf.analysis_channel": mtf_analysis_channel,
                "mtf.capture_required_raw": bool(
                    mtf_config.get("capture_required_raw", True)
                ),
                "mtf.capture_pixel_format": camera_params.get(
                    "mtf_capture_pixel_format",
                    #"BayerRG12",
                     "Mono12",
                ),
                "mtf.capture_bayer_pattern": camera_params.get(
                    "mtf_capture_bayer_pattern",
                    #"RGGB",
                    "",
                ),
                "mtf.capture_width": camera_params.get(
                    "sensor_resolution_h",
                    camera_info.get("image_width", 5536),
                ),
                "mtf.capture_height": camera_params.get(
                    "sensor_resolution_v",
                    camera_info.get("image_height", 3692),
                ),
                "mtf.capture_offset_x": 0,
                "mtf.capture_offset_y": 0,
                "mtf.capture_binning": 1,
                "mtf.capture_exposure_us": float(
                    camera_mtf_params.get(
                        "recommended_exposure_ms",
                        exposure_config.get("default_ms", 30.0),
                    )
                )
                * 1000.0,
                "mtf.capture_gain": camera_mtf_params.get("recommended_gain", 0.0),
                "mtf.capture_settle_s": 0.35,
                "mtf.capture_image_timeout_s": 2.0,
                "mtf.capture_only_samples": int(
                    mtf_config.get("capture_only_samples", 10)
                ),
                "mtf.capture_only_timeout_s": float(
                    mtf_config.get("capture_only_timeout_s", 1.0)
                ),
                "mtf.capture_only_context_margin_px": int(
                    mtf_config.get("capture_only_context_margin_px", 64)
                ),
                "mtf.capture_only_save_fullframe_raw": bool(
                    mtf_config.get("capture_only_save_fullframe_raw", True)
                ),
                "mtf.capture_only_preview_png": bool(
                    mtf_config.get("capture_only_preview_png", True)
                ),
                "mtf.capture_disable_exposure_auto": True,
                "mtf.capture_disable_gain_auto": True,
                "mtf.capture_disable_white_balance_auto": True,
                "mtf.capture_disable_gamma": True,
                "mtf.capture_disable_color_transform": True,
                "mtf.raw_green_pair_warn_pct": 10.0,
                "mtf.green_wavelength_um": camera_mtf_params.get(
                    "wavelength_um",
                    0.555,
                ),
                "mtf.profile": mtf_profile,
                "mtf.debug_export_dir": mtf_debug_dir,
                "mtf_min_edge_angle": float(
                    mtf_config.get("min_edge_angle", 2.0)
                ),
                "mtf_max_edge_angle": float(
                    mtf_config.get("max_edge_angle", 11.0)
                ),
                "enable_debug_overlay": False,
                "autofocus.refinement_samples": config["autofocus"][
                    "refinement_samples"
                ],
                "autofocus.min_step_mm": config["autofocus"]["min_step_mm"],
                "autofocus.refinement_shrink_factor": config["autofocus"][
                    "refinement_shrink_factor"
                ],
                "autofocus.analysis_roi_x_px": int(
                    config["autofocus"].get("analysis_roi_x_px", -1)
                ),
                "autofocus.analysis_roi_y_px": int(
                    config["autofocus"].get("analysis_roi_y_px", -1)
                ),
                "autofocus.analysis_roi_width_px": int(
                    config["autofocus"].get("analysis_roi_width_px", 2048)
                ),
                "autofocus.analysis_roi_height_px": int(
                    config["autofocus"].get("analysis_roi_height_px", 2048)
                ),
                "autofocus.analysis_downsample_max_dim_px": int(
                    config["autofocus"].get("analysis_downsample_max_dim_px", 2048)
                ),
                "autofocus.analysis_use_center_roi": bool(
                    config["autofocus"].get("analysis_use_center_roi", True)
                ),
                "autofocus.profile_table_json": af_profile_json,
                "autofocus.fly_over.refinement_mode": config["fly_over"][
                    "refinement_mode"
                ],
                "autofocus.fly_over.refinement_strategy": config["fly_over"][
                    "refinement_strategy"
                ],
                "measurement_conditions.camera_objective": config[
                    "measurement_conditions"
                ]["camera_objective"],
                "measurement_conditions.notes": config["measurement_conditions"][
                    "notes"
                ],
            }
        ],
    )


def _create_target_tilt_node(
    camera_params: dict,
    config: dict,
    sensor_pixel_size_um: float,
):
    """Create one remappable action node in the selected camera namespace."""
    camera_name = str(camera_params.get("cameraname", "promoc_camera")).strip()
    magnification = float(config.get("magnification", camera_params.get("magnification", 1.0)))
    object_um_per_pixel = float(
        config.get("object_um_per_pixel", sensor_pixel_size_um / max(magnification, 1.0e-9))
    )
    parameter_names = (
        "roi_rows",
        "roi_cols",
        "roi_width_fraction",
        "roi_height_fraction",
        "roi_margin_fraction",
        "use_integral_image",
        "focus_metric",
        "evaluation_focus_metrics",
        "peak_fit_method",
        "surface_weighted",
        "surface_robust",
        "huber_k",
        "settle_time_s",
        "axis_timeout_s",
        "image_timeout_s",
        "axis_position_tolerance_mm",
        "min_contrast",
        "max_black_fraction",
        "max_saturated_fraction",
        "min_gradient_energy",
        "max_frame_cv",
        "min_peak_prominence",
        "min_peak_curvature",
        "min_fit_r2",
        "max_peak_uncertainty_um",
        "weight_sigma_floor_um",
        "weight_sigma_ceiling_um",
        "robust_outlier_weight_threshold",
        "min_valid_rois",
        "min_span_fraction",
        "min_quadrants",
        "max_design_condition",
        "repeatability_x_deg",
        "repeatability_y_deg",
        "tolerance_x_deg",
        "tolerance_y_deg",
        "peak_half_window",
        "bootstrap_iterations",
        "bootstrap_seed",
        "reference_surface_path",
        "evaluation_enabled",
        "evaluation_output_directory",
        "evaluation_export_all_focus_curves",
        "service_wait_timeout_s",
        "roi_selection_mode",
        "manual_target_bbox",
        "candidate_roi_width_fraction",
        "candidate_roi_height_fraction",
        "candidate_step_x_fraction",
        "candidate_step_y_fraction",
        "minimum_structured_pixel_fraction",
        "structure_mad_multiplier",
        "structure_energy_quantile",
        "analysis_max_dimension_px",
        "sparse_contrast_quantile",
        "sparse_energy_quantile",
        "minimum_gradient_snr",
        "minimum_connected_edge_pixels",
        "minimum_connected_edge_span_fraction",
        "support_closing_radius",
        "minimum_target_coverage_fraction",
        "minimum_baseline_x_mm",
        "minimum_baseline_y_mm",
        "minimum_spatial_bins_x",
        "minimum_spatial_bins_y",
        "minimum_selected_rois",
        "maximum_selected_rois",
        "minimum_quality_weight",
        "maximum_quality_weight",
        "maximum_standardized_residual",
        "diagnostic_image_enabled",
        "diagnostic_image_topic",
        "diagnostic_image_max_dimension",
    )
    parameters = {
        # Relative topics keep the node reusable for one instance per camera.
        "image_topic": "stream0/image_raw",
        "camera_info_topic": "stream0/camera_info",
        # Canonical physical focus-stage interface found in this repository.
        "axis_service_prefix": str(
            config.get("axis_service_prefix", "/promoc/linear_axis/lts300_x_axis")
        ),
        "object_um_per_pixel": object_um_per_pixel,
    }
    parameters.update(
        {
            name: config[name]
            for name in parameter_names
            if name in config
            # ROS 2 Launch cannot infer the element type of an empty array and
            # normalizes it to (), which ParameterValue rejects. The node
            # declares this parameter explicitly as STRING_ARRAY, so omitting
            # an empty override correctly yields its typed empty default.
            and not (name == "evaluation_focus_metrics" and not config[name])
        }
    )
    return Node(
        package="camera_nodes",
        executable="target_tilt_estimator",
        name="target_tilt_estimator",
        namespace=f"promoc/{camera_name}",
        output="screen",
        emulate_tty=True,
        parameters=[parameters],
    )
