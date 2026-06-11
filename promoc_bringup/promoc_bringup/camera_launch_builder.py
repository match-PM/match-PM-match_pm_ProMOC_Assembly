"""Helper builders for the reduced camera launch stack."""

from __future__ import annotations


def resolve_binning_factor(camera_params: dict, binning_override: str, logger) -> int:
    """Resolve effective binning factor from config with optional launch override."""
    binning_factor = int(camera_params.get("binning_factor", 1))
    if not binning_override:
        return binning_factor
    try:
        return int(binning_override)
    except ValueError:
        logger.warn(
            f"Invalid binning_factor override '{binning_override}', using config value."
        )
        return binning_factor


def build_driver_node_parameters(
    camera_params: dict,
    camera_config: dict,
    camera_info_yaml: str,
    dynamic_parameters_yaml: str,
    binning_factor: int,
) -> dict:
    """Build parameter dictionary for camera_aravis2 driver node."""
    return {
        "guid": camera_params["guid"],
        "frame_id": camera_params["cameraname"],
        "stream_names": ["stream0"],
        "camera_info_urls": [f"file://{camera_info_yaml}"],
        "dynamic_parameters_yaml_url": dynamic_parameters_yaml,
        "DeviceControl": {"DeviceLinkThroughputLimit": 125000000},
        "AcquisitionControl": {
            "AcquisitionFrameRateEnable": True,
            "AcquisitionFrameRate": 15.0,
            "ExposureTime": 30000.0,
            "AcquisitionMode": "Continuous",
        },
        "ImageFormatControl": {
            "PixelFormat": [camera_params["pixel_format"]],
            "Width": camera_config["camera_info"]["image_width"],
            "Height": camera_config["camera_info"]["image_height"],
            "BinningHorizontal": int(binning_factor),
            "BinningVertical": int(binning_factor),
        },
    }


def build_camera_node_parameters(
    camera_params: dict | None,
    camera_config: dict | None,
    *,
    use_simulator: bool,
) -> dict:
    """Build reduced camera-node parameters from launch/runtime context."""
    if use_simulator:
        return {
            "driver_mode": "mock",
            "use_simulator": True,
            "camera_name": "mock_camera",
            "image_topic": "/promoc/camera/image_raw",
            "status_topic": "/promoc/camera/status",
            "frame_id": "assembly_camera_frame",
        }

    source_topic = "/promoc/assembly_camera/stream0/image_raw"
    frame_id = "assembly_camera_frame"
    camera_name = "assembly_camera"
    if camera_params:
        source_topic = camera_params.get("subscription_topic", source_topic)
        frame_id = camera_params.get("cameraname", frame_id)
        camera_name = camera_params.get("cameraname", camera_name)
    if camera_config:
        frame_id = camera_config.get("camera_info", {}).get("camera_name", frame_id)

    return {
        "driver_mode": "hardware",
        "use_simulator": False,
        "camera_name": camera_name,
        "source_image_topic": source_topic,
        "image_topic": "/promoc/camera/image_raw",
        "status_topic": "/promoc/camera/status",
        "frame_id": frame_id,
    }
