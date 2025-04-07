from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess
from launch.actions import SetEnvironmentVariable
from ament_index_python.packages import get_package_share_directory
import os
import yaml


def load_yaml_config():
    """Load the promoc_assembly_params.yaml."""
    try:
        config_dir = os.path.join(
            get_package_share_directory('promoc_bringup'), 'config')
        config_file = os.path.join(config_dir, 'promoc_assembly_params.yaml')

        if not os.path.exists(config_file):
            raise FileNotFoundError(
                f"Konfigurationsdatei nicht gefunden: {config_file}")

        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)

        # Validiere die Konfiguration
        if 'lts300_devices' not in config or 'remote_connection' not in config:
            raise ValueError(
                "Konfigurationsdatei fehlen erforderliche Abschnitte")

        return config
    except Exception as e:
        print(f"Fehler beim Laden der Konfiguration: {e}")
        return None


def create_ssh_command(remote_user, remote_host, ros_domain_id, executable, serial_number, node_name, namespace):
    """Create the SSH Command for the Remote Node."""
    return [
        'ssh',
        '-t',
        f"{remote_user}@{remote_host}",
        f'cmd.exe /c "cd C:\\\\Users\\\\admin\\\\promoc_ros2_ws && '
        f'call C:\\\\dev\\\\ros2_jazzy\\\\setup.bat && '
        f'call C:\\\\Users\\\\admin\\\\promoc_ros2_ws\\\\install\\\\setup.bat && '
        f'set ROS_DOMAIN_ID={ros_domain_id} && '
        f'ros2 run linear_axis_nodes {executable} '
        f'--ros-args -p serial_number:={serial_number} '
        f'-p node_name:={node_name}"'
        f'--ros-args -r __ns:=/{namespace}"'
    ]


def generate_launch_description():
    # load the parameters from promoc_assembly_params.yaml
    config = load_yaml_config()

    # extracte the remote connection parameters
    remote_user = config['remote_connection']['user']
    remote_host = config['remote_connection']['host']
    ros_domain_id = config['remote_connection']['ros_domain_id']
    namespace = config.get('namespace', 'promoc_assembly')
    # Create a launch description for the local node
    ld = LaunchDescription([
        SetEnvironmentVariable('PYTHONPATH', os.path.dirname(
            os.path.abspath(__file__)) + ':' + os.environ.get('PYTHONPATH', '')),
        SetEnvironmentVariable('ROS_DOMAIN_ID', ros_domain_id),


        # Start the mover_service_node
        Node(
            package='planar_motor_nodes',
            executable='mover_service_node',
            namespace=namespace,
            name='mover_service_node',
            output='screen'
        )
    ])

    # Add the amount of LTS300 devices that have parameters in the yaml via remote ssh-access
    for device_data in config['lts300_devices'].values():
        ssh_command = create_ssh_command(
            remote_user,
            remote_host,
            ros_domain_id,
            device_data['executable'],
            device_data['serial_number'],
            device_data['node_name'],
            namespace

        )

        ld.add_action(ExecuteProcess(cmd=ssh_command, output='screen'))

    return ld


# TODO ssh Verbindung überarbeiten sodass sie ohne passwort funktioniert
    # Node für die Kamerachse ready machen
    # Code aufräumen
    # DDS überarbeiten
