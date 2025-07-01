#!/usr/bin/env python3
# filepath: /home/soc/Development/Ros2/promoc_assembly/src/promoc_hardware/planar_motor_nodes/planar_motor_nodes/position_utils.py

import time
import math
from typing import List, Optional, Tuple
from enum import Enum

# Smart PMCLib import
from .pmclib_loader import bot, get_pmclib_status, XbotState


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
            # Enhanced debugging for real PMCLib (less verbose)
            if not self.is_mock and xbot_id > 0:
                self.node.get_logger().debug(f"🔍 Requesting position for XBot {xbot_id}")
            
            xbot_data_list = bot.get_all_xbot_info(0)  # Feedback option 0 = position
            
            if not xbot_data_list:
                if not self.is_mock:
                    self.node.get_logger().error(f"❌ No XBot data returned from PMCLib")
                return None
                
            # Check if requested XBot ID exists
            if xbot_id >= len(xbot_data_list):
                if not self.is_mock:
                    # Only log warning once per session for each XBot ID
                    warning_key = f"xbot_{xbot_id}_unavailable"
                    if not hasattr(self, '_logged_warnings'):
                        self._logged_warnings = set()
                    
                    if warning_key not in self._logged_warnings:
                        self.node.get_logger().warning(
                            f"⚠️ XBot {xbot_id} not available. Available XBots: {len(xbot_data_list)} "
                            f"(indices 0-{len(xbot_data_list)-1}). Using XBot 0 as fallback.")
                        self._logged_warnings.add(warning_key)
                
                # Use XBot 0 as fallback
                xbot_id = 0

            xbot_data = xbot_data_list[xbot_id]

            position = [
                float(xbot_data.x_pos),
                float(xbot_data.y_pos),
                float(xbot_data.z_pos),
                float(xbot_data.rx_pos),
                float(xbot_data.ry_pos),
                float(xbot_data.rz_pos)
            ]
            
            return position
            
        except (IndexError, AttributeError) as e:
            if not self.is_mock:
                self.node.get_logger().error(f"❌ Error getting position for XBot {xbot_id}: {e}")
            return None

    def get_xbot_status_info(self, xbot_id: int = 0) -> Optional[dict]:
        """Get comprehensive XBot status including movement state."""
        try:
            # Enhanced debugging for real PMCLib
            if not self.is_mock:
                self.node.get_logger().debug(f"🔍 Getting status info for XBot {xbot_id}")
            
            # Get basic position first (most reliable)
            current_pos = self.get_current_position(xbot_id)
            if not current_pos:
                if not self.is_mock:
                    self.node.get_logger().warning(f"⚠️ No position data for XBot {xbot_id}, but continuing with status check")
                # Don't return None immediately - try to get status anyway
                current_pos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # Fallback

            # Try to get detailed status from XBot controller
            try:
                if not self.is_mock:
                    self.node.get_logger().debug(f"🔍 Calling bot.get_xbot_status({xbot_id})")
                
                xbot_status = bot.get_xbot_status(xbot_id)
                
                if not self.is_mock:
                    self.node.get_logger().debug(f"🔍 XBot {xbot_id} raw status: {xbot_status}")
                    self.node.get_logger().debug(f"🔍 XBot {xbot_id} state: {xbot_status.xbot_state}")
                
                xbot_state_str = self._xbot_state_to_string(xbot_status.xbot_state)
                xbot_state_enum = xbot_status.xbot_state
                
                if not self.is_mock:
                    self.node.get_logger().debug(f"🔍 XBot {xbot_id} interpreted state: {xbot_state_str}")
                
            except Exception as e:
                # Fallback if status call fails
                if not self.is_mock:
                    self.node.get_logger().warning(f"⚠️ Could not get XBot {xbot_id} status: {e}")
                    # Try to understand what XBots are available
                    try:
                        # Check how many XBots the system thinks are available
                        all_status = []
                        for test_id in range(4):  # Test first 4 XBot IDs
                            try:
                                test_status = bot.get_xbot_status(test_id)
                                all_status.append(f"XBot {test_id}: available")
                            except Exception as test_e:
                                all_status.append(f"XBot {test_id}: {test_e}")
                        self.node.get_logger().debug(f"🔍 XBot availability check: {all_status}")
                    except:
                        pass
                        
                xbot_state_str = "IDLE"
                xbot_state_enum = XbotState.XBOT_IDLE

            status_info = {
                'position': current_pos,
                'xbot_state': xbot_state_enum,
                'xbot_state_string': xbot_state_str,
                'xbot_id': xbot_id,
                'cmd_label': 0,
                'force_mode': False,
                'motion_buffer_blocked': False,
                'buffered_motion_count': 0,
                'is_connected_to_group': False,
                'connected_group_id': -1
            }

            return status_info

        except Exception as e:
            if not self.is_mock:
                self.node.get_logger().error(f"❌ Error getting XBot status: {e}")
            return None

    def diagnose_xbot_availability(self, max_xbot_id: int = 4) -> dict:
        """Diagnose which XBots are available and responding."""
        diagnosis = {
            'available_xbots': [],
            'total_from_get_all': 0,
            'errors': [],
            'feedback_options': {}
        }
        
        try:
            # Test different feedback options
            for feedback_opt in [0, 1, 2]:
                try:
                    data_list = bot.get_all_xbot_info(feedback_opt)
                    count = len(data_list) if data_list else 0
                    diagnosis['feedback_options'][feedback_opt] = {
                        'count': count,
                        'success': True
                    }
                    if feedback_opt == 0:  # Position feedback
                        diagnosis['total_from_get_all'] = count
                except Exception as e:
                    diagnosis['feedback_options'][feedback_opt] = {
                        'count': 0,
                        'success': False,
                        'error': str(e)
                    }
            
            # Test individual XBot status calls
            for xbot_id in range(max_xbot_id):
                try:
                    status = bot.get_xbot_status(xbot_id)
                    diagnosis['available_xbots'].append({
                        'id': xbot_id,
                        'status': 'available',
                        'state': self._xbot_state_to_string(status.xbot_state)
                    })
                except Exception as e:
                    diagnosis['available_xbots'].append({
                        'id': xbot_id,
                        'status': 'error',
                        'error': str(e)
                    })
                    
        except Exception as e:
            diagnosis['errors'].append(f"General diagnosis error: {e}")
            
        return diagnosis

    def get_xbot_state_string(self, xbot_id: int = 0) -> str:
        """Get just the XBot state as a string - simple and reliable."""
        try:
            # For real PMCLib, handle the case where only XBot 0 is available
            if not self.is_mock:
                # First check how many XBots are available
                try:
                    xbot_data_list = bot.get_all_xbot_info(0)
                    available_count = len(xbot_data_list) if xbot_data_list else 0
                    
                    if xbot_id >= available_count:
                        # Only log debug message, not warning
                        self.node.get_logger().debug(
                            f"🔍 XBot {xbot_id} not available (only {available_count} XBots), using XBot 0")
                        xbot_id = 0  # Fallback to XBot 0
                except:
                    pass  # If this fails, continue with original xbot_id
                    
            xbot_status = bot.get_xbot_status(xbot_id)
            return self._xbot_state_to_string(xbot_status.xbot_state)
        except Exception as e:
            if not self.is_mock:
                self.node.get_logger().debug(f"🔍 get_xbot_state_string failed for XBot {xbot_id}: {e}")
                # Try XBot 0 as fallback
                if xbot_id != 0:
                    try:
                        xbot_status = bot.get_xbot_status(0)
                        return self._xbot_state_to_string(xbot_status.xbot_state)
                    except:
                        pass
            return "IDLE"  # Safe fallback

    def _xbot_state_to_string(self, xbot_state) -> str:
        """Convert XbotState enum to readable string"""
        try:
            if hasattr(xbot_state, 'name'):
                return xbot_state.name
            else:
                # Fallback for integer values
                state_names = {
                    -2: "XBOT_PREVIEW",
                    -1: "XBOT_UNKNOWN",
                    0: "XBOT_UNDETECTED",
                    1: "XBOT_DISCOVERING",
                    2: "XBOT_LANDED",
                    3: "XBOT_IDLE",
                    4: "XBOT_DISABLED",
                    5: "XBOT_MOTION",
                    6: "XBOT_WAIT",
                    7: "XBOT_STOPPING",
                    8: "XBOT_OBSTACLE_DETECTED",
                    9: "XBOT_HOLDPOSITION",
                    10: "XBOT_STOPPED",
                    11: "XBOT_RESERVED",
                    12: "XBOT_RESERVED1",
                    13: "XBOT_RESERVED2",
                    14: "XBOT_ERROR",
                    15: "XBOT_UNINSTALLED"
                }
                return state_names.get(int(xbot_state), "UNKNOWN")
        except:
            return "UNKNOWN"

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

    def wait_for_motion_completion_robust(self, xbot_id: int, target_position: List[float],
                                          position_tolerance: float, max_wait_time: float = 10.0) -> MotionStatus:
        """
        Robust motion completion waiting that handles real PMCLib quirks.
        Falls back to alternative XBot IDs if the requested one becomes unavailable.
        """
        start_time = time.time()
        last_log_time = start_time
        last_known_good_xbot = xbot_id

        # For real PMCLib, first check what XBots are available
        if not self.is_mock:
            diagnosis = self.diagnose_xbot_availability()
            available_xbots = [x['id'] for x in diagnosis['available_xbots'] if x['status'] == 'available']
            self.node.get_logger().info(f"🔍 Available XBots for motion monitoring: {available_xbots}")
            
            if xbot_id not in available_xbots and available_xbots:
                fallback_xbot = available_xbots[0]
                self.node.get_logger().warning(
                    f"⚠️ XBot {xbot_id} not available, using XBot {fallback_xbot} for monitoring")
                last_known_good_xbot = fallback_xbot

        while time.time() - start_time < max_wait_time:
            try:
                # Try requested XBot first
                state_str = self.get_xbot_state_string(xbot_id)
                monitoring_xbot = xbot_id
                
                # If that fails and we're using real PMCLib, try fallback
                if not self.is_mock and state_str in ["IDLE", "ERROR"] and last_known_good_xbot != xbot_id:
                    try:
                        fallback_state = self.get_xbot_state_string(last_known_good_xbot)
                        if fallback_state not in ["IDLE", "ERROR"]:
                            state_str = fallback_state
                            monitoring_xbot = last_known_good_xbot
                            self.node.get_logger().debug(
                                f"🔄 Using XBot {monitoring_xbot} for monitoring (requested: {xbot_id})")
                    except:
                        pass
                
                elapsed_time = time.time() - start_time

                # Log progress every 1 second
                if time.time() - last_log_time > 1.0:
                    self.node.get_logger().info(
                        f"🔄 Motion monitoring XBot {monitoring_xbot}: {state_str} (t={elapsed_time:.1f}s)")
                    last_log_time = time.time()

                # Check if motion completed
                if state_str in ["XBOT_IDLE", "IDLE"]:
                    self.node.get_logger().info(
                        f"✅ Motion completed in {elapsed_time:.2f}s (monitored via XBot {monitoring_xbot})")
                    return MotionStatus.COMPLETED

                # Check for error states
                elif state_str in ["XBOT_ERROR", "ERROR", "XBOT_STOPPED", "XBOT_OBSTACLE_DETECTED"]:
                    self.node.get_logger().error(
                        f"❌ Motion error - State: {state_str} (XBot {monitoring_xbot})")
                    return MotionStatus.ERROR

                # Continue waiting for motion states
                time.sleep(0.1)

            except Exception as e:
                self.node.get_logger().warning(f"⚠️ Error checking motion status: {e}")
                time.sleep(0.1)

        # Timeout
        self.node.get_logger().warning(f"⏰ Motion timeout after {max_wait_time}s")
        return MotionStatus.TIMEOUT

    def wait_for_motion_completion_simple(self, xbot_id: int, target_position: List[float],
                                          position_tolerance: float, max_wait_time: float = 10.0) -> MotionStatus:
        """
        Simple and robust motion completion waiting using string states.
        """
        start_time = time.time()
        last_log_time = start_time

        while time.time() - start_time < max_wait_time:
            try:
                # Get current state as string
                state_str = self.get_xbot_state_string(xbot_id)
                elapsed_time = time.time() - start_time

                # Log progress every 1 second
                if time.time() - last_log_time > 1.0:
                    self.node.get_logger().info(
                        f"🔄 XBot {xbot_id} motion: {state_str} (t={elapsed_time:.1f}s)")
                    last_log_time = time.time()

                # Check if motion completed
                if state_str in ["XBOT_IDLE", "IDLE"]:
                    self.node.get_logger().info(
                        f"✅ XBot {xbot_id} motion completed in {elapsed_time:.2f}s")
                    return MotionStatus.COMPLETED

                # Check for error states
                elif state_str in ["XBOT_ERROR", "ERROR", "XBOT_STOPPED", "XBOT_OBSTACLE_DETECTED"]:
                    self.node.get_logger().error(
                        f"❌ XBot {xbot_id} motion error - State: {state_str}")
                    return MotionStatus.ERROR

                # Continue waiting for motion states
                time.sleep(0.1)

            except Exception as e:
                self.node.get_logger().warning(f"⚠️ Error checking motion status: {e}")
                time.sleep(0.1)

        # Timeout
        self.node.get_logger().warning(f"⏰ XBot {xbot_id} motion timeout after {max_wait_time}s")
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
            # Handle XbotState enum values
            if hasattr(XbotState, 'XBOT_IDLE') and xbot_state == XbotState.XBOT_IDLE:
                return MotionStatus.IDLE
            elif hasattr(XbotState, 'XBOT_MOTION') and xbot_state == XbotState.XBOT_MOTION:
                return MotionStatus.MOVING
            elif hasattr(XbotState, 'XBOT_WAIT') and xbot_state == XbotState.XBOT_WAIT:
                return MotionStatus.MOVING
            elif hasattr(XbotState, 'XBOT_STOPPING') and xbot_state == XbotState.XBOT_STOPPING:
                return MotionStatus.MOVING
            elif hasattr(XbotState, 'XBOT_ERROR') and xbot_state == XbotState.XBOT_ERROR:
                return MotionStatus.ERROR
            elif hasattr(XbotState, 'XBOT_STOPPED') and xbot_state == XbotState.XBOT_STOPPED:
                return MotionStatus.ERROR
            elif hasattr(XbotState, 'XBOT_OBSTACLE_DETECTED') and xbot_state == XbotState.XBOT_OBSTACLE_DETECTED:
                return MotionStatus.ERROR
            elif hasattr(XbotState, 'XBOT_HOLDPOSITION') and xbot_state == XbotState.XBOT_HOLDPOSITION:
                return MotionStatus.ERROR
            elif hasattr(XbotState, 'XBOT_DISABLED') and xbot_state == XbotState.XBOT_DISABLED:
                return MotionStatus.ERROR
            elif hasattr(XbotState, 'XBOT_UNDETECTED') and xbot_state == XbotState.XBOT_UNDETECTED:
                return MotionStatus.ERROR
            elif hasattr(XbotState, 'XBOT_LANDED') and xbot_state == XbotState.XBOT_LANDED:
                return MotionStatus.IDLE
            else:
                # Fallback: try integer comparison
                state_int = int(xbot_state) if hasattr(xbot_state, '__int__') else xbot_state
                
                if state_int == 3:  # XBOT_IDLE
                    return MotionStatus.IDLE
                elif state_int == 5:  # XBOT_MOTION
                    return MotionStatus.MOVING
                elif state_int == 6:  # XBOT_WAIT
                    return MotionStatus.MOVING
                elif state_int == 7:  # XBOT_STOPPING
                    return MotionStatus.MOVING
                elif state_int in [2]:  # XBOT_LANDED
                    return MotionStatus.IDLE
                elif state_int in [14, 10, 8, 9, 4, 0]:  # ERROR states
                    return MotionStatus.ERROR
                else:
                    # Log unknown state for debugging
                    self.node.get_logger().debug(
                        f"🔧 Unknown XBot state: {xbot_state} (value: {state_int})")
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
        if not status_info:
            return
            
        current_pos = status_info.get('position')
        if not current_pos or len(current_pos) < 6:
            return
            
        xbot_state_str = status_info.get('xbot_state_string', 'UNKNOWN')
        buffered_count = status_info.get('buffered_motion_count', 0)

        if len(target_position) >= 6:
            pos_errors = [target_position[i] - current_pos[i]
                          for i in range(6)]

            self.node.get_logger().debug(
                f"🎯 XBot {xbot_id} progress ({elapsed_time:.1f}s):\n"
                f"  State: {xbot_state_str}, Buffered: {buffered_count}\n"
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
