import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():

    bringup_pkg_share = get_package_share_directory('promoc_bringup')

    # --- 1. Start base system (mover + dynamic joints) ---
    # We include the consolidated system launch file.
    base_system_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                bringup_pkg_share,
                'launch',
                'system.launch.py'
            )
        )
    )
    # --- 2. Prepare demo controller node ---
    demo_controller_params_path = os.path.join(
        bringup_pkg_share, 'config', 'demo_controller_params.yaml'
    )

    demo_controller_node = Node(
        package='promoc_bringup',
        executable='unified_demo',
        name='demo_controller',
        parameters=[demo_controller_params_path, {'demo_mode': 'full'}],
        output='screen',
        arguments=['--ros-args', '--log-level', 'INFO']
    )

    # --- 3. Return everything ---
    return LaunchDescription([
        base_system_launch,
        demo_controller_node
    ])
