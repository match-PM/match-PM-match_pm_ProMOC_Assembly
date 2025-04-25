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

        print(f"Suche Konfigurationsdatei in: {config_file}")

        if not os.path.exists(config_file):
            # Versuche, die Datei direkt aus dem Quellverzeichnis zu laden
            src_config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config', 'promoc_assembly_params.yaml')
            print(f"Konfigurationsdatei nicht im installierten Paket gefunden. Versuche: {src_config_file}")
            
            if os.path.exists(src_config_file):
                config_file = src_config_file
            else:
                raise FileNotFoundError(
                    f"Konfigurationsdatei nicht gefunden: {config_file} oder {src_config_file}")

        print(f"Lade Konfigurationsdatei: {config_file}")
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

def get_password_from_file():
    """Read password from credentials file."""
    try:
        credentials_file = os.path.expanduser('~/.ssh_credentials')
        print(f"Lese SSH-Anmeldeinformationen aus: {credentials_file}")
        
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(f"SSH-Anmeldeinformationsdatei nicht gefunden: {credentials_file}")
            
        with open(credentials_file, 'r') as f:
            remote_password = f.read().strip()
            if not remote_password:
                raise ValueError("SSH-Anmeldeinformationsdatei ist leer")
            return remote_password
    except Exception as e:
        print(f'Fehler beim Lesen der SSH-Anmeldeinformationen: {e}')
        raise RuntimeError(f'Fehler beim Lesen der SSH-Anmeldeinformationen: {e}')


def create_ssh_command(remote_user, remote_host, ros_domain_id, executable, serial_number, node_name, namespace):
    """Create the SSH Command for the Remote Node."""
    try:
        remote_password = get_password_from_file()
        
        return [
            'sshpass',
            '-p',
            remote_password,
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-t',
            f"{remote_user}@{remote_host}",
            f'cmd.exe /c "cd C:\\\\Users\\\\admin\\\\promoc_ros2_ws && '
            f'call C:\\\\dev\\\\ros2_jazzy\\\\setup.bat && '
            f'call C:\\\\Users\\\\admin\\\\promoc_ros2_ws\\\\install\\\\setup.bat && '
            f'set ROS_DOMAIN_ID={ros_domain_id} && '
            f'ros2 run linear_axis_nodes {executable} '
            f'--ros-args -p serial_number:=\\"{serial_number}\\" '
            f'-p node_name:={node_name} '
            f'-r __ns:=/{namespace}"'
        ]
        
    except Exception as e:
        print(f"Fehler beim Erstellen des SSH-Befehls: {e}")
        return None


def generate_launch_description():
    """Generate the launch description for the promoc assembly."""
    # load the parameters from promoc_assembly_params.yaml
    config = load_yaml_config()
    
    if config is None:
        print("Fehler: Konfiguration konnte nicht geladen werden.")
        # Wir müssen eine leere LaunchDescription zurückgeben, um einen Fehler zu vermeiden
        return LaunchDescription([])

    try:
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
            SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp'),
            SetEnvironmentVariable('CYCLONEDDS_URI', f'file://{os.path.expanduser("~/Dokumente/cyclonedds_config/cyclonedds.xml")}'),

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
        if 'lts300_devices' in config and config['lts300_devices']:
            for device_name, device_data in config['lts300_devices'].items():
                try:
                    # Überprüfe, ob alle erforderlichen Schlüssel für das Gerät vorhanden sind
                    if 'executable' not in device_data:
                        print(f"Warnung: 'executable' fehlt für Gerät {device_name}, überspringe...")
                        continue
                    if 'serial_number' not in device_data:
                        print(f"Warnung: 'serial_number' fehlt für Gerät {device_name}, überspringe...")
                        continue
                    if 'node_name' not in device_data:
                        print(f"Warnung: 'node_name' fehlt für Gerät {device_name}, überspringe...")
                        continue
                        
                    ssh_command = create_ssh_command(
                        remote_user,
                        remote_host,
                        ros_domain_id,
                        device_data['executable'],
                        device_data['serial_number'],
                        device_data['node_name'],
                        namespace
                    )

                    if ssh_command:
                        ld.add_action(ExecuteProcess(cmd=ssh_command, output='screen'))
                except Exception as e:
                    print(f"Fehler beim Hinzufügen des Geräts {device_name}: {e}")
        else:
            print("Warnung: Keine LTS300-Geräte in der Konfiguration gefunden.")

        return ld
    except Exception as e:
        print(f"Fehler beim Generieren der Launch-Beschreibung: {e}")
        return LaunchDescription([])


# TODO # DDS überarbeiten
    # Node für die Kamerachse ready machen
    # Code aufräumen
    
