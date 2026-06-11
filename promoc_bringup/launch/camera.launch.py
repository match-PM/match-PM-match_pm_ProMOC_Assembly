"""Camera launch file for raw image streaming."""

from __future__ import annotations

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "driver_mode",
                default_value="hardware",
                description="Canonical driver mode: hardware|mock",
            ),
            DeclareLaunchArgument(
                "camera_type",
                default_value="ids_u3_3800cp_hq",
                description="Camera config filename in config/cameras without extension.",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    driver_mode = LaunchConfiguration("driver_mode").perform(context).strip().lower()
    is_sim = driver_mode == "mock"
    camera_type = LaunchConfiguration("camera_type").perform(context).strip()
    logger = launch.logging.get_logger()

    logger.info(f"Camera launch driver_mode={driver_mode}")
    actions = []

    camera_config = os.path.join(
        get_package_share_directory("camera_nodes"), "config", "camera.yaml"
    )

    if is_sim:
        actions.append(
            Node(
                package="camera_nodes",
                executable="camera_node",
                name="camera_node",
                namespace="promoc",
                output="screen",
                parameters=[camera_config, {"driver_mode": "mock"}],
                arguments=["--ros-args", "--log-level", "INFO"],
            )
        )
        return actions

    bringup_pkg_share = get_package_share_directory("promoc_bringup")
    camera_hardware_config_file = os.path.join(
        bringup_pkg_share, "config", "cameras", f"{camera_type}.yaml"
    )

    if not os.path.exists(camera_hardware_config_file):
        logger.error(f"Camera hardware configuration file not found: {camera_hardware_config_file}")
        return []

    try:
        with open(camera_hardware_config_file, "r", encoding="utf-8") as file_handle:
            hw_config = yaml.safe_load(file_handle)

        camera_params = hw_config.get("camera_params", {})
        driver = {"usb3vision": "camera_driver_uv", "gigevision": "camera_driver_gv"}.get(
            camera_params.get("driver", "usb3vision")
        )
        driver_node_name = camera_params.get("cameraname", "assembly_camera")

        tmp_dir = tempfile.mkdtemp()
        camera_info_yaml = os.path.join(tmp_dir, "camera_info.yaml")
        with open(camera_info_yaml, "w", encoding="utf-8") as file_handle:
            file_handle.write(yaml.dump(hw_config.get("camera_info", {})))

        dynamic_parameters_yaml = os.path.join(tmp_dir, "dynamic_parameters.yaml")
        with open(dynamic_parameters_yaml, "w", encoding="utf-8") as file_handle:
            file_handle.write(yaml.dump(hw_config.get("dynamic_parameters", [])))

        # Build basic parameters for the hardware driver
        # We removed complex build_driver_node_parameters to simplify
        driver_params = [
            {"camera_info_url": f"file://{camera_info_yaml}"},
            {"dynamic_parameters_url": f"file://{dynamic_parameters_yaml}"},
            {"guid": camera_params.get("guid", "")},
            {"frame_id": "assembly_camera_frame"},
        ]

        actions.append(
            Node(
                name=driver_node_name,
                namespace="promoc",
                package="camera_aravis2",
                executable=driver,
                output="screen",
                emulate_tty=True,
                arguments=["--ros-args", "--log-level", "INFO"],
                parameters=driver_params,
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
                parameters=[camera_config, {"driver_mode": "hardware"}],
            )
        )

    except Exception as exc:
        logger.error(f"Failed to load camera configuration: {exc}")

    return actions
