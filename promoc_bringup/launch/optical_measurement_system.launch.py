#!/usr/bin/env python3
"""
ProMOC Optical Measurement System Launch File

Starts complete optical measurement station with:
1. assembly_camera - Camera driver (camera_aravis2) 
2. camera_node - Image processing with services (Autofocus, MTF, ROI)
3. lts300_x_axis - X-axis linear stage for focus positioning

Usage:
    ros2 launch promoc_bringup optical_measurement_system.launch.py
    ros2 launch promoc_bringup optical_measurement_system.launch.py use_simulator:=true
"""

import os
import json
from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, TimerAction
from launch.substitutions import LaunchConfiguration
from launch.conditions import UnlessCondition
from launch_ros.actions import Node

from promoc_bringup.launch_utils import (
    load_user_config,
    load_camera_config,
    load_linear_axis_config,
)

# Console output format
os.environ['RCUTILS_CONSOLE_OUTPUT_FORMAT'] = '{time}: [{name}] [{severity}]\t{message}'


def generate_launch_description():
    """Generate launch description for optical measurement system."""
    bringup_share = get_package_share_directory('promoc_bringup')
    
    # Load all configurations
    user_config = load_user_config(bringup_share)
    camera_config = load_camera_config(bringup_share)
    axis_config = load_linear_axis_config(bringup_share, 'lts300_x_axis')

    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('use_simulator', default_value='false',
                              description='Use simulated camera'),
        DeclareLaunchArgument('x_axis_port', default_value='/dev/ttyUSB0',
                              description='Serial port for X-axis'),
        DeclareLaunchArgument('x_axis_name', default_value='lts300_x_axis',
                              description='Node name for X-axis'),

        # Startup banner
        _create_startup_info(),

        # Camera driver (real hardware only)
        _create_camera_driver_node(camera_config),

        # X-axis linear stage
        _create_x_axis_node(axis_config),

        # Camera processing node (delayed start)
        TimerAction(period=2.0, actions=[
            _create_camera_node(user_config, camera_config),
            _create_verification_node(user_config)
        ]),
    ])


def _create_startup_info():
    """Create startup banner."""
    return LogInfo(msg="\n"
        "╔═══════════════════════════════════════════════════════════════════╗\n"
        "║  ProMOC Optical Measurement System                                ║\n"
        "╠═══════════════════════════════════════════════════════════════════╣\n"
        "║  Services: /camera_node/autofocus, /camera_node/measure_mtf       ║\n"
        "╚═══════════════════════════════════════════════════════════════════╝\n"
    )


def _create_camera_driver_node(camera_config: dict):
    """Create camera_aravis2 driver node."""
    return Node(
        name=camera_config.get('cameraname', 'assembly_camera'),
        namespace='promoc',
        package='camera_aravis2',
        executable='camera_driver_uv',
        output='screen',
        emulate_tty=True,
        condition=UnlessCondition(LaunchConfiguration('use_simulator')),
        parameters=[{
            'guid': camera_config.get('guid', ''),
            'frame_id': 'camera_frame',
            'stream_names': ['stream0'],
            'camera_info_urls': [os.path.join(
                get_package_share_directory('camera_aravis2'),
                'config/camera_info_example_uv.yaml')],
            'verbose': False,
            'ImageFormatControl': {
                'PixelFormat': [camera_config.get('pixel_format', 'RGB8')],
                'Width': 2448,
                'Height': 2048
            },
            'AcquisitionControl': {
                'AcquisitionFrameRateEnable': True,
                'AcquisitionFrameRate': 10.0
            }
        }]
    )


def _create_x_axis_node(axis_config: dict):
    """Create LTS300 X-axis node."""
    return Node(
        package='linear_axis_nodes',
        executable='lts300_node',
        name=LaunchConfiguration('x_axis_name'),
        output='screen',
        emulate_tty=True,
        parameters=[{
            'serial_port': LaunchConfiguration('x_axis_port'),
            'serial_number': axis_config.get('serial_number', '45456044'),
        }]
    )


def _create_camera_node(config: dict, camera_config: dict):
    """Create camera processing node with all parameters."""
    base_dir = config.get('user', {}).get('measurement_base_path') or os.path.join(
        os.path.expanduser('~'), 'Dokumente', 'Messungen'
    )
    base_dir = os.path.expanduser(str(base_dir))
    user_name = config.get('user', {}).get('name', '').strip()
    mtf_config = config.get('mtf', {})
    mtf_profile = str(mtf_config.get('profile', 'default'))
    mtf_debug_dir = str(mtf_config.get('debug_export_dir', '') or '')
    af_profile_json = json.dumps(config.get('autofocus_profiles', {}))
    return Node(
        package='camera_nodes',
        executable='camera_node',
        name='camera_node',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'measurement.username': config['user']['name'],
            'measurement.base_path': base_dir,
            'use_simulator': LaunchConfiguration('use_simulator'),
            'x_axis_node_name': LaunchConfiguration('x_axis_name'),
            'pixel_size_um': config['camera']['pixel_size_um'],
            'mtf_csv_path': '',
            'mtf.use_full_frame': True,
            'mtf.full_frame_width': camera_config.get('sensor_resolution_h', 5536),
            'mtf.full_frame_height': camera_config.get('sensor_resolution_v', 3692),
            'mtf.full_frame_offset_x': 0,
            'mtf.full_frame_offset_y': 0,
            'mtf.full_frame_binning': 1,
            'mtf.profile': mtf_profile,
            'mtf.debug_export_dir': mtf_debug_dir,
            # Debug overlay for alignment
            'enable_debug_overlay': False,
            # Autofocus parameters
            'autofocus.refinement_samples': config['autofocus']['refinement_samples'],
            'autofocus.min_step_mm': config['autofocus']['min_step_mm'],
            'autofocus.refinement_shrink_factor': config['autofocus']['refinement_shrink_factor'],
            'autofocus.profile_table_json': af_profile_json,
            'autofocus.fly_over.refinement_mode': config['fly_over']['refinement_mode'],
            'autofocus.fly_over.refinement_strategy': config['fly_over']['refinement_strategy'],
            # Measurement conditions
            'measurement_conditions.coaxial_light_voltage': config['measurement_conditions']['coaxial_light_voltage'],
            'measurement_conditions.coaxial_light_current': config['measurement_conditions']['coaxial_light_current'],
            'measurement_conditions.camera_objective': config['measurement_conditions']['camera_objective'],
            'measurement_conditions.notes': config['measurement_conditions']['notes'],
        }]
    )


def _create_verification_node(config: dict):
    """Create scientific verification node."""
    base_dir = config.get('user', {}).get('measurement_base_path') or os.path.join(
        os.path.expanduser('~'), 'Dokumente', 'Messungen'
    )
    base_dir = os.path.expanduser(str(base_dir))
    mtf_config = config.get('mtf', {})
    mtf_profile = str(mtf_config.get('profile', 'default'))
    mtf_debug_dir = str(mtf_config.get('debug_export_dir', '') or '')
    return Node(
        package='verification',
        executable='scientific_verification',
        name='scientific_verification_node',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'camera_topic': '/promoc/assembly_camera/stream0/image_raw',
            'autofocus_service': '/camera_node/autofocus',
            'axis_name': LaunchConfiguration('x_axis_name'),
            'pixel_size_um': config['camera']['pixel_size_um'],
            'results_dir': base_dir,
            'mtf.profile': mtf_profile,
            'mtf.debug_export_dir': mtf_debug_dir,
        }]
    )
