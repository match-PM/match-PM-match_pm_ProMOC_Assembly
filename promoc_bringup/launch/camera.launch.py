"""Camera stack launch file with canonical runtime mode support."""

from __future__ import annotations

import os
import subprocess
import tempfile
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import launch

from promoc_bringup.launch_utils import resolve_runtime_mode
from promoc_bringup.camera_launch_builder import (
    build_camera_node_parameters,
    build_driver_node_parameters,
    resolve_binning_factor,
)


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
                description="Camera config filename in config/cameras without extension.",
            ),
            DeclareLaunchArgument(
                "binning_factor",
                default_value="",
                description="Optional camera binning override (e.g. 1 or 2).",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    runtime_mode = resolve_runtime_mode(context, logger=launch.logging.get_logger())
    camera_type = LaunchConfiguration("camera_type").perform(context).strip()
    binning_override = LaunchConfiguration("binning_factor").perform(context).strip()
    logger = launch.logging.get_logger()

    logger.info(f"Camera launch runtime_mode={runtime_mode}")
    actions = []

    bringup_pkg_share = get_package_share_directory("promoc_bringup")
    camera_config_file = os.path.join(
        bringup_pkg_share, "config", "cameras", f"{camera_type}.yaml"
    )

    if not os.path.exists(camera_config_file):
        logger.error(f"Camera configuration file not found: {camera_config_file}")
        return []

    _run_prelaunch_reset(bringup_pkg_share)

    try:
        with open(camera_config_file, "r", encoding="utf-8") as file_handle:
            camera_config = yaml.safe_load(file_handle)

        camera_params = camera_config["camera_params"]
        driver = {"usb3vision": "camera_driver_uv", "gigevision": "camera_driver_gv"}[
            camera_params["driver"]
        ]
        driver_node_name = camera_params["cameraname"]

        tmp_dir = tempfile.mkdtemp()
        camera_info_yaml = os.path.join(tmp_dir, "camera_info.yaml")
        with open(camera_info_yaml, "w", encoding="utf-8") as file_handle:
            file_handle.write(yaml.dump(camera_config["camera_info"]))

        dynamic_parameters_yaml = os.path.join(tmp_dir, "dynamic_parameters.yaml")
        with open(dynamic_parameters_yaml, "w", encoding="utf-8") as file_handle:
            file_handle.write(yaml.dump(camera_config["dynamic_parameters"]))

        binning_factor = resolve_binning_factor(
            camera_params,
            binning_override,
            logger,
        )

        actions.append(
            Node(
                name=driver_node_name,
                namespace="promoc",
                package="camera_aravis2",
                executable=driver,
                output="screen",
                emulate_tty=True,
                arguments=["--ros-args", "--log-level", "INFO"],
                parameters=[
                    build_driver_node_parameters(
                        camera_params,
                        camera_config,
                        camera_info_yaml,
                        dynamic_parameters_yaml,
                        binning_factor,
                    )
                ],
            )
        )

        actions.append(
            Node(
                name=f"{driver_node_name}_controller",
                namespace="promoc",
                package="pm_genicam_controller",
                executable="controller",
                output="screen",
                emulate_tty=True,
                arguments=["--ros-args", "--log-level", "INFO"],
                parameters=[{"driver_node": f"/promoc/{driver_node_name}"}],
            )
        )

        actions.append(
            Node(
                package="camera_nodes",
                executable="camera_node",
                name="camera_node",
                namespace="promoc",
                output="screen",
                arguments=["--ros-args", "--log-level", "INFO"],
                parameters=[
                    build_camera_node_parameters(
                        camera_params,
                        camera_config,
                    )
                ],
            )
        )

    except Exception as exc:
        logger.error(f"Failed to load camera configuration: {exc}")

    return actions


def _run_prelaunch_reset(bringup_pkg_share: str) -> None:
    logger = launch.logging.get_logger()
    reset_script_locations = [
        os.path.join(
            os.path.dirname(__file__), "..", "promoc_bringup", "camera_reset_hook.py"
        ),
        os.path.join(
            bringup_pkg_share,
            "..",
            "..",
            "..",
            "src",
            "match-PM-match_pm_ProMOC_Assembly",
            "promoc_bringup",
            "promoc_bringup",
            "camera_reset_hook.py",
        ),
    ]

    reset_script = None
    for location in reset_script_locations:
        if os.path.exists(location):
            reset_script = location
            break

    if not reset_script:
        logger.warn("Pre-launch reset script not found, skipping automatic reset.")
        return

    logger.info(f"Executing pre-launch camera reset from {reset_script}.")
    try:
        result = subprocess.run(
            ["python3", reset_script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.stdout:
            for line in result.stdout.splitlines():
                if line.strip():
                    logger.info(f"reset: {line}")
    except Exception as exc:
        logger.warn(f"Pre-launch reset failed ({exc}), continuing.")
