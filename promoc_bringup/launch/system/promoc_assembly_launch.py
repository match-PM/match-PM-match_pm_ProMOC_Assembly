import os
import re
import yaml
import glob
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def load_mover_config(bringup_pkg_share):
    print("\nPreparing static nodes to launch:")
    mover_params_path = os.path.join(bringup_pkg_share, 'config', 'mover_node_params.yaml')

    if os.path.exists(mover_params_path):
        mover_node = Node(
            package='planar_motor_nodes',
            executable='mover_node',
            name='mover_node',
            parameters=[mover_params_path],
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        )
        print(" mover_node' prepared.")
        return mover_node
    else:
        print(f" mover_node' config not found at {mover_params_path}")
        return None
    

def load_axes_config():
    """
    Loads the axes configuration from the 'linear_axes_params.yaml' file located in the 'config' directory
    of the 'promoc_bringup' package.
    Returns:
        tuple:
            - dict: The loaded axes configuration as a dictionary. Returns an empty dictionary if loading fails.
            - str or None: The path to the configuration file. Returns None if loading fails.
    Raises:
        Prints an error message if the configuration file cannot be read or parsed.
    """

    try:
        pkg_share = get_package_share_directory('promoc_bringup') # Adjust the package name if necessary
        config_file_path = os.path.join(pkg_share, 'config', 'linear_axes_params.yaml')
        with open(config_file_path, 'r') as file:
            # Load the entire content of the YAML file
            config = yaml.safe_load(file)
        
        # The configuration is the entire file, not just a part of it
        known_axes = config if config is not None else {}
        print(f"✅ Configuration loaded for nodes: {list(known_axes.keys())}")
        # We also return the path since we need it later
        return known_axes, config_file_path
    except (IOError, yaml.YAMLError) as e:
        print(f"❌ Error loading configuration: {e}")
        return {}, None

def discover_connected_devices():
    """
    Discover Thorlabs APT stepper motor controllers connected under /dev/serial/by-id.
    Scans the /dev/serial/by-id directory for symlinks matching the pattern
    'usb-Thorlabs_APT_Stepper_Motor_Controller_*'. For each matching filename the
    function attempts to extract a numeric serial with the regular expression
    r'usb-Thorlabs_APT_Stepper_Motor_Controller_([0-9]+)' and builds a mapping from
    that serial (string) to the corresponding stable device path (the symlink).
    Side effects:
    - Prints progress and diagnostic messages to stdout:
        - start of scan,
        - each detected device and its serial,
        - warnings for unrecognized filename formats,
        - errors encountered while processing specific paths,
        - a final summary of the number of devices found.
    Returns:
            dict[str, str]: Mapping of device serial number (as a string) to the
            stable device symlink path under /dev/serial/by-id. If no devices are
            found an empty dict is returned.
    Notes:
    - Exceptions raised while processing individual device paths are caught and
        logged; they do not abort the overall scan.
    - The returned paths are stable device identifiers (symlinks) which are
        preferred over dynamic /dev/tty* names.
    - Example return value:
            {'12345678': '/dev/serial/by-id/usb-Thorlabs_APT_Stepper_Motor_Controller_12345678'}
    """
    port_map = {}
    print("🛰️  Scanning for connected devices in /dev/serial/by-id/...")
    search_pattern = '/dev/serial/by-id/usb-Thorlabs_APT_Stepper_Motor_Controller_*'
    
    for device_path in glob.glob(search_pattern):
        try:
            filename = os.path.basename(device_path)
            match = re.search(r'usb-Thorlabs_APT_Stepper_Motor_Controller_([0-9]+)', filename)

            if match:
                serial = match.group(1)
                port_map[serial] = device_path
                print(f"  -> Detected device: {filename} (serial: {serial}) -> using stable path {device_path}")
            else:
                print(f"  ⚠️  Unrecognized device filename format: {filename}")

        except Exception as e:
            print(f"  ⚠️  Error processing {device_path}: {e}")
            continue
            
    if port_map:
        print(f"  -> Found {len(port_map)} device(s).")
    else:
        print("  -> No devices found.")
    return port_map

def generate_launch_description():
    
    known_axes_config, axes_config_path = load_axes_config()
    connected_devices = discover_connected_devices()
    
    bringup_pkg_share = get_package_share_directory('promoc_bringup')
    launch_actions = []

    # Load mover configuration
    mover_node = load_mover_config(bringup_pkg_share)
    if mover_node:
        launch_actions.append(mover_node)

    known_axes_config, axes_config_path = load_axes_config()
    if axes_config_path:
        connected_devices = discover_connected_devices()
        print("\n🛰️  Matching connected devices to launch dynamic nodes:")
        for node_name, node_params in known_axes_config.items():
            try:
                target_serial = node_params['ros__parameters']['serial_number']
                if target_serial in connected_devices:
                    stable_device_path = connected_devices[target_serial]
                    print(f"  ✅ '{node_name}' is connected. Creating node.")
                    axis_node = Node(
                        package='linear_axis_nodes',
                        executable='lts300_node',
                        name=node_name,
                        parameters=[
                            axes_config_path,
                            {'serial_port': stable_device_path}
                        ],
                        output='screen',
                        arguments=['--ros-args', '--log-level', 'INFO']
                    )
                    launch_actions.append(axis_node)
                else:
                    print(f"  ❌ '{node_name}' is configured but not connected.")
            except KeyError:
                print(f"  ⚠️  Skipping '{node_name}', 'serial_number' not found.")
                continue

    return LaunchDescription(launch_actions)