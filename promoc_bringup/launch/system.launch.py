"""Main CS runtime launch file.

This is the maintained top-level entry point for the branch. It composes the
runtime from three core subsystems:
- camera stack
- two linear axes
- planar-motor mover

The launch file is intentionally orchestration-only. It decides *what starts*
and *which namespaces/configuration are applied*, while the runtime behavior
stays inside the owning packages.
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
    # Resolve one canonical runtime mode up front so every subsystem gets the
    # same interpretation of "hardware" vs "sim".
    runtime_mode = resolve_runtime_mode(context, logger=launch.logging.get_logger())
    is_sim = runtime_mode == "sim"
    bringup_pkg = get_package_share_directory("promoc_bringup")
    logger = launch.logging.get_logger()

    logger.info(f"Runtime mode: {runtime_mode}")
    actions = []

    # Keep camera bringup in its dedicated launch file so the system-level start
    # stays readable and easy to explain.
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
                name="mover",
                # Pin the mover under the canonical namespace here so the runtime
                # contract does not depend on package-internal defaults.
                namespace="promoc",
                parameters=[mover_config],
                output="screen",
                arguments=["--ros-args", "--log-level", "INFO"],
            )
        )
    else:
        logger.error(f"Mover config not found: {mover_config}")

    axis_pkg = get_package_share_directory("linear_axis_nodes")
    axes = [
        ("lts300_x_axis", os.path.join(axis_pkg, "config", "x_axis.yaml")),
        ("lts300_z_axis", os.path.join(axis_pkg, "config", "z_axis.yaml")),
    ]

    if is_sim:
        logger.info("Linear axes mode: SIMULATION")
        for node_name, config_path in axes:
            actions.append(_create_axis_node(node_name, config_path, driver_mode="mock"))
        return actions

    logger.info("Linear axes mode: HARDWARE")
    connected = discover_connected_devices()
    for node_name, config_path in axes:
        params, config_error = _load_axis_parameters(config_path)
        if config_error:
            logger.error(f"{node_name}: {config_error}")
            continue

        serial = params.get("serial_number")
        if not serial:
            logger.warn(f"{node_name}: No serial_number configured")
            continue

        if serial in connected:
            logger.info(f"{node_name}: connected")
            actions.append(
                _create_axis_node(
                    node_name,
                    config_path,
                    driver_mode="hardware",
                    device_path=connected[serial],
                )
            )
        else:
            logger.warn(f"{node_name}: not connected (serial={serial})")

    return actions


def _create_axis_node(
    node_name: str,
    config_path: str,
    driver_mode: str,
    device_path: str = None,
):
    # The launch file owns the public axis namespace so all runtime packages can
    # rely on one stable `/promoc/linear_axis/...` contract.
    params = [config_path, {"driver_mode": driver_mode}]
    if device_path:
        params.append({"serial_port": device_path})

    return Node(
        package="linear_axis_nodes",
        executable="lts300_node",
        name=node_name,
        namespace="promoc/linear_axis",
        parameters=params,
        output="screen",
        arguments=["--ros-args", "--log-level", "INFO"],
    )


def _load_axis_parameters(config_path: str):
    config, error = load_yaml_config(config_path)
    if error:
        return {}, error

    for key, value in (config or {}).items():
        if isinstance(value, dict) and isinstance(value.get("ros__parameters"), dict):
            return value["ros__parameters"], None

    return {}, f"No ros__parameters block found in {config_path}"
