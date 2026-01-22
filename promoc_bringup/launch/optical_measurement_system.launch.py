#!/usr/bin/env python3
"""
ProMOC Optical Measurement System Launch File

Starts complete optical measurement station with:
1. assembly_camera - Camera driver (camera_aravis2) 
2. camera_node - Image processing with services:
   - Autofocus (multi-level refinement algorithm)
   - MTF measurement (ISO 12233 slanted edge)
   - ROI selection
3. lts300_x_axis - X-axis linear stage for focus positioning

Usage:
    ros2 launch promoc_bringup optical_measurement_system.launch.py
    ros2 launch promoc_bringup optical_measurement_system.launch.py use_simulator:=true
    ros2 launch promoc_bringup optical_measurement_system.launch.py x_axis_port:=/dev/ttyUSB1

Available Services:
    # Autofocus
    ros2 service call /camera_node/autofocus promoc_assembly_interfaces/srv/AutoFocus \\
        "{start_position: 100.0, end_position: 150.0, step_size: 5.0}"
    
    # MTF Measurement
    ros2 service call /camera_node/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF "{}"
"""

import os
import yaml
from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, TimerAction
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node

# Console output format
os.environ['RCUTILS_CONSOLE_OUTPUT_FORMAT'] = '{time}: [{name}] [{severity}]\t{message}'


def load_user_config():
    """Load user configuration from user_config.yaml with fallback to defaults."""
    config_dir = os.path.join(
        get_package_share_directory('promoc_bringup'), 'config')
    user_config_path = os.path.join(config_dir, 'user_config.yaml')
    
    defaults = {
        'user': {'name': 'default_user'},
        'autofocus': {
            'refinement_samples': 51,
            'min_step_mm': 0.010,
            'refinement_shrink_factor': 0.25,
        },
        'camera': {
            'pixel_size_um': 3.45,
            'mtf_csv_path': '/tmp/mtf_results.csv',
        },
        'measurement_conditions': {
            'coaxial_light_voltage': 0.0,
            'coaxial_light_current': 0.0,
            'camera_objective': 'unknown',
            'notes': '',
        }
    }
    
    if os.path.exists(user_config_path):
        try:
            with open(user_config_path, 'r') as f:
                user_config = yaml.safe_load(f) or {}
            # Merge user config with defaults
            for section in defaults:
                if section in user_config:
                    defaults[section].update(user_config[section])
            print(f"✓ Loaded user config: {user_config_path}")
        except Exception as e:
            print(f"⚠ Failed to load user config: {e}, using defaults")
    else:
        print(f"ℹ No user config found at {user_config_path}, using defaults")
        print(f"  Create one with: cp user_config.example.yaml user_config.yaml")
    
    return defaults


def generate_launch_description():
    """Generate launch description for optical measurement system."""

    # Load user configuration
    config = load_user_config()

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
                'measurement.username': config['user']['name'],
                'use_simulator': LaunchConfiguration('use_simulator'),
                'z_axis_node_name': LaunchConfiguration('x_axis_name'),
                'pixel_size_um': config['camera']['pixel_size_um'],
                'mtf_csv_path': config['camera']['mtf_csv_path'],
                # Autofocus: Multi-level refinement down to 10µm (LTS300: 4µm repeatable, 70µm DOF)
                'autofocus.refinement_samples': config['autofocus']['refinement_samples'],
                'autofocus.min_step_mm': config['autofocus']['min_step_mm'],
                'autofocus.refinement_shrink_factor': config['autofocus']['refinement_shrink_factor'],
                # Measurement conditions for CSV documentation
                'measurement_conditions.coaxial_light_voltage': config['measurement_conditions']['coaxial_light_voltage'],
                'measurement_conditions.coaxial_light_current': config['measurement_conditions']['coaxial_light_current'],
                'measurement_conditions.camera_objective': config['measurement_conditions']['camera_objective'],
                'measurement_conditions.notes': config['measurement_conditions']['notes'],
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
            "║  ProMOC Optical Measurement System                                ║\n"
            "╠═══════════════════════════════════════════════════════════════════╣\n"
            "║  Components:                                                      ║\n"
            "║    1. Camera Driver (camera_aravis2)                              ║\n"
            "║    2. Camera Node (image processing + services)                   ║\n"
            "║    3. X-Axis Linear Stage (LTS300)                                ║\n"
            "╠═══════════════════════════════════════════════════════════════════╣\n"
            "║  Available Services:                                              ║\n"
            "║    • Autofocus: /camera_node/autofocus                            ║\n"
            "║    • MTF Measurement: /camera_node/measure_mtf                    ║\n"
            "║    • ROI Selection: /camera_node/select_roi                       ║\n"
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
