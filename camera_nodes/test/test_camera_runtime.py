# ruff: noqa: E402
"""Runtime tests for mock image publication and status handling."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in ("camera_nodes", "promoc_core", "promoc_assembly_interfaces"):
    package_root = REPO_ROOT / rel
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from camera_nodes.node import CameraNode
from promoc_assembly_interfaces.msg import DeviceStatus
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Image


def test_mock_node_publishes_repeated_frames_and_status():
    os.environ.setdefault("ROS_LOG_DIR", "/tmp/ros_logs_camera_tests")
    rclpy.init()
    camera = CameraNode(
        parameter_overrides=[
            Parameter("driver_mode", value="mock"),
            Parameter("mock.width", value=32),
            Parameter("mock.height", value=24),
            Parameter("mock.encoding", value="mono8"),
            Parameter("frame_id", value="test_frame"),
            Parameter("publish_rate_hz", value=20.0),
            Parameter("status_publish_rate_hz", value=20.0),
        ]
    )
    collector = Node("camera_test_collector")
    executor = SingleThreadedExecutor()
    executor.add_node(camera)
    executor.add_node(collector)

    images: list[Image] = []
    statuses: list[DeviceStatus] = []
    collector.create_subscription(Image, "/promoc/camera/image_raw", images.append, 10)
    collector.create_subscription(DeviceStatus, "/promoc/camera/status", statuses.append, 10)

    deadline = time.time() + 2.0
    while time.time() < deadline and len(images) < 2:
        executor.spin_once(timeout_sec=0.1)

    assert len(images) >= 2
    assert images[0].header.frame_id == "test_frame"
    assert images[0].width == 32
    assert images[0].height == 24
    assert images[0].encoding == "mono8"
    assert len(images[0].data) == 32 * 24
    assert images[0].header.stamp.sec >= 0

    assert statuses
    assert any(msg.state == int(4) for msg in statuses)

    driver = camera.driver
    camera.destroy_node()
    collector.destroy_node()
    executor.shutdown()
    rclpy.shutdown()

    assert driver.is_connected is False
