"""Compatibility wrapper for legacy motion-input module path."""

from ..adapters.mapping import (
    InvalidParameterError,
    MotionInputConverters,
    MotionInputOptions,
    ParameterValidationError,
    ProcessedMotionInput,
    process_motion_input,
)


__all__ = [
    "InvalidParameterError",
    "MotionInputConverters",
    "MotionInputOptions",
    "ParameterValidationError",
    "ProcessedMotionInput",
    "process_motion_input",
]
