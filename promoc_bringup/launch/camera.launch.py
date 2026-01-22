import os
import yaml
import tempfile
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node
import launch


def generate_launch_description():
    """
    Consolidated camera system launch file.

    Supports both simulation and hardware via 'sim_mode' argument.
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
    sim_mode = LaunchConfiguration(
        'sim_mode').perform(context).lower() == 'true'
    launch_actions = []

    bringup_pkg_share = get_package_share_directory('promoc_bringup')

    camera_config_file = os.path.join(
        bringup_pkg_share, 'config', 'ids_camera_params.yaml')

    # Pre-launch camera reset for hardware mode
    if not sim_mode:
        # Try to find reset script in source directory
        reset_script_locations = [
            os.path.join(os.path.dirname(__file__), '..', 'promoc_bringup', 'camera_reset_hook.py'),
            os.path.join(bringup_pkg_share, '..', '..', '..', 'src',
                        'match-PM-match_pm_ProMOC_Assembly', 'promoc_bringup',
                        'promoc_bringup', 'camera_reset_hook.py'),
        ]
        
        reset_script = None
        for loc in reset_script_locations:
            if os.path.exists(loc):
                reset_script = loc
                break
        
        if reset_script:
            launch.logging.get_logger().info(f"🔄 Executing pre-launch camera reset from {reset_script}...")
            try:
                # Execute reset synchronously before launching nodes
                result = subprocess.run(
                    ['python3', reset_script],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            launch.logging.get_logger().info(f"  {line}")
            except Exception as e:
                launch.logging.get_logger().warn(
                    f"Pre-launch reset failed: {e}, continuing anyway...")
        else:
            launch.logging.get_logger().warn(
                "Pre-launch reset script not found, skipping automatic reset")

    if sim_mode:
        launch.logging.get_logger().info("🚀 Launching Camera in SIMULATION mode")

        launch_actions.append(Node(
            package='camera_nodes',
            executable='camera_simulator',
            name='camera_simulator',
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO']
        ))

        launch_actions.append(Node(
            package='camera_nodes',
            executable='camera_node',
            name='camera_node',
            namespace='promoc',
            output='screen',
            parameters=[{
                'use_simulator': True,
                'mtf_csv_path': ''
            }],
            arguments=['--ros-args', '--log-level', 'INFO']
        ))

    else:
        launch.logging.get_logger().info("📷 Launching Camera in HARDWARE mode")

        try:
            camera_config = yaml.load(
                open(camera_config_file),
                Loader=yaml.SafeLoader
            )
            camera_params = camera_config["camera_params"]

            driver = {
                "usb3vision": "camera_driver_uv",
                "gigevision": "camera_driver_gv",
            }[camera_params["driver"]]

            driver_node_name = f"{camera_params['cameraname']}"

            d = tempfile.mkdtemp()
            camera_info_yaml = os.path.join(d, "camera_info.yaml")
            with open(camera_info_yaml, "wt") as f:
                f.write(yaml.dump(camera_config["camera_info"]))

            dynamic_parameters_yaml = os.path.join(
                d, "dynamic_parameters.yaml")
            with open(dynamic_parameters_yaml, "wt") as f:
                f.write(yaml.dump(camera_config["dynamic_parameters"]))

            launch.logging.get_logger().info(
                f"Using config: {camera_config_file}")
            launch.logging.get_logger().info(
                f"Camera GUID: {camera_params['guid']}")

            launch_actions.append(Node(
                name=driver_node_name,
                namespace='promoc',
                package="camera_aravis2",
                executable=driver,
                output="screen",
                emulate_tty=True,
                arguments=['--ros-args', '--log-level', 'INFO'],
                parameters=[{
                    "guid": camera_params["guid"],
                    "frame_id": camera_params["cameraname"],
                    "stream_names": ["stream0"],
                    "camera_info_urls": [f"file://{camera_info_yaml}"],
                    "dynamic_parameters_yaml_url": dynamic_parameters_yaml,
                    "DeviceControl": {
                        "DeviceLinkThroughputLimit": 125000000,
                    },
                    "AcquisitionControl": {
                        "AcquisitionFrameRateEnable": True,
                        "AcquisitionFrameRate": 15.0,
                        "ExposureTime": 30000.0,
                        "AcquisitionMode": "Continuous"
                    },
                    "ImageFormatControl": {
                        "PixelFormat": [camera_params["pixel_format"]],
                        "Width": 2048,
                        "Height": 1536,
                    },
                }]
            ))

            launch_actions.append(Node(
                name=f"{driver_node_name}_controller",
                namespace='promoc',
                package="pm_genicam_controller",
                executable="controller",
                output="screen",
                emulate_tty=True,
                arguments=['--ros-args', '--log-level', 'INFO'],
                parameters=[{
                    "driver_node": f"/promoc/{driver_node_name}",
                }]
            ))

            launch_actions.append(Node(
                package='camera_nodes',
                executable='camera_node',
                name='camera_node',
                namespace='promoc',
                output='screen',
                arguments=['--ros-args', '--log-level', 'INFO'],
                parameters=[{
                    'use_simulator': False,
                        'mtf_csv_path': ''
                }],
            ))

            # Add camera watchdog for automatic recovery
            launch_actions.append(Node(
                package='camera_nodes',
                executable='camera_watchdog',
                name='camera_watchdog',
                namespace='promoc',
                output='screen',
                arguments=['--ros-args', '--log-level', 'INFO'],
                parameters=[{
                    'image_topic': '/promoc/assembly_camera/stream0/image_raw',
                    'timeout_seconds': 10.0,
                    'enable_auto_reset': True,
                    'reset_cooldown_seconds': 30.0
                }]
            ))

        except Exception as e:
            launch.logging.get_logger().error(
                f"Failed to load camera configuration: {e}")

    return launch_actions
