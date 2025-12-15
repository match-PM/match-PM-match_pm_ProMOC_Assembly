#!/usr/bin/env python3
"""
ProMOC Autofocus System Launch File

Startet alle notwendigen Nodes für den Autofokus-Test:
1. assembly_camera - Kamera-Treiber (camera_aravis2)
2. camera_node - Bildverarbeitung und Autofokus-Service
3. lts300_z_axis - Z-Achse für Fokus-Bewegung

Verwendung:
===========
    ros2 launch promoc_bringup autofocus_system.launch.py

    # Mit Simulator (ohne echte Kamera):
    ros2 launch promoc_bringup autofocus_system.launch.py use_simulator:=true

    # Mit anderem USB-Port für Z-Achse:
    ros2 launch promoc_bringup autofocus_system.launch.py z_axis_port:=/dev/ttyUSB1

Autofokus starten:
==================
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

    # ══════════════════════════════════════════════════════════════════════════
    # Launch Arguments
    # ══════════════════════════════════════════════════════════════════════════
    use_simulator_arg = DeclareLaunchArgument(
        'use_simulator',
        default_value='false',
        description='Use simulated camera instead of real hardware'
    )

    z_axis_port_arg = DeclareLaunchArgument(
        'z_axis_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for Z-axis (LTS300)'
    )

    z_axis_name_arg = DeclareLaunchArgument(
        'z_axis_name',
        default_value='lts300_z_axis',
        description='Node name for Z-axis'
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Node 1: Camera Driver (camera_aravis2)
    # ══════════════════════════════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════════════════════════════
    # Node 2: Camera Node (Bildverarbeitung + Autofokus)
    # ══════════════════════════════════════════════════════════════════════════
    camera_node = Node(
        package='camera_nodes',
        executable='camera_node',
        name='camera_node',
        output='screen',
        emulate_tty=True,
        parameters=[
            {
                'use_simulator': LaunchConfiguration('use_simulator'),
                'z_axis_node_name': LaunchConfiguration('z_axis_name'),
                'pixel_size_um': 3.45,
                'mtf_csv_path': '/tmp/mtf_results.csv',
                # Autofokus: standardmäßig Multi-Level Refinement bis 10µm
                'autofocus.enable_multilevel': True,
                'autofocus.refinement_samples': 51,
                'autofocus.min_step_mm': 0.01,
                'autofocus.refinement_shrink_factor': 0.35,
            }
        ]
    )

    # Delay camera_node start to wait for camera driver
    camera_node_delayed = TimerAction(
        period=2.0,
        actions=[camera_node]
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Node 3: Z-Axis (LTS300)
    # ══════════════════════════════════════════════════════════════════════════
    z_axis_node = Node(
        package='linear_axis_nodes',
        executable='lts300_node',
        name=LaunchConfiguration('z_axis_name'),
        output='screen',
        emulate_tty=True,
        parameters=[
            {
                'serial_port': LaunchConfiguration('z_axis_port'),
                'serial_number': '45456044',  # Detected S/N
                'debug_mode': False,
            }
        ]
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Info Messages
    # ══════════════════════════════════════════════════════════════════════════
    startup_info = LogInfo(
        msg="\n"
            "╔═══════════════════════════════════════════════════════════════════╗\n"
            "║  ProMOC Autofocus System                                          ║\n"
            "╠═══════════════════════════════════════════════════════════════════╣\n"
            "║  Starting:                                                        ║\n"
            "║    1. Camera Driver (camera_aravis2)                              ║\n"
            "║    2. Camera Node (autofocus service)                             ║\n"
            "║    3. Z-Axis (lts300_z_axis)                                      ║\n"
            "╠═══════════════════════════════════════════════════════════════════╣\n"
            "║  Autofokus starten:                                               ║\n"
            "║    ros2 service call /camera_node/autofocus \\                     ║\n"
            "║      promoc_assembly_interfaces/srv/AutoFocus \\                   ║\n"
            "║      \"{start_position: 100.0, end_position: 150.0, step_size: 5}\"║\n"
            "╚═══════════════════════════════════════════════════════════════════╝\n"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Launch Description
    # ══════════════════════════════════════════════════════════════════════════
    return LaunchDescription([
        # Arguments
        use_simulator_arg,
        z_axis_port_arg,
        z_axis_name_arg,

        # Info
        startup_info,

        # Nodes
        camera_driver_node,
        z_axis_node,
        camera_node_delayed,
    ])
