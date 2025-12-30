#!/usr/bin/env python3
"""
ProMOC Autofocus System Launch File

Starts all required nodes for autofocus testing:
1. assembly_camera - Camera driver (camera_aravis2)
2. camera_node - Image processing and autofocus service
3. lts300_x_axis - X-axis for focus movement

Usage:
    ros2 launch promoc_bringup autofocus_system.launch.py
    ros2 launch promoc_bringup autofocus_system.launch.py use_simulator:=true
    ros2 launch promoc_bringup autofocus_system.launch.py x_axis_port:=/dev/ttyUSB1

Start autofocus:
    ros2 service call /camera_node/autofocus promoc_assembly_interfaces/srv/AutoFocus \\
        "{start_position: 100.0, end_position: 150.0, step_size: 0.5}"
"""

import os
from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, TimerAction
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node

# Console output format
os.environ['RCUTILS_CONSOLE_OUTPUT_FORMAT'] = '{time}: [{name}] [{severity}]\t{message}'


def generate_launch_description():
    """Generate launch description for autofocus system."""

    use_simulator_arg = DeclareLaunchArgument(
        'use_simulator',
        default_value='false',
        description='Use simulated camera instead of real hardware'
    )

    x_axis_port_arg = DeclareLaunchArgument(
        'x_axis_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for X-axis (LTS300)'
    )

    x_axis_name_arg = DeclareLaunchArgument(
        'x_axis_name',
        default_value='lts300_x_axis',
        description='Node name for X-axis'
    )

    camera_driver_node = Node(
        name='assembly_camera',
        namespace='promoc',
        package='camera_aravis2',
        executable='camera_driver_uv',
        output='screen',
        emulate_tty=True,
        condition=UnlessCondition(LaunchConfiguration('use_simulator')),
        parameters=[
            {
                'guid': 'IDS Imaging Development Systems GmbH-1409f4a43375-4104401781',
                'frame_id': 'camera_frame',
                'stream_names': ['stream0'],
                'camera_info_urls': [os.path.join(
                    get_package_share_directory('camera_aravis2'),
                    'config/camera_info_example_uv.yaml')],
                'verbose': False,
                'ImageFormatControl': {
                    'PixelFormat': ['RGB8'],
                    'Width': 2448,
                    'Height': 2048
                },
                'AcquisitionControl': {
                    'AcquisitionFrameRateEnable': True,
                    'AcquisitionFrameRate': 10.0
                }
            }
        ]
    )

    camera_node = Node(
        package='camera_nodes',
        executable='camera_node',
        name='camera_node',
        output='screen',
        emulate_tty=True,
        parameters=[
            {
                'use_simulator': LaunchConfiguration('use_simulator'),
                'z_axis_node_name': LaunchConfiguration('x_axis_name'),
                'pixel_size_um': 3.45,
                'mtf_csv_path': '/tmp/mtf_results.csv',
                # Autofocus: Multi-level refinement down to 10µm by default
                'autofocus.enable_multilevel': True,
                'autofocus.refinement_samples': 51,
                'autofocus.min_step_mm': 0.01,
                'autofocus.refinement_shrink_factor': 0.35,
            }
        ]
    )

    camera_node_delayed = TimerAction(
        period=2.0,
        actions=[camera_node]
    )

    x_axis_node = Node(
        package='linear_axis_nodes',
        executable='lts300_node',
        name=LaunchConfiguration('x_axis_name'),
        output='screen',
        emulate_tty=True,
        parameters=[
            {
                'serial_port': LaunchConfiguration('x_axis_port'),
                'serial_number': '45456044',
                'debug_mode': False,
            }
        ]
    )

    startup_info = LogInfo(
        msg="\n"
            "╔═══════════════════════════════════════════════════════════════════╗\n"
            "║  ProMOC Autofocus System                                          ║\n"
            "╠═══════════════════════════════════════════════════════════════════╣\n"
            "║  Starting:                                                        ║\n"
            "║    1. Camera Driver (camera_aravis2)                              ║\n"
            "║    2. Camera Node (autofocus service)                             ║\n"
            "║    3. X-Axis (lts300_x_axis)                                      ║\n"
            "╠═══════════════════════════════════════════════════════════════════╣\n"
            "║  Start autofocus:                                                 ║\n"
            "║    ros2 service call /camera_node/autofocus \\                     ║\n"
            "║      promoc_assembly_interfaces/srv/AutoFocus \\                   ║\n"
            "║      \"{start_position: 100.0, end_position: 150.0, step_size: 5}\"║\n"
            "╚═══════════════════════════════════════════════════════════════════╝\n"
    )

    return LaunchDescription([
        use_simulator_arg,
        x_axis_port_arg,
        x_axis_name_arg,

        startup_info,

        camera_driver_node,
        x_axis_node,
        camera_node_delayed,
    ])
