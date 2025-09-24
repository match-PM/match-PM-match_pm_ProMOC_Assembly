#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Your camera manager (subscribes to camera_aravis2 topics)
        Node(
            package='camera_nodes',
            executable='camera_manager',
            name='camera_manager',
            output='screen',
        ),
        
        # Assembly Camera (via camera_aravis2) - EXTERNAL PACKAGE
        Node(
            package='camera_aravis2',  # External package - no direct import needed!
            executable='camera_driver_gv',
            name='assembly_camera',
            parameters=[{
                'guid': 'YOUR_ASSEMBLY_CAMERA_SERIAL',  # Replace with actual camera serial
                'frame_id': 'assembly_camera_frame',
                'ImageFormatControl': {
                    'PixelFormat': 'BayerRG8',
                    'Width': 1920,
                    'Height': 1080,
                },
                'AcquisitionControl': {
                    'AcquisitionMode': 'Continuous',
                    'AcquisitionFrameRate': 30.0,
                    'ExposureTime': 10000.0,
                },
            }],
            remappings=[
                ('image', 'assembly_camera/image_raw'),      # Output topic
                ('camera_info', 'assembly_camera/camera_info'),
            ]
        ),
        
        # Inspection Camera (if you have a second camera)
        # Node(
        #     package='camera_aravis2',
        #     executable='camera_driver_gv',
        #     name='inspection_camera',
        #     parameters=[{
        #         'guid': 'YOUR_INSPECTION_CAMERA_SERIAL',
        #         'frame_id': 'inspection_camera_frame',
        #     }],
        #     remappings=[
        #         ('image', 'inspection_camera/image_raw'),
        #         ('camera_info', 'inspection_camera/camera_info'),
        #     ]
        # ),
    ])