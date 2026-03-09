"""Pure motion-input processing helpers for planar motor services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from promoc_core.promoc_exceptions import ConfigurationError

InvalidParameterError = ConfigurationError
ParameterValidationError = ConfigurationError


@dataclass(frozen=True)
class MotionInputConverters:
    """Unit-conversion functions required by motion input processing."""

    mm_to_m: Callable[[float], float]
    deg_to_rad: Callable[[float], float]


@dataclass(frozen=True)
class MotionInputOptions:
    """Static options controlling motion input processing behavior."""

    no_change: float = -999999.0
    default_position: tuple[float, float, float, float, float, float] = (
        0.1,
        0.1,
        0.001,
        0.0,
        0.0,
        0.0,
    )


@dataclass(frozen=True)
class ProcessedMotionInput:
    """Normalized motion input used for backend command dispatch."""

    target_position: list[float]
    current_position: list[float]


def process_motion_input(
    request,
    *,
    motion_type: str,
    converters: MotionInputConverters,
    options: MotionInputOptions,
    get_current_position: Callable[[int], Sequence[float] | None] | None = None,
    current_position: Sequence[float] | None = None,
) -> ProcessedMotionInput:
    """Validate and normalize motion request data into SI-unit target positions."""
    _validate_base_params(request)
    _validate_motion_type_params(request, motion_type)

    if current_position is None:
        current_position = _resolve_current_position(
            request,
            options=options,
            get_current_position=get_current_position,
        )

    current = [float(v) for v in current_position]
    target = current[:]

    if motion_type == "linear":
        target[0] = converters.mm_to_m(float(request.x_pos))
        target[1] = converters.mm_to_m(float(request.y_pos))
        target[2] = 0.001
    elif motion_type == "6dof":
        target[0] = _value_or_current(
            float(request.x_pos),
            current[0],
            options=options,
            convert=converters.mm_to_m,
        )
        target[1] = _value_or_current(
            float(request.y_pos),
            current[1],
            options=options,
            convert=converters.mm_to_m,
        )
        target[2] = _value_or_current(
            float(request.z_pos),
            current[2],
            options=options,
            convert=converters.mm_to_m,
        )
        target[3] = _value_or_current(
            float(request.rx_pos),
            current[3],
            options=options,
            convert=converters.deg_to_rad,
        )
        target[4] = _value_or_current(
            float(request.ry_pos),
            current[4],
            options=options,
            convert=converters.deg_to_rad,
        )
        target[5] = _value_or_current(
            float(request.rz_pos),
            current[5],
            options=options,
            convert=converters.deg_to_rad,
        )
    elif motion_type == "rotary":
        target[5] = converters.deg_to_rad(float(request.target_rz))
    elif motion_type == "arc_si":
        target[0] = converters.mm_to_m(float(request.target_x))
        target[1] = converters.mm_to_m(float(request.target_y))
    elif motion_type == "arc":
        target[0] = converters.mm_to_m(float(request.x_pos))
        target[1] = converters.mm_to_m(float(request.y_pos))
    else:
        raise ValueError(f"Unknown motion type: {motion_type}")

    return ProcessedMotionInput(target_position=target, current_position=current)


def _validate_base_params(request) -> None:
    if hasattr(request, "xbot_id") and request.xbot_id < 0:
        raise ParameterValidationError(
            f"XBot ID must be non-negative, got: {request.xbot_id}",
            details={
                "parameter": "xbot_id",
                "value": request.xbot_id,
                "constraint": "non-negative",
            },
        )


def _validate_motion_type_params(request, motion_type: str) -> None:
    if motion_type == "rotary":
        if hasattr(request, "rot_mode") and request.rot_mode not in [0, 1, 2]:
            raise ParameterValidationError(
                f"Invalid rot_mode: {request.rot_mode}. Valid: 0, 1, 2",
                details={"parameter": "rot_mode", "value": request.rot_mode},
            )
        if hasattr(request, "max_rz_speed") and request.max_rz_speed <= 0:
            raise ParameterValidationError(
                f"Max RZ speed must be positive, got: {request.max_rz_speed}",
                details={"parameter": "max_rz_speed", "value": request.max_rz_speed},
            )
        if hasattr(request, "max_accel_rz") and request.max_accel_rz <= 0:
            raise ParameterValidationError(
                (
                    "Max RZ acceleration must be positive, got: "
                    f"{request.max_accel_rz}"
                ),
                details={
                    "parameter": "max_accel_rz",
                    "value": request.max_accel_rz,
                },
            )

    if motion_type in {"arc", "arc_si"}:
        _validate_arc_params(request)


def _validate_arc_params(request) -> None:
    enum_validations = [
        ("arc_mode", [0, 1, 2], "arc_mode"),
        ("arc_type", [0, 1], "arc_type"),
        ("arc_direction", [0, 1], "arc_direction"),
        ("pos_mode", [0, 1], "pos_mode"),
    ]

    for attr, valid_values, name in enum_validations:
        if hasattr(request, attr) and getattr(request, attr) not in valid_values:
            raise InvalidParameterError(
                f"Invalid {name}: {getattr(request, attr)}. Valid: {valid_values}",
                details={"parameter": name, "value": getattr(request, attr)},
            )

    for param in ["radius", "max_speed", "max_accel"]:
        if hasattr(request, param) and getattr(request, param) <= 0:
            raise InvalidParameterError(
                f"{param} must be positive, got: {getattr(request, param)}",
                details={"parameter": param, "value": getattr(request, param)},
            )


def _resolve_current_position(
    request,
    *,
    options: MotionInputOptions,
    get_current_position: Callable[[int], Sequence[float] | None] | None,
) -> list[float]:
    if get_current_position is not None and hasattr(request, "xbot_id"):
        fetched = get_current_position(int(request.xbot_id))
        if fetched is not None:
            values = [float(v) for v in fetched]
            if len(values) >= 6:
                return values[:6]

    return list(options.default_position)


def _value_or_current(
    incoming: float,
    current: float,
    *,
    options: MotionInputOptions,
    convert: Callable[[float], float],
) -> float:
    if incoming == options.no_change:
        return current
    return float(convert(incoming))


__all__ = [
    "InvalidParameterError",
    "MotionInputConverters",
    "MotionInputOptions",
    "ParameterValidationError",
    "ProcessedMotionInput",
    "process_motion_input",
]
