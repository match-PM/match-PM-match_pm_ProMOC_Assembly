"""Helper builders for camera.launch.py parameter mapping."""

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
    """Build camera_node parameter mapping from launch/runtime context."""
    if use_simulator:
        return {"use_simulator": True}

<<<<<<< HEAD
    return {
        "use_simulator": False,
=======
    camera_params = camera_params or {}
    camera_config = camera_config or {}
    camera_info = camera_config.get("camera_info", {})

    return {
        "use_simulator": False,
        "mtf.use_full_frame": True,
        "mtf.full_frame_width": camera_params.get(
            "sensor_resolution_h",
            camera_info.get("image_width", 5536),
        ),
        "mtf.full_frame_height": camera_params.get(
            "sensor_resolution_v",
            camera_info.get("image_height", 3692),
        ),
        "mtf.full_frame_offset_x": 0,
        "mtf.full_frame_offset_y": 0,
        "mtf.full_frame_binning": 1,
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
    }
