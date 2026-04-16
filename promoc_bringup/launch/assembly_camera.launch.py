"""Deprecated compatibility wrapper for `camera.launch.py`.

Release N keeps this file so existing operator scripts do not break.
Use `camera.launch.py` directly for new workflows.
"""

from __future__ import annotations

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description() -> LaunchDescription:
    share_dir = get_package_share_directory("promoc_bringup")
    camera_launch = os.path.join(share_dir, "launch", "camera.launch.py")
    return LaunchDescription(
        [
            LogInfo(
                msg=(
                    "[Deprecated] Use "
                    "'ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware'"
                )
            ),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(camera_launch)),
        ]
    )
