from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch.actions import SetEnvironmentVariable
import os

def generate_launch_description():
    # Declare launch arguments
    lts300_serial_1_arg = DeclareLaunchArgument(
        'lts300_serial_1',
        default_value='45318394',
        description='Seriennummer für das erste LTS300-Gerät'
    )
    lts300_serial_2_arg = DeclareLaunchArgument(
        'lts300_serial_2',
        default_value='45318395',
        description='Seriennummer für das zweite LTS300-Gerät'
    )
    lts300_name_1_arg = DeclareLaunchArgument(
        'lts300_name_1',
        default_value='lts300_z_axis',
        description='Name für das erste LTS300-Gerät'
    )
    lts300_name_2_arg = DeclareLaunchArgument(
        'lts300_name_2',
        default_value='lts300_camera_x_axis',
        description='Name für das zweite LTS300-Gerät'
    )
    remote_password_arg = DeclareLaunchArgument(
        'remote_password',
        default_value='MaTch897M+v',
        description='Passwort für die entfernte Maschine'
    )
    remote_user_arg = DeclareLaunchArgument(
        'remote_user',
        default_value='admin',
        description='Benutzername für die entfernte Maschine'
    )
    remote_host_arg = DeclareLaunchArgument(
        'remote_host',
        default_value='10.145.4.63',
        description='Hostname oder IP-Adresse der entfernten Maschine'
    )

    # Function to construct the SSH command
    def launch_remote_node(context):
        remote_user = LaunchConfiguration('remote_user').perform(context)
        remote_host = LaunchConfiguration('remote_host').perform(context)
        lts300_serial_1 = LaunchConfiguration('lts300_serial_1').perform(context)
        lts300_name_1 = LaunchConfiguration('lts300_name_1').perform(context)

        ssh_command = [
            'ssh',
            '-t',
            f'{remote_user}@{remote_host}',
            f'cmd.exe /c "cd C:\\\\Users\\\\admin\\\\promoc_ros2_ws && '
            f'call C:\\\\dev\\\\ros2_jazzy\\\\setup.bat && '
            f'call C:\\\\Users\\\\admin\\\\promoc_ros2_ws\\\\install\\\\setup.bat && '
            f'set ROS_DOMAIN_ID=13 && '
            f'ros2 run linear_axis_nodes lts300_service_node '
            f'--ros-args '
            f'-p serial_number:={lts300_serial_1} '
            f'-p node_name:={lts300_name_1}"'
        ]
        return [ExecuteProcess(cmd=ssh_command, output='screen')]

    # Create the launch description
    ld = LaunchDescription([
        SetEnvironmentVariable('PYTHONPATH', os.path.dirname(os.path.abspath(__file__)) + ':' + os.environ.get('PYTHONPATH', '')),
        lts300_serial_1_arg,
        lts300_serial_2_arg,
        lts300_name_1_arg,
        lts300_name_2_arg,
        remote_password_arg,
        remote_user_arg,
        remote_host_arg,
        # Start the mover_service_node
        Node(
            package='planar_motor_nodes',
            executable='mover_service_node',
            name='mover_service_node',
            output='screen'
        ),
        # Start the remote node using OpaqueFunction
        OpaqueFunction(function=launch_remote_node)
    ])

    return ld
