"""Small internal driver contract for planar-motor control."""

from __future__ import annotations

from abc import ABC, abstractmethod
from ..models import SpeedProfile, XBotPose, XBotSnapshot


class PlanarMotorDriver(ABC):
    """Minimal driver boundary used by the planar-motor node.

    Abstrakte Schnittstelle, die alle Treiberimplementierungen erfuellen muessen.
    Trennt die ROS-Logik sauber von der Hardware/Mock-Implementierung.
    """

    @abstractmethod
    def connect(self, controller_address: str) -> None:
        """Verbindung zum Planarmotor-Controller aufbauen."""

    @abstractmethod
    def disconnect(self) -> None:
        """Verbindung zum Planarmotor-Controller trennen."""

    @abstractmethod
    def list_xbot_ids(self) -> list[int]:
        """Liste aller verfuegbaren XBot-IDs vom Controller abrufen."""

    @abstractmethod
    def activate_xbots(self) -> None:
        """Einen oder mehrere XBots aktivieren."""

    @abstractmethod
    def deactivate_xbots(self) -> None:
        """Einen oder mehrere XBots deaktivieren."""

    @abstractmethod
    def set_levitation(self, xbot_id: int, enabled: bool = True) -> None:
        """Levitation (Schwebezustand) fuer XBots ein-/ausschalten."""

    @abstractmethod
    def get_snapshot(self, xbot_id: int) -> XBotSnapshot:
        """Aktuellen Zustand (Pose, Status, Flags) eines XBots abrufen."""

    @abstractmethod
    def move_linear_absolute(
        self,
        xbot_id: int,
        target_x: float,
        target_y: float,
        speed: SpeedProfile,
    ) -> float | None:
        """Absolute XY-Linearbewegung starten, geschaetzte Fahrzeit zurueckgeben."""

    @abstractmethod
    def move_six_dof_absolute(
        self,
        xbot_id: int,
        target_pose: XBotPose,
        speed: SpeedProfile,
    ) -> float | None:
        """Absolute 6-DOF-Bewegung starten, geschaetzte Fahrzeit zurueckgeben."""

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
        """Kreisbogenbewegung starten, geschaetzte Fahrzeit zurueckgeben."""

    @abstractmethod
    def rotate(
        self,
        xbot_id: int,
        target_rz: float,
        max_speed: float,
        max_accel: float,
        mode: int,
    ) -> float | None:
        """Rotationsbewegung um Z-Achse starten, geschaetzte Fahrzeit zurueckgeben."""

    @abstractmethod
    def stop(self, xbot_id: int) -> None:
        """Einzelnen XBot sofort stoppen."""

    @abstractmethod
    def stop_all(self) -> None:
        """Alle XBots sofort stoppen."""
