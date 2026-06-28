"""Small internal driver contract for planar-motor control."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from ..models import SpeedProfile, XBotPose, XBotSnapshot


class PlanarMotorDriver(ABC):
    """Minimal driver boundary used by the planar-motor node."""

    @abstractmethod
    def connect(self, controller_address: str) -> None:
        """Connect to the planar-motor controller."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the planar-motor controller."""

    @abstractmethod
    def list_xbot_ids(self) -> list[int]:
        """Return the currently discoverable XBot identifiers."""

    @abstractmethod
    def activate_xbots(self, xbot_ids: Sequence[int] | None = None) -> None:
        """Activate one or more XBots."""

    @abstractmethod
    def deactivate_xbots(self, xbot_ids: Sequence[int] | None = None) -> None:
        """Deactivate one or more XBots."""

    @abstractmethod
    def set_levitation(
        self, xbot_ids: Sequence[int] | None = None, enabled: bool = True
    ) -> None:
        """Enable or disable levitation for one or more XBots."""

    @abstractmethod
    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        """Return the current XBot snapshot."""

    @abstractmethod
    def move_linear_absolute(
        self,
        xbot_id: int,
        target_x: float,
        target_y: float,
        speed: SpeedProfile,
    ) -> float | None:
        """Start an absolute XY motion and return an estimated travel time."""

    @abstractmethod
    def move_six_dof_absolute(
        self,
        xbot_id: int,
        target_pose: XBotPose,
        speed: SpeedProfile,
    ) -> float | None:
        """Start an absolute 6-DOF motion and return an estimated travel time."""

    @abstractmethod
    def arc_move(
        self,
        xbot_id: int,
        target_x: float,
        target_y: float,
        radius_m: float,
        max_speed: float,
        max_accel: float,
        *,
        relative: bool,
        final_speed: float,
        arc_mode: int,
        arc_type: int,
        arc_direction: int,
        angle_rad: float,
    ) -> float | None:
        """Start an arc move and return an estimated travel time."""

    @abstractmethod
    def rotate(
        self,
        xbot_id: int,
        target_rz: float,
        max_speed: float,
        max_accel: float,
        mode: int,
    ) -> float | None:
        """Start a rotary move and return an estimated travel time."""

    @abstractmethod
    def stop(self, xbot_id: int) -> None:
        """Stop motion for a single XBot."""

    @abstractmethod
    def stop_all(self) -> None:
        """Stop all controlled XBots."""
