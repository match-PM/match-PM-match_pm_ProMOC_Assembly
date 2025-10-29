import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    
    # Declare the use_sim_time argument
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    # Get the path to the linear axes parameters file
    linear_axes_params_path = os.path.join(
        get_package_share_directory('promoc_bringup'),
        'config',
        'linear_axes_params.yaml'
    )

    # Get the path to the camera node parameters file
    camera_node_params_path = os.path.join(
        get_package_share_directory('promoc_bringup'),
        'config',
        'camera_node_params.yaml'
    )

    return LaunchDescription([
        use_sim_time_arg,

        # Launch the linear axis node in simulation mode
        Node(
            package='linear_axis_nodes',
            executable='lts300_node',
            name='lts300_x_axis',
            parameters=[
                linear_axes_params_path,
                {'use_sim_time': LaunchConfiguration('use_sim_time')}
            ],
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        ),

        # Launch the camera simulator
        Node(
            package='camera_nodes',
            executable='camera_simulator',
            name='camera_simulator',
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        ),

        # Launch the camera node
        Node(
            package='camera_nodes',
            executable='camera_node',
            name='camera_node',
            parameters=[
                camera_node_params_path,
                {'use_sim_time': LaunchConfiguration('use_sim_time')}
            ],
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        ),
    ])
