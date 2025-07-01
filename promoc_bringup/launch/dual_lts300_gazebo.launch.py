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
    namespace = LaunchConfiguration('namespace', default='promoc_assembly')
    paused = LaunchConfiguration('paused', default='false')
    verbose = LaunchConfiguration('verbose', default='false')

    # Package directories
    promoc_bringup_dir = get_package_share_directory('promoc_bringup')
    ros_distro = os.environ.get('ROS_DISTRO')

    # URDF processing - Use modular dual LTS300 system
    xacro_file = os.path.join(
        promoc_bringup_dir, 'urdf', 'assemblies', 'dual_lts300_system.urdf.xacro')

    # Process the xacro file to generate the URDF
    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)
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
        # Humble (Gazebo Classic)
        gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                os.path.join(get_package_share_directory(
                    'gazebo_ros'), 'launch', 'gazebo.launch.py')
            ]),
            launch_arguments={
                'verbose': verbose,
                'pause': paused,
                'use_sim_time': 'true'
            }.items(),
        )
        spawn_entity = Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=['-entity', 'dual_lts300_system',
                       '-topic', 'robot_description'],
            output='screen',
        )
    else:
        # Jazzy and newer (Ignition Gazebo)
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
                       '-name', 'dual_lts300_system'],
            output='screen',
        )

    # Joint State Broadcaster (start after Gazebo)
    load_joint_state_broadcaster = TimerAction(
        period=3.0,  # Wait 3 seconds after Gazebo start
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

    # Position Controllers for X and Z Axis
    load_x_position_controller = TimerAction(
        period=4.0,  # After Joint State Broadcaster
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['lts300_x_position_controller',
                           '--controller-manager', '/controller_manager'],
                output='screen',
            )
        ]
    )

    load_z_position_controller = TimerAction(
        period=4.5,  # Slightly delayed
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['lts300_z_position_controller',
                           '--controller-manager', '/controller_manager'],
                output='screen',
            )
        ]
    )

    # LTS300 X-Axis Service Node
    lts300_x_axis_node = TimerAction(
        period=6.0,  # After controller setup
        actions=[
            Node(
                package='linear_axis_nodes',
                executable='lts300_service_node',
                name='lts300_x_axis',
                namespace=namespace,
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'use_gazebo': True,  # Enable Gazebo integration
                    'debug_mode': debug_mode,
                    'x_axis_serial': 'SIM_X',  # Simulation Serial
                    'z_axis_serial': 'NONE',   # Only X-Axis
                    'serial_port': '/dev/sim_x',
                    'collision_threshold': 300.0,
                    'namespace': namespace,
                    'node_name': 'lts300_x_axis'
                }],
                output='screen',
                remappings=[
                    # Remap for consistent topic names
                    ('linear_axis_info', 'x_axis/linear_axis_info'),
                    ('move_absolute', 'x_axis/move_absolute'),
                    ('move_relative', 'x_axis/move_relative'),
                    ('home', 'x_axis/home'),
                    ('get_position', 'x_axis/get_position'),
                    ('shutdown', 'x_axis/shutdown'),
                ]
            )
        ]
    )

    # LTS300 Z-Axis Service Node
    lts300_z_axis_node = TimerAction(
        period=6.5,  # Slightly delayed after X-Axis
        actions=[
            Node(
                package='linear_axis_nodes',
                executable='lts300_service_node',
                name='lts300_z_axis',
                namespace=namespace,
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'use_gazebo': True,  # Enable Gazebo integration
                    'debug_mode': debug_mode,
                    'x_axis_serial': 'NONE',   # Only Z-Axis
                    'z_axis_serial': 'SIM_Z',  # Simulation Serial
                    'serial_port': '/dev/sim_z',
                    'collision_threshold': 300.0,
                    'namespace': namespace,
                    'node_name': 'lts300_z_axis'
                }],
                output='screen',
                remappings=[
                    # Remap for consistent topic names
                    ('linear_axis_info', 'z_axis/linear_axis_info'),
                    ('move_absolute', 'z_axis/move_absolute'),
                    ('move_relative', 'z_axis/move_relative'),
                    ('home', 'z_axis/home'),
                    ('get_position', 'z_axis/get_position'),
                    ('shutdown', 'z_axis/shutdown'),
                ]
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
        description='Enable debug output for linear axis nodes'
    )

    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace',
        default_value='promoc_assembly',
        description='Namespace for all nodes'
    )

    declare_paused_cmd = DeclareLaunchArgument(
        'paused',
        default_value='false',
        description='Start Gazebo paused'
    )

    declare_verbose_cmd = DeclareLaunchArgument(
        'verbose',
        default_value='false',
        description='Enable verbose Gazebo output'
    )

    return LaunchDescription([
        # Launch Arguments
        declare_use_sim_time_cmd,
        declare_debug_mode_cmd,
        declare_namespace_cmd,
        declare_paused_cmd,
        declare_verbose_cmd,

        # Core Simulation
        gazebo,
        robot_state_publisher_node,
        spawn_entity,

        # Controllers (with timing)
        load_joint_state_broadcaster,
        load_x_position_controller,
        load_z_position_controller,

        # LTS300 Service Nodes (with timing)
        lts300_x_axis_node,
        lts300_z_axis_node,
    ])
