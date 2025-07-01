#!/usr/bin/env python3

import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    debug_mode = LaunchConfiguration('debug_mode', default='true')
    test_axis = LaunchConfiguration('test_axis', default='x')  # x or z

    # Package directories
    promoc_bringup_dir = get_package_share_directory('promoc_bringup')
    ros_distro = os.environ.get('ROS_DISTRO')

    # URDF processing - Use test single axis
    xacro_file = os.path.join(
        promoc_bringup_dir, 'urdf', 'assemblies', 'test_single_axis.urdf.xacro')

    # Process the xacro file with test_axis argument
    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc, mappings={'test_axis': test_axis})
    robot_description_config = doc.toxml()

    # Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_config,
            'use_sim_time': use_sim_time
        }],
    )

    # Gazebo Launch (ROS distro specific)
    if ros_distro == 'humble':
        gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                os.path.join(get_package_share_directory(
                    'gazebo_ros'), 'launch', 'gazebo.launch.py')
            ]),
            launch_arguments={'use_sim_time': 'true'}.items(),
        )
        spawn_entity = Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=['-entity', 'test_single_axis',
                       '-topic', 'robot_description'],
            output='screen',
        )
    else:
        gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(get_package_share_directory(
                    'ros_gz_sim'), 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={'gz_args': '-r -v 4 empty.sdf'}.items()
        )
        spawn_entity = Node(
            package='ros_gz_sim',
            executable='create',
            arguments=['-topic', 'robot_description',
                       '-name', 'test_single_axis'],
            output='screen',
        )

    # Joint State Broadcaster
    load_joint_state_broadcaster = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['joint_state_broadcaster',
                           '--controller-manager', '/controller_manager'],
                output='screen',
            )
        ]
    )

    # Conditional controller loading based on test_axis
    load_controller = TimerAction(
        period=4.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[f'test_lts300_{test_axis}_position_controller',
                           '--controller-manager', '/controller_manager'],
                output='screen',
            )
        ]
    )

    # Launch Arguments
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    declare_debug_mode_cmd = DeclareLaunchArgument(
        'debug_mode',
        default_value='true',
        description='Enable debug output'
    )

    declare_test_axis_cmd = DeclareLaunchArgument(
        'test_axis',
        default_value='x',
        description='Which axis to test: x or z'
    )

    return LaunchDescription([
        # Launch Arguments
        declare_use_sim_time_cmd,
        declare_debug_mode_cmd,
        declare_test_axis_cmd,

        # Core Simulation
        gazebo,
        robot_state_publisher_node,
        spawn_entity,

        # Controllers
        load_joint_state_broadcaster,
        load_controller,
    ])
