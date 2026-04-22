"""Validation helpers for linear-axis motion callbacks."""

from __future__ import annotations

from promoc_core.promoc_exceptions import (
    CollisionDetectedError,
    SoftLimitViolationError,
)
from promoc_core.validation import check_collision_risk, is_in_range

from ..config import LTS300NodeConfig


class LinearAxisValidator:
    """Encapsulate collision and soft-limit validation rules."""

    def __init__(self, config: LTS300NodeConfig, logger):
        self._config = config
        self._logger = logger

    def collision_check(self, other_axis_position: float, axis_position: float = 0.0):
        """Validate cross-axis collision risk."""
        is_safe, warning_msg = check_collision_risk(
            axis_position=axis_position,
            other_axis_position=other_axis_position,
            collision_threshold=self._config.collision_threshold,
        )

        if warning_msg:
            self._logger.warn(warning_msg)

        if not is_safe:
            raise CollisionDetectedError(
                f"Collision risk detected! Other axis at {other_axis_position:.2f}mm exceeds "
                f"threshold {self._config.collision_threshold}mm",
                details={
                    "other_axis_position": other_axis_position,
                    "collision_threshold": self._config.collision_threshold,
                    "axis_name": getattr(self._logger, "name", "lts300"),
                },
            )

    def validate_position(self, position: float):
        """Validate target position against configured soft limits."""
        min_position = self._config.min_position
        max_position = self._config.max_position

        if is_in_range(position, min_position, max_position):
            return

        if position < min_position:
            violation_type = "min_limit"
            msg = f"Position {position:.2f}mm below minimum limit {min_position:.2f}mm"
        else:
            violation_type = "max_limit"
            msg = (
                f"Position {position:.2f}mm exceeds maximum limit {max_position:.2f}mm"
            )

        raise SoftLimitViolationError(
            msg,
            details={
                "requested_position": position,
                "min_position": min_position,
                "max_position": max_position,
                "violation_type": violation_type,
            },
        )

    def validate_distance(self, distance: float):
        """Validate relative movement distance against max single move."""
        max_single_move = self._config.max_single_move
        abs_distance = abs(distance)
        if abs_distance <= max_single_move:
            return

        raise SoftLimitViolationError(
            f"Movement distance {abs_distance:.2f}mm exceeds maximum single move "
            f"limit {max_single_move:.2f}mm",
            details={
                "requested_distance": distance,
                "abs_distance": abs_distance,
                "max_single_move": max_single_move,
                "violation_type": "max_distance",
            },
        )

    def validate_target_position(self, current_pos: float, distance: float):
        """Validate target position implied by relative movement."""
        self.validate_position(current_pos + distance)
