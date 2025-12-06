#!/usr/bin/env python3
"""Launch file for MTF Analysis Node."""

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
    default_params = os.path.join(pkg_share, 'config', 'mtf_params.yaml')

    # Launch Arguments
    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params,
        description='Path to parameter file'
    )

    # MTF Node
    mtf_node = Node(
        package='lens_testing_nodes',
        executable='mtf_node',
        name='mtf_node',
        output='screen',
        parameters=[LaunchConfiguration('params_file')],
    )

    return LaunchDescription([
        params_file_arg,
        mtf_node,
    ])
