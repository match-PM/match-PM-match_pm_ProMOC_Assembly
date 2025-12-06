#!/usr/bin/env python3
"""
Launch file for full measurement setup.

Starts:
- Camera (camera_aravis2)
- Linear Axis (LTS300)
- Autofocus Node
- MTF Node
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Package paths
    lens_testing_share = get_package_share_directory('lens_testing_nodes')
    promoc_bringup_share = get_package_share_directory('promoc_bringup')

    # Parameter files
    autofocus_params = os.path.join(
        lens_testing_share, 'config', 'autofocus_params.yaml')
    mtf_params = os.path.join(lens_testing_share, 'config', 'mtf_params.yaml')

    # Camera Launch (from promoc_bringup)
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(promoc_bringup_share, 'launch',
                         'assembly_camera.launch.py')
        )
    )

    # Autofocus Node (delayed start to wait for camera)
    autofocus_node = TimerAction(
        period=3.0,  # Wait 3 seconds
        actions=[
            Node(
                package='lens_testing_nodes',
                executable='hybrid_focus_node',
                name='hybrid_focus_node',
                output='screen',
                parameters=[autofocus_params, {'auto_start': False}],
            )
        ]
    )

    # MTF Node
    mtf_node = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='lens_testing_nodes',
                executable='mtf_node',
                name='mtf_node',
                output='screen',
                parameters=[mtf_params],
            )
        ]
    )

    return LaunchDescription([
        camera_launch,
        autofocus_node,
        mtf_node,
    ])
