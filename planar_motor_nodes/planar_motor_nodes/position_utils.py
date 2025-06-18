import time
import math
from typing import List


# Smart PMCLib import
from .pmclib_loader import bot, get_pmclib_status


class PositionUtils:
    """Utility-Klasse für Position-Management und Validierung"""

    def __init__(self, node):
        self.node = node

        pmclib_status = get_pmclib_status()
        self.is_mock = pmclib_status['is_mock']

    def get_current_position(self, xbot_id: int = 0) -> List[float]:
        """Get current XBot position."""
        try:
            xbot_data_list = bot.get_all_xbot_info(xbot_id)
            if not xbot_data_list:
                self.node.get_logger().error("❌ Error: xbot_data_list is empty")
                return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

            return [
                float(xbot_data_list[0].x_pos),
                float(xbot_data_list[0].y_pos),
                float(xbot_data_list[0].z_pos),
                float(xbot_data_list[0].rx_pos),
                float(xbot_data_list[0].ry_pos),
                float(xbot_data_list[0].rz_pos)
            ]
        except (IndexError, AttributeError) as e:
            self.node.get_logger().error(f"❌ Error getting position: {e}")
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def check_position_reached(self, target_position: List[float],
                               tolerance: float, max_wait_time: float = 2.0,
                               xbot_id: int = 0) -> bool:
        """Check if target position is reached within tolerance and timeout."""

        def is_within_tolerance(current_pos: List[float]) -> bool:
            for i in range(min(len(target_position), len(current_pos))):
                if abs(target_position[i] - current_pos[i]) > tolerance:
                    return False
            return True

        start_time = time.time()
        check_interval = 0.1

        while time.time() - start_time < max_wait_time:
            current_position = self.get_current_position(xbot_id)

            if is_within_tolerance(current_position):
                return True

            time.sleep(check_interval)

        self.node.get_logger().warning(
            f"⚠️ Timeout! Target position not reached: {target_position}")
        return False

    def is_position_in_bounds(self, x: float, y: float, z: float) -> bool:
        """Check if position is within defined boundaries."""
        return (self.node.x_min <= x <= self.node.x_max and
                self.node.y_min <= y <= self.node.y_max and
                self.node.z_min <= z <= self.node.z_max)

    def convert_mm_to_meters(self, positions: List[float]) -> List[float]:
        """Convert position values from millimeters to meters."""
        return [pos / 1000.0 for pos in positions]

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
        # Check XYZ bounds
        if not self.is_position_in_bounds(x, y, z):
            self.node.get_logger().error(
                f"❌ Position outside valid range: ({x:.3f}, {y:.3f}, {z:.3f})")
            return False

        # Check rotation bounds (simplified)
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

        r = (mover_width / 2) * math.sqrt(2) / 1000.0  # Convert mm to m
        max_rotation = math.atan(r / z_value) * safety_factor
        return max_rotation

    def constrain_position_to_bounds(self, current_pos: List[float],
                                     target_pos: List[float]) -> List[float]:
        """Constrain target position to valid bounds, use current position as fallback."""
        constrained = target_pos.copy()

        # Constrain X
        if not (self.node.x_min <= target_pos[0] <= self.node.x_max):
            constrained[0] = current_pos[0]
            self.node.get_logger().warning(
                f"⚠️ X position {target_pos[0]:.3f} out of bounds, using current: {current_pos[0]:.3f}")

        # Constrain Y
        if not (self.node.y_min <= target_pos[1] <= self.node.y_max):
            constrained[1] = current_pos[1]
            self.node.get_logger().warning(
                f"⚠️ Y position {target_pos[1]:.3f} out of bounds, using current: {current_pos[1]:.3f}")

        # Constrain Z
        if not (self.node.z_min <= target_pos[2] <= self.node.z_max):
            constrained[2] = current_pos[2]
            self.node.get_logger().warning(
                f"⚠️ Z position {target_pos[2]:.3f} out of bounds, using current: {current_pos[2]:.3f}")

        # Constrain rotations based on Z value
        if len(target_pos) >= 6:
            max_rotation = self.calculate_max_rotation(constrained[2])

            for i, axis in enumerate(['RX', 'RY'], start=3):
                if abs(target_pos[i]) > max_rotation:
                    constrained[i] = current_pos[i]
                    self.node.get_logger().warning(
                        f"⚠️ {axis} rotation {target_pos[i]:.3f} out of bounds, using current: {current_pos[i]:.3f}")

        return constrained
