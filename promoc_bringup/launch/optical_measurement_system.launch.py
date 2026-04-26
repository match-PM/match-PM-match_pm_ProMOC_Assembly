#!/usr/bin/env python3
"""Optical measurement launch for the hardware-only messstand."""

from __future__ import annotations

import json
import os

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
    load_user_config,
    load_yaml_config,
    materialize_camera_info_yaml,
    materialize_dynamic_parameters_yaml,
    resolve_runtime_mode,
)

os.environ["RCUTILS_CONSOLE_OUTPUT_FORMAT"] = "{time}: [{name}] [{severity}]\t{message}"

X_AXIS_NAME = "lts300_x_axis"


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
                default_value="ids_u3_3800cp_hq",
                description="IDS camera config filename in config/cameras without extension.",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    runtime_mode = resolve_runtime_mode(context, logger=launch.logging.get_logger())
    camera_type = LaunchConfiguration("camera_type").perform(context).strip()
    bringup_share = get_package_share_directory("promoc_bringup")
    logger = launch.logging.get_logger()

    user_config = load_user_config(bringup_share)
    axis_config = load_linear_axis_config(bringup_share, X_AXIS_NAME)
    camera_profile = _load_camera_profile(bringup_share, camera_type, logger)
    if not camera_profile:
        return [LogInfo(msg=f"Optical measurement runtime_mode={runtime_mode}")]

    camera_params = camera_profile.get("camera_params", {})
    camera_info = camera_profile.get("camera_info", {})
    exposure_config = camera_profile.get("exposure_time", {})
    camera_mtf_params = camera_profile.get("mtf_params", {})
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
        _create_startup_info(),
        LogInfo(
            msg=(
                "Camera stream target: "
                f"{camera_params.get('sensor_resolution_h', camera_info.get('image_width', 5536))}x"
                f"{camera_params.get('sensor_resolution_v', camera_info.get('image_height', 3692))}, "
                f"exposure={float(exposure_config.get('default_ms', 30.0)):.2f} ms"
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
                )
            ],
        ),
    ]


def _load_camera_profile(bringup_share: str, camera_type: str, logger) -> dict:
    config_path = get_config_path(bringup_share, os.path.join("cameras", f"{camera_type}.yaml"))
    config, error = load_yaml_config(config_path)
    if error:
        logger.error(f"Failed to load camera profile '{camera_type}': {error}")
        return {}
    return config or {}


def _resolve_axis_port(axis_config: dict) -> str | None:
    serial = str(axis_config.get("serial_number", "")).strip()
    if not serial:
        return None
    connected = discover_thorlabs_devices()
    return connected.get(serial)


def _create_startup_info():
    return LogInfo(
        msg="\n"
        "=== ProMOC Measurement Stand ===\n"
        "Services: /promoc/camera/autofocus, /promoc/camera/measure_mtf_center, /promoc/camera/measure_mtf_roi, /promoc/camera/set_exposure\n"
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
    executable = {"usb3vision": "camera_driver_uv", "gigevision": "camera_driver_gv"}[
        driver_type
    ]
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
                "pixel_size_um": config["camera"]["pixel_size_um"],
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
                "mtf.use_full_frame": False,
                "mtf.use_raw_capture": bool(mtf_config.get("use_raw_capture", True)),
                "mtf.capture_required_raw": bool(
                    mtf_config.get("capture_required_raw", True)
                ),
                "mtf.capture_pixel_format": camera_params.get(
                    "mtf_capture_pixel_format",
                    "BayerRG12",
                ),
                "mtf.capture_bayer_pattern": camera_params.get(
                    "mtf_capture_bayer_pattern",
                    "RGGB",
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
                "enable_debug_overlay": False,
                "autofocus.refinement_samples": config["autofocus"][
                    "refinement_samples"
                ],
                "autofocus.min_step_mm": config["autofocus"]["min_step_mm"],
                "autofocus.refinement_shrink_factor": config["autofocus"][
                    "refinement_shrink_factor"
                ],
                "autofocus.profile_table_json": af_profile_json,
                "autofocus.fly_over.refinement_mode": config["fly_over"][
                    "refinement_mode"
                ],
                "autofocus.fly_over.refinement_strategy": config["fly_over"][
                    "refinement_strategy"
                ],
                "measurement_conditions.coaxial_light_voltage": config[
                    "measurement_conditions"
                ]["coaxial_light_voltage"],
                "measurement_conditions.coaxial_light_current": config[
                    "measurement_conditions"
                ]["coaxial_light_current"],
                "measurement_conditions.camera_objective": config[
                    "measurement_conditions"
                ]["camera_objective"],
                "measurement_conditions.notes": config["measurement_conditions"][
                    "notes"
                ],
            }
        ],
    )
