"""Small runtime models used by the planar-motor node."""

from __future__ import annotations

from dataclasses import dataclass

from promoc_core.status import DeviceState


@dataclass(frozen=True)
class XBotPose:
    """Cartesian XBot pose in SI units."""

    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float

    def with_delta(self, delta: "XBotPose") -> "XBotPose":
        """Return a new pose translated by ``delta``."""
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
    """Per-XBot speed parameters in SI units."""

    xy_vel: float
    xy_max_accel: float
    z_vel: float
    z_max_accel: float
    rx_vel: float
    ry_vel: float
    rz_vel: float


@dataclass(frozen=True)
class XBotSnapshot:
    """Current driver view of one XBot."""

    xbot_id: int
    pose: XBotPose | None
    raw_state: str
    device_state: DeviceState
    active: bool
    levitated: bool
    busy: bool
    error_code: int = 0
    message: str = ""
