"""Main ProMOC device-stack launch file.

This launch file provides one clear and predictable way to launch the
ProMOC device nodes while preserving independent package startup.
"""

from __future__ import annotations

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    """Haupt-Launch-File fuer den gesamten ProMOC Geraete-Stack.

    Startet je nach Launch-Argumenten:
    - camera (camera.launch.py)
    - x_axis (lts300_node mit x_axis.yaml)
    - z_axis (lts300_node mit z_axis.yaml)
    - planar_motor (mover_node mit planar_motor.yaml)
    - system_controller (promoc_system_controller)

    Alle Knoten teilen sich den driver_mode (hardware|mock).
    """
    driver_mode_arg = DeclareLaunchArgument(
        "driver_mode",
        default_value="hardware",
        description="hardware|mock",
    )
    camera_arg = DeclareLaunchArgument(
        "camera",
        default_value="true",
        description="true|false",
    )
    x_axis_arg = DeclareLaunchArgument(
        "x_axis",
        default_value="true",
        description="true|false",
    )
    z_axis_arg = DeclareLaunchArgument(
        "z_axis",
        default_value="true",
        description="true|false",
    )
    planar_motor_arg = DeclareLaunchArgument(
        "planar_motor",
        default_value="true",
        description="true|false",
    )
    system_controller_arg = DeclareLaunchArgument(
        "system_controller",
        default_value="false",
        description="true|false",
    )

    # Pfade zu den YAML-Konfigurationen der einzelnen Knoten
    camera_config = os.path.join(
        get_package_share_directory("camera_nodes"),
        "config",
        "camera.yaml",
    )
    x_axis_config = os.path.join(
        get_package_share_directory("linear_axis_nodes"),
        "config",
        "x_axis.yaml",
    )
    z_axis_config = os.path.join(
        get_package_share_directory("linear_axis_nodes"),
        "config",
        "z_axis.yaml",
    )
    planar_motor_config = os.path.join(
        get_package_share_directory("planar_motor_nodes"),
        "config",
        "planar_motor.yaml",
    )
    system_controller_config = os.path.join(
        get_package_share_directory("promoc_core"),
        "config",
        "system_controller.yaml",
    )

    driver_mode_param = {"driver_mode": LaunchConfiguration("driver_mode")}
    # Kamera-Launch (separate Launch-Description mit eigenem camera.launch.py)
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("promoc_bringup"),
                "launch",
                "camera.launch.py",
            )
        ),
        launch_arguments={"driver_mode": LaunchConfiguration("driver_mode")}.items(),
        condition=IfCondition(LaunchConfiguration("camera")),
    )

    # X-Achse: lts300_node im Namespace /promoc/linear_axis
    x_axis_node = Node(
        package="linear_axis_nodes",
        executable="lts300_node",
        name="lts300_x_axis",
        namespace="promoc/linear_axis",
        parameters=[x_axis_config, driver_mode_param],
        condition=IfCondition(LaunchConfiguration("x_axis")),
        output="screen",
        arguments=["--ros-args", "--log-level", "INFO"],
    )

    # Z-Achse: lts300_node im Namespace /promoc/linear_axis
    z_axis_node = Node(
        package="linear_axis_nodes",
        executable="lts300_node",
        name="lts300_z_axis",
        namespace="promoc/linear_axis",
        parameters=[z_axis_config, driver_mode_param],
        condition=IfCondition(LaunchConfiguration("z_axis")),
        output="screen",
        arguments=["--ros-args", "--log-level", "INFO"],
    )

    # Planarmotor: mover_node im Namespace /promoc
    planar_motor_node = Node(
        package="planar_motor_nodes",
        executable="mover_node",
        name="mover",
        namespace="promoc",
        parameters=[planar_motor_config, driver_mode_param],
        condition=IfCondition(LaunchConfiguration("planar_motor")),
        output="screen",
        arguments=["--ros-args", "--log-level", "INFO"],
    )

    # System-Controller: Ueberwacht alle Geraete und koordiniert Stop/Reset
    system_controller_node = Node(
        package="promoc_core",
        executable="promoc_system_controller",
        name="system_controller",
        namespace="promoc",
        parameters=[system_controller_config],
        condition=IfCondition(LaunchConfiguration("system_controller")),
        output="screen",
        arguments=["--ros-args", "--log-level", "INFO"],
    )

    return LaunchDescription(
        [
            driver_mode_arg,
            camera_arg,
            x_axis_arg,
            z_axis_arg,
            planar_motor_arg,
            system_controller_arg,
            camera_launch,
            x_axis_node,
            z_axis_node,
            planar_motor_node,
            system_controller_node,
        ]
    )
