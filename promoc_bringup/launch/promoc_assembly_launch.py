from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os
import yaml

def load_yaml_config():
    """
    Load YAML configuration file for ProMOC assembly.

    This function attempts to load a YAML configuration file from a predefined location.
    If the file is not found in the expected directory, it tries an alternative location.
    If the file is not found in either location, it raises a FileNotFoundError.

    Returns:
        dict: A dictionary containing the configuration parameters loaded from the YAML file.
              Returns None if an error occurs during the loading process.

    Raises:
        FileNotFoundError: If the configuration file is not found in either of the expected locations.
        Exception: For any other error that occurs during the file loading or parsing process.
    """
    try:
        config_dir = os.path.join(get_package_share_directory('promoc_bringup'), 'config')
        config_file = os.path.join(config_dir, 'promoc_assembly_params.yaml')

        if not os.path.exists(config_file):
            src_config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config', 'promoc_assembly_params.yaml')
            
            if os.path.exists(src_config_file):
                config_file = src_config_file
            else:
                raise FileNotFoundError(f"Configuration file not found: {config_file} or {src_config_file}")

        with open(config_file, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

def create_mover_node(namespace, device_data):
    move_area_params = device_data.get('move_area_parameters', {})
    return Node(
        package=device_data['package'],
        executable=device_data['executable'],
        namespace=namespace,
        name=device_data['node_name'],
        parameters=[
            {'node_name': device_data['node_name']},
            {'x_min': move_area_params.get('x_min', 0.055)},
            {'x_max': move_area_params.get('x_max', 0.420)},
            {'y_min': move_area_params.get('y_min', -0.055)},
            {'y_max': move_area_params.get('y_max', 0.180)},
            {'z_min': move_area_params.get('z_min', 0.000)},
            {'z_max': move_area_params.get('z_max', 0.004)},
        ],
        output='screen'
    )

def create_lts300_node(namespace, device_data, total_devices):
    required_keys = ['package', 'executable', 'serial_number', 'node_name', 'serial_port']
    if not all(key in device_data for key in required_keys):
        print(f"Warning: Missing required parameters for device {device_data.get('node_name', 'unknown')}, skipping...")
        return None

    parameters = [
        {'serial_number': device_data['serial_number']},
        {'serial_port': device_data['serial_port']},
        {'node_name': device_data['node_name']},
        {'number_of_axes': total_devices}
    ]

    # Liste der zusätzlichen Parameter, die wir überprüfen wollen
    additional_params = ['collision_threshold', 'device_units_per_mm']

    # Überprüfen Sie jeden zusätzlichen Parameter
    for param in additional_params:
        if param in device_data.get('parameters', {}):
            parameters.append({param: device_data['parameters'][param]})

    return Node(
        package=device_data['package'],
        executable=device_data['executable'],
        namespace=namespace,
        name=device_data['node_name'],
        parameters=parameters,
        output='screen'
    )


def generate_launch_description():
    promoc_assembly_params = load_yaml_config()
    if promoc_assembly_params is None:
        print("Error: Configuration could not be loaded.")
        return LaunchDescription([])
    
    print("Loaded configuration:", promoc_assembly_params)

    namespace = promoc_assembly_params.get('namespace', 'promoc_assembly')
    nodes = []

    
    mover_data = promoc_assembly_params.get('mover_node', {})
    if isinstance(mover_data, dict) and all(key in mover_data for key in ['package', 'executable', 'node_name']):
        mover_node = create_mover_node(namespace, mover_data)
        nodes.append(mover_node)
    else:
        print("Warning: Invalid or missing data for mover node")

    # Create and add LTS300 nodes
    lts300_devices = promoc_assembly_params.get('lts300_devices', {})
    for device_name, device_data in lts300_devices.items():
        lts300_node = create_lts300_node(namespace, device_data, len(lts300_devices))
        if lts300_node:
            nodes.append(lts300_node)

    print(f"Total number of LTS300 devices: {len(lts300_devices)}")
    print(f"Total number of nodes: {len(nodes)}")

    return LaunchDescription(nodes)