from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument

def generate_launch_description():
    return LaunchDescription([
        # Deklarieren Sie Launch-Argumente für die Seriennummern und Namen der LTS300-Geräte
        DeclareLaunchArgument(
            'lts300_serial_1',
            default_value='45318394',
            description='Seriennummer für das erste LTS300-Gerät'
        ),
        DeclareLaunchArgument(
            'lts300_serial_2',
            default_value='45318395',
            description='Seriennummer für das zweite LTS300-Gerät'
        ),
        DeclareLaunchArgument(
            'lts300_name_1',
            default_value='lts300_z_axis',
            description='Name für das erste LTS300-Gerät'
        ),
        DeclareLaunchArgument(
            'lts300_name_2',
            default_value='lts300_camera_x_axis',
            description='Name für das zweite LTS300-Gerät'
        ),
        ## Launch-Argumente für SSH-Verbindung
        DeclareLaunchArgument(
           'remote_password',
            default_value='remote_password',
            description='Passwort für die entfernte Maschine'
        ),
        DeclareLaunchArgument(
            'remote_user',
            default_value='remote_username',
            description='Benutzername für die entfernte Maschine'
        ),
        DeclareLaunchArgument(
            'remote_host',
            default_value='remote_hostname_or_ip',
            description='Hostname oder IP-Adresse der entfernten Maschine'
        ),

        # Starten Sie den mover_service_node
        Node(
            package='planar_motor_nodes',
            executable='mover_service_node',
            name='mover_service_node',
            output='screen'
        ),

        # Starten Sie die erste Instanz des lts300_service_node
        Node(
            package='linear_axis_nodes',
            executable='lts300_service_node',
            name=LaunchConfiguration('lts300_name_1'),
            parameters=[{
                'serial_number': LaunchConfiguration('lts300_serial_1'),
                'node_name': LaunchConfiguration('lts300_name_1')
            }],
            output='screen'
        ),

        # Starten Sie die zweite Instanz des lts300_service_node
        Node(
            package='linear_axis_nodes',
            executable='lts300_service_node',
            name=LaunchConfiguration('lts300_name_2'),
            parameters=[{
                'serial_number': LaunchConfiguration('lts300_serial_2'),
                'node_name': LaunchConfiguration('lts300_name_2')
            }],
            output='screen'
        ),

        # Beispiel für einen Remote-Prozess-Start (hier als Kommentar
        # aufgeführt, da es nicht auf allen Systemen funktioniert)
        '''
        # Starten Sie eine Instanz des lts300_service_node auf der entfernten Maschine
        ExecuteProcess(
            cmd=[
                'ssh',
                LaunchConfiguration('remote_user') + '@' + LaunchConfiguration('remote_host'),
                'source /opt/ros/foxy/setup.bash && ' +  # Passen Sie dies an Ihre ROS2-Version an
                'ros2 run linear_axis_nodes lts300_service_node ' +
                '--ros-args ' +
                '-p serial_number:=' + LaunchConfiguration('lts300_serial_1') + ' ' +
                '-p node_name:=' + LaunchConfiguration('lts300_name_1')
            ],
            output='screen'
        ),'''
    ])
    
