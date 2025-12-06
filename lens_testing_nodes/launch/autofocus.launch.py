#!/usr/bin/env python3
"""Launch file for Hybrid Autofocus Node."""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Package path
    pkg_share = get_package_share_directory('lens_testing_nodes')

    # Parameter file
    default_params = os.path.join(pkg_share, 'config', 'autofocus_params.yaml')

    # Launch Arguments
    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params,
        description='Path to parameter file'
    )

    auto_start_arg = DeclareLaunchArgument(
        'auto_start',
        default_value='false',
        description='Start automatically'
    )

    # Autofocus Node
    autofocus_node = Node(
        package='lens_testing_nodes',
        executable='hybrid_focus_node',
        name='hybrid_focus_node',
        output='screen',
        parameters=[
            LaunchConfiguration('params_file'),
            {'auto_start': LaunchConfiguration('auto_start')}
        ],
        remappings=[
            # Topic remappings if needed
        ]
    )

    return LaunchDescription([
        params_file_arg,
        auto_start_arg,
        autofocus_node,
    ])
