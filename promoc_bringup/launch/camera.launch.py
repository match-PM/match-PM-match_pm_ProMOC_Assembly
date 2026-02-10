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
    Allows flexible camera selection via 'camera_type' argument.
    """

    sim_mode_arg = DeclareLaunchArgument(
        'sim_mode',
        default_value='false',
        description='Run in simulation mode'
    )

    camera_type_arg = DeclareLaunchArgument(
        'camera_type',
        default_value='ids_u3_3800cp_hq',
        description='Camera configuration to use (filename in config/cameras/ without .yaml extension). Default: ids_u3_3800cp_hq'
    )

    binning_factor_arg = DeclareLaunchArgument(
        'binning_factor',
        default_value='',
        description='Override binning factor (e.g., 1 or 2). Empty = use config file.'
    )

    return LaunchDescription([
        sim_mode_arg,
        camera_type_arg,
        binning_factor_arg,
        OpaqueFunction(function=launch_setup)
    ])


def launch_setup(context, *args, **kwargs):
    sim_mode = LaunchConfiguration(
        'sim_mode').perform(context).lower() == 'true'
    camera_type = LaunchConfiguration('camera_type').perform(context)
    binning_override = LaunchConfiguration('binning_factor').perform(context).strip()
    
    launch_actions = []

    bringup_pkg_share = get_package_share_directory('promoc_bringup')

    # Construct camera config file path from camera_type parameter
    # First, try new cameras/ subdirectory structure
    camera_config_file = os.path.join(
        bringup_pkg_share, 'config', 'cameras', f'{camera_type}.yaml')
    
    # Fallback to legacy config location if not found
    if not os.path.exists(camera_config_file):
        legacy_config = os.path.join(
            bringup_pkg_share, 'config', 'ids_camera_params.yaml')
        if os.path.exists(legacy_config):
            launch.logging.get_logger().warn(
                f"Camera config not found at {camera_config_file}, "
                f"using legacy config: {legacy_config}")
            camera_config_file = legacy_config
        else:
            launch.logging.get_logger().error(
                f"Camera configuration file not found: {camera_config_file}")
            return []


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

            # Get binning factor (default to 1 if not specified)
            binning_factor = camera_params.get("binning_factor", 1)
            if binning_override:
                try:
                    binning_factor = int(binning_override)
                except ValueError:
                    launch.logging.get_logger().warn(
                        f"Invalid binning_factor override '{binning_override}', using config value"
                    )

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
                        "Width": camera_config["camera_info"]["image_width"],
                        "Height": camera_config["camera_info"]["image_height"],
                        "BinningHorizontal": binning_factor,
                        "BinningVertical": binning_factor,
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
                    'mtf_csv_path': '',
                    'mtf.use_full_frame': True,
                    'mtf.full_frame_width': camera_params.get(
                        'sensor_resolution_h',
                        camera_config["camera_info"]["image_width"],
                    ),
                    'mtf.full_frame_height': camera_params.get(
                        'sensor_resolution_v',
                        camera_config["camera_info"]["image_height"],
                    ),
                    'mtf.full_frame_offset_x': 0,
                    'mtf.full_frame_offset_y': 0,
                    'mtf.full_frame_binning': 1,
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
