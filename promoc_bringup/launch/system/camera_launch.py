import os
import yaml
import tempfile
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import launch

def generate_launch_description():
    """Launch file to run the camera controller with pm_genicam and camera_aravis2."""

    # Load camera configuration from YAML file (for pm_genicam)
    camera_config_file = os.path.join(
        get_package_share_directory('promoc_bringup'),
        'config',
        'camera_node_params.yaml'
    )

    # Load ROS2 parameters for camera_node
    camera_node_params_file = os.path.join(
        get_package_share_directory('promoc_bringup'),
        'config',
        'camera_node_ros_params.yaml'
    )
    
    # Load camera configuration for pm_genicam
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

    # Create temporary files for camera info and dynamic parameters
    d = tempfile.mkdtemp()
    camera_info_yaml = os.path.join(d, "camera_info.yaml")
    with open(camera_info_yaml, "wt") as f:
        f.write(yaml.dump(camera_config["camera_info"]))

    dynamic_parameters_yaml = os.path.join(d, "dynamic_parameters.yaml")
    with open(dynamic_parameters_yaml, "wt") as f:
        f.write(yaml.dump(camera_config["dynamic_parameters"]))

    launch.logging.get_logger().info(f"Using config: {camera_config_file}")
    launch.logging.get_logger().info(f"Camera GUID: {camera_params['guid']}")

    return LaunchDescription([
        # Camera driver node (camera_aravis2)
        Node(
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
                    "AcquisitionFrameRate": 15.0,  # Unter dem Maximum für Stabilität
                    "ExposureTime": 30000.0,  # 30ms für gute Belichtung
                    "AcquisitionMode": "Continuous"
                },
                "ImageFormatControl": {
                    "PixelFormat": [camera_params["pixel_format"]],
                    "Width": 2048,  # Größere ROI nutzen (aber nicht voll)
                    "Height": 1536,  # Bessere Auflösung
                },
            }]
        ),

        # Controller node (pm_genicam_controller)
        Node(
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
        ),
        
        # Your camera controller, loading parameters from YAML
        Node(
            package='camera_nodes',
            executable='camera_node',
            name='camera_node',
            namespace='promoc',
            output='screen',
            arguments=['--ros-args', '--log-level', 'INFO'],
            parameters=[camera_node_params_file, {'use_simulator': False}],
        ),
    ])
