from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    bringup_dir = get_package_share_directory('promoc_bringup')
    config_dir = os.path.join(bringup_dir, 'config')
    params_file = os.path.join(config_dir, 'mover_node_params.yaml')

    mover_node = Node(
        package='planar_motor_nodes',
        executable='mover_node',
        name='mover_node',
        parameters=[params_file],
        output='screen',
        arguments=['--ros-args', '--log-level', 'INFO']
    )

    demo_controller = Node(
        package='promoc_bringup',
        executable='unified_demo',
        name='demo_controller',
        parameters=[{'demo_mode': 'planar_motor', 'xbot_id': 1}],
        output='screen',
        arguments=['--ros-args', '--log-level', 'INFO']
    )

    demo_delayed = TimerAction(
        period=5.0,
        actions=[demo_controller]
    )

    return LaunchDescription([
        mover_node,
        demo_delayed
    ])
