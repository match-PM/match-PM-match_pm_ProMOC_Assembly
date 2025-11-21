import os
import re
import glob
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import launch

def discover_connected_devices():
    """
    Discover Thorlabs APT stepper motor controllers connected under /dev/serial/by-id.
    Returns a map of serial number to device path.
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

def load_axes_config(bringup_pkg_share):
    """Loads the axes configuration."""
    config_file_path = os.path.join(bringup_pkg_share, 'config', 'linear_axes_params.yaml')
    try:
        with open(config_file_path, 'r') as file:
            config = yaml.safe_load(file)
        return config, config_file_path
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return {}, None

def generate_launch_description():
    """
    Consolidated system launch file.
    Launches:
    - Camera (via camera.launch.py)
    - Mover Node
    - Linear Axis Nodes (Hardware or Simulation)
    """
    
    sim_mode_arg = DeclareLaunchArgument(
        'sim_mode',
        default_value='false',
        description='Run in simulation mode'
    )

    return LaunchDescription([
        sim_mode_arg,
        OpaqueFunction(function=launch_setup)
    ])

def launch_setup(context, *args, **kwargs):
    sim_mode = LaunchConfiguration('sim_mode').perform(context).lower() == 'true'
    launch_actions = []
    
    bringup_pkg_share = get_package_share_directory('promoc_bringup')
    
    # 1. Launch Camera
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_pkg_share, 'launch', 'camera.launch.py')
        ),
        launch_arguments={'sim_mode': str(sim_mode).lower()}.items()
    )
    launch_actions.append(camera_launch)
    
    # 2. Launch Mover Node
    mover_params_path = os.path.join(bringup_pkg_share, 'config', 'mover_node_params.yaml')
    if os.path.exists(mover_params_path):
        launch_actions.append(Node(
            package='planar_motor_nodes',
            executable='mover_node',
            name='mover_node',
            parameters=[mover_params_path],
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        ))
    else:
        launch.logging.get_logger().error(f"mover_node config not found at {mover_params_path}")

    # 3. Launch Linear Axes
    axes_config, axes_config_path = load_axes_config(bringup_pkg_share)
    
    if axes_config:
        if sim_mode:
            launch.logging.get_logger().info("🚀 Launching Linear Axes in SIMULATION mode")
            # Launch all defined axes in simulation mode
            for node_name in axes_config.keys():
                launch_actions.append(Node(
                    package='linear_axis_nodes',
                    executable='lts300_node',
                    name=node_name,
                    parameters=[
                        axes_config_path,
                        {'use_sim_time': True}
                    ],
                    output='screen',
                    arguments=['--ros-args', '--log-level', 'INFO']
                ))
        else:
            launch.logging.get_logger().info("⚙️ Launching Linear Axes in HARDWARE mode")
            connected_devices = discover_connected_devices()
            
            for node_name, node_params in axes_config.items():
                try:
                    target_serial = node_params['ros__parameters']['serial_number']
                    if target_serial in connected_devices:
                        stable_device_path = connected_devices[target_serial]
                        launch.logging.get_logger().info(f"  ✅ '{node_name}' is connected. Creating node.")
                        launch_actions.append(Node(
                            package='linear_axis_nodes',
                            executable='lts300_node',
                            name=node_name,
                            parameters=[
                                axes_config_path,
                                {'serial_port': stable_device_path, 'use_sim_time': False}
                            ],
                            output='screen',
                            arguments=['--ros-args', '--log-level', 'INFO']
                        ))
                    else:
                        launch.logging.get_logger().warn(f"  ❌ '{node_name}' (S/N: {target_serial}) is configured but not connected.")
                except KeyError:
                    launch.logging.get_logger().warn(f"  ⚠️  Skipping '{node_name}', 'serial_number' not found.")
                    continue

    return launch_actions
