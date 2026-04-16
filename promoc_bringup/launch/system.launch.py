"""
System launch file for the ProMOC measurement stand.

Starts:
- Camera stack (via camera.launch.py)
- The fixed LTS300 X axis in hardware mode

Canonical launch API:
    ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
"""

from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource

from promoc_bringup.launch_utils import (
    discover_thorlabs_devices as discover_connected_devices,
    get_config_path,
    load_yaml_config,
    resolve_runtime_mode,
)


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "runtime_mode",
                default_value="hardware",
                description="Canonical runtime mode. Only 'hardware' is supported.",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    runtime_mode = resolve_runtime_mode(context, logger=launch.logging.get_logger())
    bringup_pkg = get_package_share_directory("promoc_bringup")
    logger = launch.logging.get_logger()

    logger.info(f"Runtime mode: {runtime_mode}")
    actions = []

    actions.append(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(bringup_pkg, "launch", "camera.launch.py")
            ),
            launch_arguments={"runtime_mode": runtime_mode}.items(),
        )
    )

    axes_config_path = get_config_path(bringup_pkg, "linear_axes_params.yaml")
    axes_config_raw, axes_error = load_yaml_config(axes_config_path)
    if axes_error:
        logger.error(f"Failed to load linear axes configuration: {axes_error}")
        return actions

    axis_cfg = axes_config_raw.get("lts300_x_axis", {})
    axis_params = axis_cfg.get("ros__parameters", {}) if isinstance(axis_cfg, dict) else {}
    if not axis_params:
        logger.warn("No valid lts300_x_axis entry found in linear_axes_params.yaml.")
        return actions

    logger.info("Linear axes mode: HARDWARE")
    connected = discover_connected_devices()
    serial = axis_params.get("serial_number")
    if not serial:
        logger.warn("lts300_x_axis: No serial_number configured")
        return actions

    if serial in connected:
        logger.info("lts300_x_axis: connected")
        actions.append(_create_axis_node(axes_config_path, device_path=connected[serial]))
    else:
        logger.warn(f"lts300_x_axis: not connected (serial={serial})")

    return actions


def _create_axis_node(config_path: str, device_path: str | None = None):
    from launch_ros.actions import Node

    params = [config_path, {"use_sim_time": False}]
    if device_path:
        params.append({"serial_port": device_path})

    return Node(
        package="linear_axis_nodes",
        executable="lts300_node",
        name="lts300_x_axis",
        parameters=params,
        output="screen",
        arguments=["--ros-args", "--log-level", "INFO"],
    )
