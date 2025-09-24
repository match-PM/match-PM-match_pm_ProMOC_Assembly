import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """Launch file to run the camera controller with the real camera driver."""

    config_file = os.path.join(
        get_package_share_directory('promoc_bringup'),
        'config',
        'camera_node_params.yaml'
    )

    return LaunchDescription([
        # Your camera controller, loading parameters from YAML
        Node(
            package='camera_nodes',
            executable='camera_node',
            name='camera_node',
            output='screen',
            # Load parameters from YAML and override 'use_simulator' to be False
            parameters=[config_file, {'use_simulator': False}],
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
    ])
