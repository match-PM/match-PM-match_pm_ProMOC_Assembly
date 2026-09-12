"""Pure motion-input processing helpers for planar motor services."""

from __future__ import annotations

from dataclasses import dataclass
import math

from promoc_core import error_codes
from promoc_core.promoc_exceptions import ConfigurationError

from ..models import XBotPose


@dataclass(frozen=True)
class ProcessedMotionInput:
    """Normalized motion request used for backend dispatch."""

    xbot_id: int
    absolute_target: XBotPose
    relative_target: XBotPose | None = None


def process_six_dof_request(
    request,
    current_pose: XBotPose,
    no_change: float,
) -> ProcessedMotionInput:
    """Normalize the 6-DOF request into an absolute target pose.

    Jeder Achsenwert wird geprueft: Bei NO_CHANGE (-999999.0) bleibt die
    aktuelle Position erhalten. Ansonsten Umrechnung von mm nach m (XYZ)
    bzw. von Grad nach Radiant (RX, RY, RZ).
    """
    xbot_id = _validated_xbot_id(request.xbot_id)
    target = XBotPose(
        x=_optional_mm(request.x_pos, current_pose.x, no_change),
        y=_optional_mm(request.y_pos, current_pose.y, no_change),
        z=_optional_mm(request.z_pos, current_pose.z, no_change),
        rx=_optional_deg(request.rx_pos, current_pose.rx, no_change),
        ry=_optional_deg(request.ry_pos, current_pose.ry, no_change),
        rz=_optional_deg(request.rz_pos, current_pose.rz, no_change),
    )
    return ProcessedMotionInput(xbot_id=xbot_id, absolute_target=target)


def process_linear_request(request) -> ProcessedMotionInput:
    """Normalize the linear absolute request.

    Reine XY-Bewegung: X/Y von mm nach m umrechnen, Z konstant auf 0.001 m
    (Schwebehoehe), Rotationen auf 0.
    """
    xbot_id = _validated_xbot_id(request.xbot_id)
    target = XBotPose(
        x=(request.x_pos, "x_pos") / 1000.0,
        y=(request.y_pos, "y_pos") / 1000.0,
        z=0.001,
        rx=0.0,
        ry=0.0,
        rz=0.0,
    )
    return ProcessedMotionInput(xbot_id=xbot_id, absolute_target=target)


def process_rotary_request(request, current_pose: XBotPose) -> ProcessedMotionInput:
    """Normalize the rotary request.

    Reine RZ-Rotation: target_rz von Grad nach Radiant umrechnen,
    alle anderen Achsen bleiben auf der aktuellen Position.
    Validiert zusaetzlich, dass max_rz_speed und max_accel_rz positiv sind.
    """
    xbot_id = _validated_xbot_id(request.xbot_id)
    if _require_finite(request.max_rz_speed, "max_rz_speed") <= 0.0:
        raise ConfigurationError(
            "max_rz_speed must be positive",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "max_rz_speed", "value": request.max_rz_speed},
        )
    if _require_finite(request.max_accel_rz, "max_accel_rz") <= 0.0:
        raise ConfigurationError(
            "max_accel_rz must be positive",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "max_accel_rz", "value": request.max_accel_rz},
        )
    target_rz = math.radians(_require_finite(request.target_rz, "target_rz"))
    target = XBotPose(
        x=current_pose.x,
        y=current_pose.y,
        z=current_pose.z,
        rx=current_pose.rx,
        ry=current_pose.ry,
        rz=target_rz,
    )
    return ProcessedMotionInput(xbot_id=xbot_id, absolute_target=target)


def process_arc_request(request, current_pose: XBotPose) -> ProcessedMotionInput:
    """Normalize the arc request into absolute and optional relative targets.

    Kreisbogen-Parameter:
    - pos_mode=1 -> relative Bewegung (relative_target gesetzt, absolute = current + delta)
    - pos_mode=0 -> absolute Bewegung (nur absolute_target)
    - radius, max_speed, max_accel muessen positiv sein
    - arc_mode, arc_type, arc_direction, pos_mode muessen 0 oder 1 sein
    """
    xbot_id = _validated_xbot_id(request.xbot_id)
    _validate_arc_mode(
        request.arc_mode,
        request.arc_type,
        request.arc_direction,
        request.pos_mode,
    )
    if _require_finite(request.radius, "radius") <= 0.0:
        raise ConfigurationError(
            "radius must be positive",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "radius", "value": request.radius},
        )
    if _require_finite(request.max_speed, "max_speed") <= 0.0:
        raise ConfigurationError(
            "max_speed must be positive",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "max_speed", "value": request.max_speed},
        )
    if _require_finite(request.max_accel, "max_accel") <= 0.0:
        raise ConfigurationError(
            "max_accel must be positive",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "max_accel", "value": request.max_accel},
        )
    relative = int(request.pos_mode) == 1
    target_x = _require_finite(request.target_x, "target_x") / 1000.0
    target_y = _require_finite(request.target_y, "target_y") / 1000.0
    if relative:
        relative_target = XBotPose(target_x, target_y, 0.0, 0.0, 0.0, 0.0)
        absolute_target = current_pose.with_delta(relative_target)
    else:
        relative_target = None
        absolute_target = XBotPose(
            x=target_x,
            y=target_y,
            z=current_pose.z,
            rx=current_pose.rx,
            ry=current_pose.ry,
            rz=current_pose.rz,
        )
    return ProcessedMotionInput(
        xbot_id=xbot_id,
        absolute_target=absolute_target,
        relative_target=relative_target,
    )


def _validated_xbot_id(xbot_id: int) -> int:
    if int(xbot_id) < 0:
        raise ConfigurationError(
            f"XBot ID must be non-negative, got: {xbot_id}",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "xbot_id", "value": xbot_id},
        )
    return int(xbot_id)


def _require_finite(value: float, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ConfigurationError(
            f"{name} must be finite",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": name, "value": value},
        )
    return numeric


def _optional_mm(value: float, current: float, no_change: float) -> float:
    # NO_CHANGE-Sentinel: Behalte aktuelle Position, sonst mm -> m
    numeric = _require_finite(value, "position")
    if numeric == no_change:
        return current
    return numeric / 1000.0


def _optional_deg(value: float, current: float, no_change: float) -> float:
    # NO_CHANGE-Sentinel: Behalte aktuelle Rotation, sonst Grad -> Radiant
    numeric = _require_finite(value, "rotation")
    if numeric == no_change:
        return current
    return math.radians(numeric)


def _validate_arc_mode(
    arc_mode: int,
    arc_type: int,
    arc_direction: int,
    pos_mode: int,
) -> None:
    # Validiert, dass alle Arc-Steuerparameter gueltige Werte (0 oder 1) haben
    if int(arc_mode) not in {0, 1}:
        raise ConfigurationError(
            f"Invalid arc_mode: {arc_mode}",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "arc_mode", "value": arc_mode},
        )
    if int(arc_type) not in {0, 1}:
        raise ConfigurationError(
            f"Invalid arc_type: {arc_type}",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "arc_type", "value": arc_type},
        )
    if int(arc_direction) not in {0, 1}:
        raise ConfigurationError(
            f"Invalid arc_direction: {arc_direction}",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "arc_direction", "value": arc_direction},
        )
    if int(pos_mode) not in {0, 1}:
        raise ConfigurationError(
            f"Invalid pos_mode: {pos_mode}",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "pos_mode", "value": pos_mode},
        )
