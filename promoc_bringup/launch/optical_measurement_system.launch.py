#!/usr/bin/env python3
"""Optical measurement system launch with canonical runtime mode support."""

from __future__ import annotations

import json
import os
from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch.conditions import UnlessCondition
from launch_ros.actions import Node
import launch

from promoc_bringup.launch_utils import (
    load_camera_config,
    load_linear_axis_config,
    load_user_config,
    resolve_runtime_mode,
)

os.environ["RCUTILS_CONSOLE_OUTPUT_FORMAT"] = "{time}: [{name}] [{severity}]\t{message}"


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "runtime_mode",
                default_value="hardware",
                description="Canonical runtime mode: hardware|sim",
            ),
            DeclareLaunchArgument("x_axis_port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("x_axis_name", default_value="lts300_x_axis"),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    runtime_mode = resolve_runtime_mode(context, logger=launch.logging.get_logger())
    use_simulator = runtime_mode == "sim"
    bringup_share = get_package_share_directory("promoc_bringup")

    user_config = load_user_config(bringup_share)
    camera_config = load_camera_config(bringup_share)
    axis_config = load_linear_axis_config(bringup_share, "lts300_x_axis")

    actions = [
        LogInfo(msg=f"Optical measurement runtime_mode={runtime_mode}"),
        _create_startup_info(),
        _create_camera_driver_node(camera_config, use_simulator),
        _create_x_axis_node(axis_config),
        TimerAction(
            period=2.0,
            actions=[_create_camera_node(user_config, camera_config, use_simulator)],
        ),
    ]
    return actions


def _create_startup_info():
    return LogInfo(
        msg="\n"
        "=== ProMOC Optical Measurement System ===\n"
<<<<<<< HEAD
        "Secondary launch path. Camera services: /promoc/camera/autofocus, /promoc/camera/set_exposure\n"
=======
        "Services: /promoc/camera/autofocus, /promoc/camera/measure_mtf\n"
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
    )


def _create_camera_driver_node(camera_config: dict, use_simulator: bool):
    return Node(
        name=camera_config.get("cameraname", "assembly_camera"),
        namespace="promoc",
        package="camera_aravis2",
        executable="camera_driver_uv",
        output="screen",
        emulate_tty=True,
        condition=UnlessCondition(str(use_simulator).lower()),
        parameters=[
            {
                "guid": camera_config.get("guid", ""),
                "frame_id": "camera_frame",
                "stream_names": ["stream0"],
                "camera_info_urls": [
                    os.path.join(
                        get_package_share_directory("camera_aravis2"),
                        "config/camera_info_example_uv.yaml",
                    )
                ],
                "verbose": False,
                "ImageFormatControl": {
                    "PixelFormat": [camera_config.get("pixel_format", "RGB8")],
                    "Width": 2448,
                    "Height": 2048,
                },
                "AcquisitionControl": {
                    "AcquisitionFrameRateEnable": True,
                    "AcquisitionFrameRate": 10.0,
                },
            }
        ],
    )


def _create_x_axis_node(axis_config: dict):
    return Node(
        package="linear_axis_nodes",
        executable="lts300_node",
        name=LaunchConfiguration("x_axis_name"),
<<<<<<< HEAD
        namespace="promoc/linear_axis",
=======
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
        output="screen",
        emulate_tty=True,
        parameters=[
            {
<<<<<<< HEAD
                "namespace": "promoc/linear_axis",
=======
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
                "serial_port": LaunchConfiguration("x_axis_port"),
                "serial_number": axis_config.get("serial_number", "45456044"),
            }
        ],
    )


def _create_camera_node(config: dict, camera_config: dict, use_simulator: bool):
    base_dir = config.get("measurement", {}).get("base_path") or os.path.join(
        os.path.expanduser("~"), "Dokumente", "Messungen"
    )
    base_dir = os.path.expanduser(str(base_dir))

<<<<<<< HEAD
=======
    mtf_config = config.get("mtf", {})
    mtf_profile = str(mtf_config.get("profile", "default"))
    mtf_debug_dir = str(mtf_config.get("debug_export_dir", "") or "")
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
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
                "use_simulator": bool(use_simulator),
                "x_axis_node_name": LaunchConfiguration("x_axis_name"),
                "pixel_size_um": config["camera"]["pixel_size_um"],
<<<<<<< HEAD
=======
                "mtf.use_full_frame": True,
                "mtf.full_frame_width": camera_config.get("sensor_resolution_h", 5536),
                "mtf.full_frame_height": camera_config.get("sensor_resolution_v", 3692),
                "mtf.full_frame_offset_x": 0,
                "mtf.full_frame_offset_y": 0,
                "mtf.full_frame_binning": 1,
                "mtf.profile": mtf_profile,
                "mtf.debug_export_dir": mtf_debug_dir,
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
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
