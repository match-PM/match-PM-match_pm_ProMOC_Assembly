"""Pure motion-input processing helpers for planar motor services."""

from __future__ import annotations

from dataclasses import dataclass
import math

from promoc_core import error_codes
from promoc_core.promoc_exceptions import ConfigurationError

from ..models import XBotPose

InvalidParameterError = ConfigurationError
ParameterValidationError = ConfigurationError


@dataclass(frozen=True)
class ProcessedMotionInput:
    """Normalized motion request used for backend dispatch."""

    xbot_id: int
    absolute_target: XBotPose
    relative_target: XBotPose | None = None


def process_six_dof_request(request, current_pose: XBotPose, no_change: float) -> ProcessedMotionInput:
    """Normalize the 6-DOF request into an absolute target pose."""
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
    """Normalize the linear absolute request."""
    xbot_id = _validated_xbot_id(request.xbot_id)
    target = XBotPose(
        x=_require_finite(request.x_pos, "x_pos") / 1000.0,
        y=_require_finite(request.y_pos, "y_pos") / 1000.0,
        z=0.001,
        rx=0.0,
        ry=0.0,
        rz=0.0,
    )
    return ProcessedMotionInput(xbot_id=xbot_id, absolute_target=target)


def process_rotary_request(request, current_pose: XBotPose) -> ProcessedMotionInput:
    """Normalize the rotary request."""
    xbot_id = _validated_xbot_id(request.xbot_id)
    if _require_finite(request.max_rz_speed, "max_rz_speed") <= 0.0:
        raise InvalidParameterError(
            "max_rz_speed must be positive",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "max_rz_speed", "value": request.max_rz_speed},
        )
    if _require_finite(request.max_accel_rz, "max_accel_rz") <= 0.0:
        raise InvalidParameterError(
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
    """Normalize the arc request into absolute and optional relative targets."""
    xbot_id = _validated_xbot_id(request.xbot_id)
    _validate_arc_mode(request.arc_mode, request.arc_type, request.arc_direction, request.pos_mode)
    for name in ("radius", "max_speed", "max_accel"):
        if _require_finite(getattr(request, name), name) <= 0.0:
            raise InvalidParameterError(
                f"{name} must be positive",
                error_code=error_codes.INVALID_COMMAND,
                details={"parameter": name, "value": getattr(request, name)},
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
        raise ParameterValidationError(
            f"XBot ID must be non-negative, got: {xbot_id}",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": "xbot_id", "value": xbot_id},
        )
    return int(xbot_id)


def _require_finite(value: float, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidParameterError(
            f"{name} must be finite",
            error_code=error_codes.INVALID_COMMAND,
            details={"parameter": name, "value": value},
        )
    return numeric


def _optional_mm(value: float, current: float, no_change: float) -> float:
    numeric = _require_finite(value, "position")
    if numeric == no_change:
        return current
    return numeric / 1000.0


def _optional_deg(value: float, current: float, no_change: float) -> float:
    numeric = _require_finite(value, "rotation")
    if numeric == no_change:
        return current
    return math.radians(numeric)


def _validate_arc_mode(arc_mode: int, arc_type: int, arc_direction: int, pos_mode: int) -> None:
    valid_values = {
        "arc_mode": (arc_mode, {0, 1}),
        "arc_type": (arc_type, {0, 1}),
        "arc_direction": (arc_direction, {0, 1}),
        "pos_mode": (pos_mode, {0, 1}),
    }
    for name, (value, allowed) in valid_values.items():
        if int(value) not in allowed:
            raise InvalidParameterError(
                f"Invalid {name}: {value}",
                error_code=error_codes.INVALID_COMMAND,
                details={"parameter": name, "value": value},
            )
