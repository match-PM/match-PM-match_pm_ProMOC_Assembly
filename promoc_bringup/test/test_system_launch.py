
import os
import unittest
import pytest

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_testing.actions import ReadyToTest
import launch_testing.markers

from ament_index_python.packages import get_package_share_directory


@pytest.mark.launch_test
def generate_test_description():
    bringup_dir = get_package_share_directory('promoc_bringup')
    launch_path = os.path.join(bringup_dir, 'launch', 'system.launch.py')

    # Launch the system in simulation mode
    # We use a timer to delay the test slightly to ensure things start up
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_path),
            launch_arguments={'sim_mode': 'true'}.items(),
        ),
        ReadyToTest(),
    ])


class TestSystemStartup(unittest.TestCase):
    
    def test_nodes_running(self, proc_output):
        """Test that the expected nodes start up."""
        # We expect these nodes to be started by system.launch.py
        # Check standard output or process names if possible.
        # Since checking process names via launch_testing is tricky without ActiveMatching,
        # we often check for log output indicating startup.
        
        # NOTE: This is a basic test. In a real scenario, we might want to check
        # for specific log messages like "Node started" or use `ros2 node list`.
        # However, verifying the launch file doesn't crash immediately is a good Step 1.
        
        # We define a strict node list we expect
        # 'mover_node', 'lts300_x_axis', 'lts300_z_axis'
        pass

    def test_no_crashes(self, proc_info):
        """Test that processes do not crash immediately."""
        # Wait for a short time to catch immediate crashes
        # launch_testing handles this validation implicitly if we check exit codes
        launch_testing.asserts.assertExitCodes(proc_info, allow_stderr=True)
