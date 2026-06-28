"""Abstract driver contract shared by hardware and mock linear axes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class LinearAxisDriver(ABC):
    """Abstrakte Treiberschnittstelle fuer Linearachsen.

    Trennt die ROS-Knotenlogik von der Hardware/Mock-Implementierung.
    Alle Positionsangaben in Millimetern, Geschwindigkeiten in mm/s.
    """

    @abstractmethod
    def connect(self, port: str = None) -> bool:
        """Mit dem Achsengeraet verbinden."""

    @abstractmethod
    def disconnect(self) -> None:
        """Verbindung trennen."""

    @abstractmethod
    def move_absolute(self, position: float, timeout: Optional[float] = None) -> None:
        """Absolute Position in mm anfahren."""

    @abstractmethod
    def move_relative(self, distance: float, timeout: Optional[float] = None) -> None:
        """Relative Strecke in mm fahren."""

    @abstractmethod
    def jog(self, step_size: float, timeout: Optional[float] = None) -> None:
        """Jog um signierten Schritt in mm (step_mode)."""

    @abstractmethod
    def home(self, timeout: float = 180.0) -> None:
        """Achse homed (Referenzfahrt)."""

    @abstractmethod
    def stop(self) -> None:
        """Aktuelle Bewegung sofort stoppen."""

    @abstractmethod
    def get_position(self) -> float:
        """Aktuelle Position in mm abrufen."""

    @abstractmethod
    def is_moving(self) -> bool:
        """Prueft ob die Achse gerade in Bewegung ist."""

    @abstractmethod
    def get_serial_number(self) -> str:
        """Seriennummer des Geraets abrufen."""

    @abstractmethod
    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """(min_velocity, acceleration, max_velocity) in mm/s bzw. mm/s^2 abrufen."""

    @abstractmethod
    def set_velocity_parameters(
        self,
        min_velocity: Optional[float] = None,
        acceleration: Optional[float] = None,
        max_velocity: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Geschwindigkeitsparameter setzen, gibt angewandte Werte zurueck."""
