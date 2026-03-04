"""
System launch file for ProMOC Assembly.

Starts:
- Camera stack (via camera.launch.py)
- Planar motor (mover_node)
- Linear axes (auto hardware detection in hardware mode)

Canonical launch API:
    ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
    ros2 launch promoc_bringup system.launch.py runtime_mode:=sim
"""

from __future__ import annotations

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import launch

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
                description="Canonical runtime mode: hardware|sim",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    runtime_mode = resolve_runtime_mode(context, logger=launch.logging.get_logger())
    is_sim = runtime_mode == "sim"
    bringup_pkg = get_package_share_directory("promoc_bringup")
    logger = launch.logging.get_logger()

    logger.info(f"Runtime mode: {runtime_mode}")
    actions = []

    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_pkg, "launch", "camera.launch.py")
        ),
        launch_arguments={"runtime_mode": runtime_mode}.items(),
    )
    actions.append(camera_launch)

    mover_config = os.path.join(bringup_pkg, "config", "mover_node_params.yaml")
    if os.path.exists(mover_config):
        actions.append(
            Node(
                package="planar_motor_nodes",
                executable="mover_node",
                name="mover_node",
                parameters=[mover_config],
                output="screen",
                arguments=["--ros-args", "--log-level", "INFO"],
            )
        )
    else:
        logger.error(f"Mover config not found: {mover_config}")

    axes_config_path = get_config_path(bringup_pkg, "linear_axes_params.yaml")
    axes_config_raw, axes_error = load_yaml_config(axes_config_path)
    if axes_error:
        logger.error(f"Failed to load linear axes configuration: {axes_error}")
        return actions

    axes_config = {}
    for node_name, node_cfg in axes_config_raw.items():
        if isinstance(node_cfg, dict) and isinstance(
            node_cfg.get("ros__parameters"), dict
        ):
            axes_config[node_name] = node_cfg

    if not axes_config:
        logger.warn(
            "No valid linear-axis entries found in linear_axes_params.yaml "
            "(expected '<node_name>.ros__parameters')."
        )
        return actions

    if is_sim:
        logger.info("Linear axes mode: SIMULATION")
        for node_name in axes_config.keys():
            actions.append(_create_axis_node(node_name, axes_config_path, sim=True))
        return actions

    logger.info("Linear axes mode: HARDWARE")
    connected = discover_connected_devices()
    for node_name, params in axes_config.items():
        serial = params.get("ros__parameters", {}).get("serial_number")
        if not serial:
            logger.warn(f"{node_name}: No serial_number configured")
            continue

        if serial in connected:
            logger.info(f"{node_name}: connected")
            actions.append(
                _create_axis_node(
                    node_name,
                    axes_config_path,
                    sim=False,
                    device_path=connected[serial],
                )
            )
        else:
            logger.warn(f"{node_name}: not connected (serial={serial})")

    return actions


def _create_axis_node(
    node_name: str, config_path: str, sim: bool, device_path: str = None
):
    params = [config_path, {"use_sim_time": sim}]
    if device_path:
        params.append({"serial_port": device_path})

    return Node(
        package="linear_axis_nodes",
        executable="lts300_node",
        name=node_name,
        parameters=params,
        output="screen",
        arguments=["--ros-args", "--log-level", "INFO"],
    )
