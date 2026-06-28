"""Camera launch file for raw image streaming."""

from __future__ import annotations

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "driver_mode",
                default_value="hardware",
                description="Canonical driver mode: hardware|mock",
            ),
            DeclareLaunchArgument(
                "camera_type",
                default_value="ids_u3_3800cp_hq",
                description="Camera config filename in config/cameras without extension.",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )


def launch_setup(context, *args, **kwargs):
    """Haupt-Launch-Logik fuer die Kamera.

    Ablauf:
    - driver_mode aus Fail: "hardware" startet auch den camera_aravis2-Treiberknoten
    - "mock" startet nur den camera_nodes-Knoten (Mock-Modus)
    - Bei "hardware": Laedt kameraspezifische YAML-Konfiguration aus config/cameras/
    """
    del args, kwargs
    driver_mode = LaunchConfiguration("driver_mode").perform(context).strip().lower()
    camera_type = LaunchConfiguration("camera_type").perform(context).strip()
    logger = launch.logging.get_logger()

    logger.info(f"Camera launch driver_mode={driver_mode}")

    if driver_mode == "mock":
        return [_camera_node("mock")]
    if driver_mode != "hardware":
        logger.error(
            f"Invalid camera driver_mode '{driver_mode}'. Use 'hardware' or 'mock'."
        )
        return []

    hardware_config_file = _camera_hardware_config_path(camera_type)
    if not os.path.exists(hardware_config_file):
        logger.error(
            f"Camera hardware configuration file not found: {hardware_config_file}"
        )
        return []

    try:
        hardware_config = _load_yaml(hardware_config_file)
        return [
            _hardware_camera_driver_node(hardware_config),  # camera_aravis2 Treiber
            _camera_node("hardware"),                        # ProMOC Kamera-Knoten
        ]
    except Exception as exc:
        logger.error(f"Failed to load camera configuration: {exc}")
        return []


def _camera_node(driver_mode: str) -> Node:
    """Erstellt den ProMOC camera_nodes-Knoten mit Konfiguration."""
    camera_config = os.path.join(
        get_package_share_directory("camera_nodes"), "config", "camera.yaml"
    )
    return Node(
        package="camera_nodes",
        executable="camera_node",
        name="camera_node",
        namespace="promoc",
        output="screen",
        parameters=[camera_config, {"driver_mode": driver_mode}],
        arguments=["--ros-args", "--log-level", "INFO"],
    )


def _camera_hardware_config_path(camera_type: str) -> str:
    """Pfad zur kameraspezifischen YAML-Konfiguration (z.B. ids_u3_3800cp_hq.yaml)."""
    bringup_pkg_share = get_package_share_directory("promoc_bringup")
    return os.path.join(bringup_pkg_share, "config", "cameras", f"{camera_type}.yaml")


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle) or {}


def _write_temp_yaml(filename: str, data) -> str:
    tmp_dir = tempfile.mkdtemp()
    yaml_path = os.path.join(tmp_dir, filename)
    with open(yaml_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(yaml.dump(data))
    return yaml_path


def _hardware_camera_driver_node(hardware_config: dict) -> Node:
    """Erstellt den camera_aravis2-Hardware-Treiberknoten.

    Aus der YAML-Konfiguration werden extrahiert:
    - Kameraparameter (GUID, Treibertyp usb3vision/gigevision)
    - CameraInfo (wird als temporaere YAML gespeichert)
    - Dynamische Parameter (wird als temporaere YAML gespeichert)
    """
    camera_params = hardware_config.get("camera_params", {})
    # Mapping: Kameratreiber -> ROS-Executable
    driver = {"usb3vision": "camera_driver_uv", "gigevision": "camera_driver_gv"}.get(
        camera_params.get("driver", "usb3vision")
    )
    if driver is None:
        raise ValueError(
            f"Unsupported camera driver type: {camera_params.get('driver')}"
        )

    camera_info_yaml = _write_temp_yaml(
        "camera_info.yaml",
        hardware_config.get("camera_info", {}),
    )
    dynamic_parameters_yaml = _write_temp_yaml(
        "dynamic_parameters.yaml",
        hardware_config.get("dynamic_parameters", []),
    )
    driver_node_name = camera_params.get("cameraname", "assembly_camera")
    driver_params = [
        {"camera_info_url": f"file://{camera_info_yaml}"},
        {"dynamic_parameters_url": f"file://{dynamic_parameters_yaml}"},
        {"guid": camera_params.get("guid", "")},
        {"frame_id": "assembly_camera_frame"},
    ]

    return Node(
        name=driver_node_name,
        namespace="promoc",
        package="camera_aravis2",
        executable=driver,
        output="screen",
        emulate_tty=True,
        arguments=["--ros-args", "--log-level", "INFO"],
        parameters=driver_params,
    )
