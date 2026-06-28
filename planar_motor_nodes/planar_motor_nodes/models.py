"""Small runtime models used by the planar-motor node."""

from __future__ import annotations

from dataclasses import dataclass

from promoc_core.status import DeviceState


@dataclass(frozen=True)
class XBotPose:
    """Cartesian XBot pose in SI units.

    Positionen in Metern (x, y, z), Rotationen in Radiant (rx, ry, rz).
    """

    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float

    def with_delta(self, delta: "XBotPose") -> "XBotPose":
        """Return a new pose translated by ``delta``.

        Addiert delta komponentenweise zur aktuellen Pose -- wird fuer
        relative Bewegungen verwendet.
        """
        return XBotPose(
            x=self.x + delta.x,
            y=self.y + delta.y,
            z=self.z + delta.z,
            rx=self.rx + delta.rx,
            ry=self.ry + delta.ry,
            rz=self.rz + delta.rz,
        )


@dataclass(frozen=True)
class SpeedProfile:
    """Per-XBot speed parameters in SI units.

    Geschwindigkeiten in m/s (xy_vel, z_vel) und rad/s (rx/ry/rz_vel).
    Beschleunigungen in m/s^2 (xy/z_max_accel).
    """

    xy_vel: float
    xy_max_accel: float
    z_vel: float
    z_max_accel: float
    rx_vel: float
    ry_vel: float
    rz_vel: float


@dataclass(frozen=True)
class XBotSnapshot:
    """Current driver view of one XBot.

    Momentaufnahme eines XBots vom Treiber:
    - pose: aktuelle Pose (None wenn nicht verfuegbar)
    - raw_state: Roh-Zustandsstring vom Treiber (z.B. "XBOT_MOTION")
    - device_state: normalisierter DeviceState (READY, BUSY, ERROR, etc.)
    - active: XBot ist aktiviert
    - levitated: XBot schwebt (Levitation an)
    - busy: XBot fuehrt gerade eine Bewegung aus
    - error_code: Fehlercode (0 = SUCCESS)
    - message: Zustandsbeschreibung
    """

    xbot_id: int
    pose: XBotPose | None
    raw_state: str
    device_state: DeviceState
    active: bool
    levitated: bool
    busy: bool
    error_code: int = 0
    message: str = ""
