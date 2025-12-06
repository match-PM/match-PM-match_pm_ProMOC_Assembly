# ProMOC Assembly Camera Launch File
import os
from ament_index_python import get_package_share_directory
import launch
from launch_ros.actions import Node

os.environ['RCUTILS_CONSOLE_OUTPUT_FORMAT'] = '{time}: [{name}] [{severity}]\t{message}'


def generate_launch_description():

    camera_node = Node(
        name='assembly_camera',
        namespace='promoc',
        package='camera_aravis2',
        executable='camera_driver_uv',
        output='screen',
        emulate_tty=True,
        parameters=[
            {
                # Driver-specific parameters
                'guid': 'IDS Imaging Development Systems GmbH-1409f4a43375-4104401781',
                'frame_id': 'camera_frame',
                'stream_names': ['stream0'],
                'camera_info_urls': [os.path.join(
                    get_package_share_directory('camera_aravis2'),
                    'config/camera_info_example_uv.yaml')],
                'verbose': False,

                # GenICam-specific parameters
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
    return launch.LaunchDescription([camera_node])
