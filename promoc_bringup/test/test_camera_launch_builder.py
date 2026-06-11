"""Focused tests for reduced camera launch parameter mapping."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
for rel in ("promoc_bringup", "camera_nodes"):
    package_root = ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from camera_nodes.config import PARAMETER_DEFAULTS  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "camera_launch_builder",
    ROOT / "promoc_bringup" / "promoc_bringup" / "camera_launch_builder.py",
)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
build_camera_node_parameters = _MODULE.build_camera_node_parameters


def test_camera_launch_builder_uses_declared_mock_parameters():
    params = build_camera_node_parameters(None, None, use_simulator=True)
    declared = {name for name, _default in PARAMETER_DEFAULTS}

    assert set(params).issubset(declared)
    assert params["driver_mode"] == "mock"
    assert params["image_topic"] == "/promoc/camera/image_raw"
    assert params["status_topic"] == "/promoc/camera/status"


def test_camera_launch_builder_maps_hardware_source_topic():
    params = build_camera_node_parameters(
        {
            "subscription_topic": "/promoc/assembly_camera/stream0/image_raw",
            "cameraname": "promoc_camera",
        },
        {"camera_info": {"camera_name": "assembly_camera_stream0"}},
        use_simulator=False,
    )

    assert params["driver_mode"] == "hardware"
    assert params["source_image_topic"] == "/promoc/assembly_camera/stream0/image_raw"
    assert params["frame_id"] == "assembly_camera_stream0"
