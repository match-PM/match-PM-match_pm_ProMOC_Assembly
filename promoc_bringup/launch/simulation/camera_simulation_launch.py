import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """Launch file to run the camera controller with a simulated camera."""
    
    config_file = os.path.join(
        get_package_share_directory('promoc_bringup'),
        'config',
        'camera_node_params.yaml'
    )

    return LaunchDescription([
        # Node to simulate the camera feed
        Node(
            package='camera_nodes',
            executable='camera_simulator',
            name='camera_simulator',
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        ),
        
        # The camera controller node that we want to test
        Node(
            package='camera_nodes',
            executable='camera_node',
            name='camera_node',
            output='screen',
            parameters=[config_file],
            arguments=['--ros-args', '--log-level', 'INFO']
        ),
    ])