from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Parameter-Datei
    bringup_dir = get_package_share_directory('promoc_bringup')
    config_dir = os.path.join(bringup_dir, 'config')
    params_file = os.path.join(config_dir, 'promoc_assembly_params.yaml')

    # Log-Level Argument
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Set log level (debug, info, warn, error)'
    )

    # Nodes direkt erstellen (wie in Demo)
    mover_node = Node(
        package='planar_motor_nodes',
        executable='mover_service_node',
        name='mover_node',
        parameters=[params_file],
        arguments=['--log-level', LaunchConfiguration('log_level')],
        output='screen'
    )

    lts300_z_axis_node = Node(
        package='linear_axis_nodes',
        executable='lts300_service_node',
        name='lts300_z_axis',
        parameters=[params_file],
        arguments=['--log-level', LaunchConfiguration('log_level')],
        output='screen'
    )

    lts300_x_axis_node = Node(
        package='linear_axis_nodes',
        executable='lts300_service_node',
        name='lts300_x_axis',
        parameters=[params_file],
        arguments=['--log-level', LaunchConfiguration('log_level')],
        output='screen'
    )

    return LaunchDescription([
        log_level_arg,
        mover_node,
        lts300_z_axis_node,
        lts300_x_axis_node
    ])