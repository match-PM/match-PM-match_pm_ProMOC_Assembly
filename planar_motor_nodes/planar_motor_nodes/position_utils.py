#!/usr/bin/env python3
# filepath: /home/soc/Development/Ros2/promoc_assembly/src/promoc_hardware/planar_motor_nodes/planar_motor_nodes/position_utils.py

import time
import math
from typing import List, Optional, Tuple
from enum import Enum

# Smart PMCLib import
from .pmclib_loader import bot, get_pmclib_status


class MotionStatus(Enum):
    """Status der Bewegung basierend auf XBot Controller Status"""
    UNKNOWN = "unknown"
    IDLE = "idle"
    MOVING = "moving"
    ERROR = "error"
    COMPLETED = "completed"
    TIMEOUT = "timeout"


class PositionUtils:
    """Utility-Klasse für Position-Management und Validierung"""

    def __init__(self, node):
        self.node = node
        pmclib_status = get_pmclib_status()
        self.is_mock = pmclib_status['is_mock']

    def get_current_position(self, xbot_id: int = 0) -> Optional[List[float]]:
        """Get current XBot position."""
        try:
            xbot_data_list = bot.get_all_xbot_info(
                0)  # Feedback option 0 = position
            if not xbot_data_list or len(xbot_data_list) <= xbot_id:
                self.node.get_logger().error(f"❌ No data for XBot {xbot_id}")
                return None

            xbot_data = xbot_data_list[xbot_id] if len(
                xbot_data_list) > xbot_id else xbot_data_list[0]

            return [
                float(xbot_data.x_pos),
                float(xbot_data.y_pos),
                float(xbot_data.z_pos),
                float(xbot_data.rx_pos),
                float(xbot_data.ry_pos),
                float(xbot_data.rz_pos)
            ]
        except (IndexError, AttributeError) as e:
            if not self.is_mock:
                self.node.get_logger().error(f"❌ Error getting position: {e}")
            return None

    def get_xbot_status_info(self, xbot_id: int = 0) -> Optional[dict]:
        """Get comprehensive XBot status including movement state."""
        try:
            # Get detailed status from XBot controller
            xbot_status = bot.get_xbot_status(xbot_id)

            # Get basic info for position
            xbot_data_list = bot.get_all_xbot_info(0)
            if not xbot_data_list or len(xbot_data_list) <= xbot_id:
                return None

            xbot_data = xbot_data_list[xbot_id] if len(
                xbot_data_list) > xbot_id else xbot_data_list[0]

            status_info = {
                'position': [
                    float(xbot_data.x_pos),
                    float(xbot_data.y_pos),
                    float(xbot_data.z_pos),
                    float(xbot_data.rx_pos),
                    float(xbot_data.ry_pos),
                    float(xbot_data.rz_pos)
                ],
                'xbot_state': xbot_data.xbot_state,
                'xbot_id': xbot_data.xbot_id,
                'cmd_label': getattr(xbot_status, 'cmd_label', 0),
                'force_mode': getattr(xbot_status, 'force_mode', False),
                'motion_buffer_blocked': getattr(xbot_status, 'motion_buffer_blocked', False),
                'buffered_motion_count': getattr(xbot_status, 'buffered_motion_count', 0),
                'is_connected_to_group': getattr(xbot_status, 'connected_to_group', False),
                'connected_group_id': getattr(xbot_status, 'connected_group_id', -1)
            }

            return status_info

        except Exception as e:
            if not self.is_mock:
                self.node.get_logger().error(
                    f"❌ Error getting XBot status: {e}")
            return None

    def wait_for_motion_completion(self, xbot_id: int, target_position: List[float],
                                   position_tolerance: float, max_wait_time: float = 10.0) -> MotionStatus:
        """
        Wait for motion completion using XBot controller status and position verification.

        Parameters
        ----------
        xbot_id : int
            XBot ID to monitor
        target_position : List[float]
            Expected final position [x, y, z, rx, ry, rz]
        position_tolerance : float
            Position tolerance for final position check
        max_wait_time : float
            Maximum time to wait for completion

        Returns
        -------
        MotionStatus
            Final status of the motion
        """
        start_time = time.time()
        check_interval = 0.05  # 50ms check interval
        last_log_time = start_time

        # Phase 1: Wait for motion to start (XBot should be MOVING)
        motion_started = self._wait_for_motion_start(
            xbot_id, max_start_wait=2.0)
        if not motion_started:
            self.node.get_logger().warning(
                f"⚠️ XBot {xbot_id} motion may not have started properly")

        # Phase 2: Wait for motion to complete (XBot becomes IDLE again)
        while time.time() - start_time < max_wait_time:
            status_info = self.get_xbot_status_info(xbot_id)

            if status_info is None:
                self.node.get_logger().error(
                    f"❌ Cannot get status for XBot {xbot_id}")
                time.sleep(check_interval)
                continue

            current_time = time.time()
            elapsed_time = current_time - start_time

            # Check XBot state
            xbot_state = status_info['xbot_state']
            motion_status = self._interpret_xbot_state(xbot_state)

            # Log progress every 1 second
            if current_time - last_log_time > 1.0:
                self._log_motion_progress(
                    xbot_id, status_info, target_position, elapsed_time)
                last_log_time = current_time

            # Check if motion completed (XBot is IDLE)
            if motion_status == MotionStatus.IDLE:
                self.node.get_logger().info(
                    f"✅ XBot {xbot_id} reports IDLE after {elapsed_time:.2f}s")

                # Verify final position
                return self._verify_final_position(xbot_id, target_position, position_tolerance, status_info)

            # Check for error states
            elif motion_status == MotionStatus.ERROR:
                self.node.get_logger().error(
                    f"❌ XBot {xbot_id} reports ERROR state")
                return MotionStatus.ERROR

            time.sleep(check_interval)

        # Timeout reached
        self.node.get_logger().warning(
            f"⚠️ Motion timeout for XBot {xbot_id} after {max_wait_time:.1f}s")
        return MotionStatus.TIMEOUT

    def _wait_for_motion_start(self, xbot_id: int, max_start_wait: float = 2.0) -> bool:
        """Wait for motion to start (XBot should become MOVING)."""
        start_time = time.time()

        while time.time() - start_time < max_start_wait:
            status_info = self.get_xbot_status_info(xbot_id)
            if status_info:
                motion_status = self._interpret_xbot_state(
                    status_info['xbot_state'])
                if motion_status == MotionStatus.MOVING:
                    return True
            time.sleep(0.02)  # 20ms check

        return False

    def _interpret_xbot_state(self, xbot_state) -> MotionStatus:
        """Interpret XBot state enum to motion status."""
        try:
            # Convert to string if it's an enum
            state_str = str(xbot_state).upper()

            if 'IDLE' in state_str or 'READY' in state_str:
                return MotionStatus.IDLE
            elif 'MOVING' in state_str or 'MOTION' in state_str or 'ACTIVE' in state_str:
                return MotionStatus.MOVING
            elif 'ERROR' in state_str or 'FAULT' in state_str or 'ACCIDENT' in state_str:
                return MotionStatus.ERROR
            else:
                # Log unknown state for debugging
                self.node.get_logger().debug(
                    f"🔧 Unknown XBot state: {xbot_state}")
                return MotionStatus.UNKNOWN

        except Exception as e:
            self.node.get_logger().error(
                f"❌ Error interpreting XBot state: {e}")
            return MotionStatus.UNKNOWN

    def _verify_final_position(self, xbot_id: int, target_position: List[float],
                               tolerance: float, status_info: dict) -> MotionStatus:
        """Verify that final position matches target."""
        current_position = status_info['position']

        # Check position accuracy
        position_errors = []
        for i in range(min(len(target_position), len(current_position))):
            error = abs(target_position[i] - current_position[i])
            position_errors.append(error)

            # Different tolerance for rotational vs linear axes
            check_tolerance = tolerance if i < 3 else tolerance * 2.0

            if error > check_tolerance:
                self.node.get_logger().warning(
                    f"⚠️ XBot {xbot_id} position error on axis {i}: "
                    f"target={target_position[i]:.6f}, actual={current_position[i]:.6f}, "
                    f"error={error:.6f}, tolerance={check_tolerance:.6f}")
                return MotionStatus.ERROR

        # Log successful completion
        max_error = max(position_errors) if position_errors else 0.0
        self.node.get_logger().info(
            f"✅ XBot {xbot_id} motion completed successfully. Max error: {max_error:.6f}")

        return MotionStatus.COMPLETED

    def _log_motion_progress(self, xbot_id: int, status_info: dict,
                             target_position: List[float], elapsed_time: float):
        """Log detailed motion progress."""
        current_pos = status_info['position']
        xbot_state = status_info['xbot_state']
        buffered_count = status_info.get('buffered_motion_count', 0)

        if len(current_pos) >= 6 and len(target_position) >= 6:
            pos_errors = [target_position[i] - current_pos[i]
                          for i in range(6)]

            self.node.get_logger().debug(
                f"🎯 XBot {xbot_id} progress ({elapsed_time:.1f}s):\n"
                f"  State: {xbot_state}, Buffered: {buffered_count}\n"
                f"  Position: ({current_pos[0]:.4f}, {current_pos[1]:.4f}, {current_pos[2]:.4f})m\n"
                f"  Rotation: ({math.degrees(current_pos[3]):.1f}°, {math.degrees(current_pos[4]):.1f}°, {math.degrees(current_pos[5]):.1f}°)\n"
                f"  Errors: XYZ=({pos_errors[0]*1000:.1f}, {pos_errors[1]*1000:.1f}, {pos_errors[2]*1000:.1f})mm"
            )

    # Legacy methods (maintained for compatibility)
    def check_position_reached(self, target_position: List[float],
                               tolerance: float, max_wait_time: float = 2.0,
                               xbot_id: int = 0) -> bool:
        """Legacy method - now uses status-based monitoring."""
        result = self.wait_for_motion_completion(
            xbot_id, target_position, tolerance, max_wait_time)
        return result == MotionStatus.COMPLETED

    # ... rest of existing methods stay the same ...
    def is_position_in_bounds(self, x: float, y: float, z: float) -> bool:
        """Check if position is within defined boundaries."""
        return (self.node.x_min <= x <= self.node.x_max and
                self.node.y_min <= y <= self.node.y_max and
                self.node.z_min <= z <= self.node.z_max)

    def validate_xbot_id(self, xbot_id: int) -> bool:
        """Validate XBot ID is in valid range."""
        if not (0 <= xbot_id <= 15):
            self.node.get_logger().error(
                f"❌ Invalid XBot ID: {xbot_id} (must be 0-15)")
            return False
        return True

    def validate_target_position(self, x: float, y: float, z: float,
                                 rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> bool:
        """Validate target position is within bounds."""
        if not self.is_position_in_bounds(x, y, z):
            self.node.get_logger().error(
                f"❌ Position outside valid range: ({x:.3f}, {y:.3f}, {z:.3f})")
            return False

        max_rotation = self.calculate_max_rotation(z)
        if abs(rx) > max_rotation or abs(ry) > max_rotation:
            self.node.get_logger().error(
                f"❌ Rotation outside valid range: rx={rx:.3f}, ry={ry:.3f}, max={max_rotation:.3f}")
            return False

        return True

    def calculate_max_rotation(self, z_value: float, mover_width: float = 120.0,
                               safety_factor: float = 0.5) -> float:
        """Calculate maximum rotation based on Z height and safety factor."""
        if z_value <= 0:
            return 0.0
        r = (mover_width / 2) * math.sqrt(2) / 1000.0
        max_rotation = math.atan(r / z_value) * safety_factor
        return max_rotation

    def constrain_position_to_bounds(self, current_pos: List[float],
                                     target_pos: List[float]) -> List[float]:
        """Constrain target position to valid bounds, use current position as fallback."""
        constrained = target_pos.copy()

        # Constrain X, Y, Z
        for i, (axis, min_val, max_val) in enumerate([
            ('X', self.node.x_min, self.node.x_max),
            ('Y', self.node.y_min, self.node.y_max),
            ('Z', self.node.z_min, self.node.z_max)
        ]):
            if not (min_val <= target_pos[i] <= max_val):
                constrained[i] = current_pos[i]
                self.node.get_logger().warning(
                    f"⚠️ {axis} position {target_pos[i]:.3f} out of bounds, using current: {current_pos[i]:.3f}")

        # Constrain rotations based on Z value
        if len(target_pos) >= 6:
            max_rotation = self.calculate_max_rotation(constrained[2])
            for i, axis in enumerate(['RX', 'RY'], start=3):
                if abs(target_pos[i]) > max_rotation:
                    constrained[i] = current_pos[i]
                    self.node.get_logger().warning(
                        f"⚠️ {axis} rotation {target_pos[i]:.3f} out of bounds, using current: {current_pos[i]:.3f}")

        return constrained
