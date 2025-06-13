from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Get the launch directory
    bringup_dir = get_package_share_directory('promoc_bringup')
    config_dir = os.path.join(bringup_dir, 'config')
    params_file = os.path.join(config_dir, 'promoc_assembly_params.yaml')

    # Hardware Nodes
    mover_node = Node(
        package='planar_motor_nodes',
        executable='mover_service_node',
        name='mover_node',
        parameters=[params_file],
        output='screen'
    )

    lts300_z_axis_node = Node(
        package='linear_axis_nodes',
        executable='lts300_service_node',
        name='lts300_z_axis',
        parameters=[params_file],
        output='screen'
    )

    lts300_x_axis_node = Node(
        package='linear_axis_nodes',
        executable='lts300_service_node',
        name='lts300_x_axis',
        parameters=[params_file],
        output='screen'
    )

    # Demo Controller Node
    demo_controller = Node(
        package='promoc_bringup',
        executable='demo_controller.py',  
        name='demo_controller',
        output='screen'
    )

    # Starte Demo Controller mit Verzögerung (5 Sekunden)
    demo_delayed = TimerAction(
        period=5.0,
        actions=[demo_controller]
    )

    return LaunchDescription([
        mover_node,
        lts300_z_axis_node,
        lts300_x_axis_node,
        demo_delayed
    ])
