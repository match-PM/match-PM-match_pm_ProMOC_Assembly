"""
System launch file for ProMOC Assembly

Starts the complete ProMOC system:
- Camera (via camera.launch.py)
- Planar motor (mover_node)
- Linear axes (automatic hardware detection)

Usage:
    ros2 launch promoc_bringup system.launch.py
    ros2 launch promoc_bringup system.launch.py sim_mode:=true

Automatically detects connected Thorlabs linear axes and launches
only nodes for available hardware.
"""

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


# =============================================================================
# Helper Functions
# =============================================================================

# Use shared helper from launch_utils
from promoc_bringup.launch_utils import discover_thorlabs_devices as discover_connected_devices


def load_axes_config(bringup_pkg_share):
    """Load linear axes configuration from YAML."""
    config_path = os.path.join(
        bringup_pkg_share, 'config', 'linear_axes_params.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f), config_path
    except Exception as e:
        print(f"❌ Error loading axes config: {e}")
        return {}, None


# =============================================================================
# Launch Description
# =============================================================================

def generate_launch_description():
    """Generate launch description with launch arguments."""
    return LaunchDescription([
        DeclareLaunchArgument(
            'sim_mode',
            default_value='false',
            description='Run in simulation mode (true/false)'
        ),
        OpaqueFunction(function=launch_setup)
    ])


def launch_setup(context, *args, **kwargs):
    """
    Setup all nodes based on configuration and detected hardware.

    Called by OpaqueFunction to allow LaunchConfiguration
    values to be evaluated at runtime.
    """
    # Get parameters
    sim_mode = LaunchConfiguration(
        'sim_mode').perform(context).lower() == 'true'
    bringup_pkg = get_package_share_directory('promoc_bringup')

    nodes = []

    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_pkg, 'launch', 'camera.launch.py')
        ),
        launch_arguments={'sim_mode': str(sim_mode).lower()}.items()
    )
    nodes.append(camera_launch)

    mover_config = os.path.join(
        bringup_pkg, 'config', 'mover_node_params.yaml')

    if os.path.exists(mover_config):
        nodes.append(Node(
            package='planar_motor_nodes',
            executable='mover_node',
            name='mover_node',
            parameters=[mover_config],
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        ))
    else:
        launch.logging.get_logger().error(
            f"Mover config not found: {mover_config}")

    axes_config, axes_config_path = load_axes_config(bringup_pkg)

    if not axes_config:
        launch.logging.get_logger().warn("No linear axes configuration found")
        return nodes

    if sim_mode:
        launch.logging.get_logger().info("🚀 Linear Axes: SIMULATION mode")
        for node_name in axes_config.keys():
            nodes.append(_create_axis_node(
                node_name, axes_config_path, sim=True))
    else:
        launch.logging.get_logger().info("⚙️ Linear Axes: HARDWARE mode")
        connected = discover_connected_devices()

        for node_name, params in axes_config.items():
            serial = params.get('ros__parameters', {}).get('serial_number')

            if not serial:
                launch.logging.get_logger().warn(
                    f"  ⚠️ {node_name}: No serial_number configured")
                continue

            if serial in connected:
                launch.logging.get_logger().info(f"  ✅ {node_name}: Connected")
                nodes.append(_create_axis_node(
                    node_name, axes_config_path,
                    sim=False, device_path=connected[serial]
                ))
            else:
                launch.logging.get_logger().warn(
                    f"  ❌ {node_name}: Not connected (S/N: {serial})")

    return nodes


def _create_axis_node(node_name: str, config_path: str, sim: bool, device_path: str = None):
    """Create linear axis node with appropriate parameters."""
    params = [config_path, {'use_sim_time': sim}]

    if device_path:
        params.append({'serial_port': device_path})

    return Node(
        package='linear_axis_nodes',
        executable='lts300_node',
        name=node_name,
        parameters=params,
        output='screen',
        arguments=['--ros-args', '--log-level', 'INFO']
    )
