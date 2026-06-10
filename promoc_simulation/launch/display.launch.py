import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():

    # Argument, um die Verwendung der GUI zu steuern
    use_joint_state_publisher_gui = DeclareLaunchArgument(
        'use_gui',
        default_value='true',
        description='Whether to use the joint_state_publisher_gui')

    # Argument für RViz
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='Whether to start RViz2')

    # Pfad zur Xacro-Datei finden
    xacro_file = os.path.join(
        get_package_share_directory('promoc_simulation'),
        'urdf',
        'promoc.xacro'
    )

    # Xacro verarbeiten, um die URDF-XML zu erhalten
    robot_description_raw = xacro.process_file(xacro_file).toxml()

    # Node für den robot_state_publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_raw}]
    )

    # Node für den joint_state_publisher_gui
    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        condition=IfCondition(LaunchConfiguration('use_gui'))
    )

    # Node für RViz2 (nur wenn use_rviz=true)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_rviz')),
        arguments=['-d', os.path.join(
            get_package_share_directory('promoc_simulation'),
            'rviz',
            'display.rviz'
        )]
    )

    return LaunchDescription([
        use_joint_state_publisher_gui,
        use_rviz_arg,
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node
    ])
