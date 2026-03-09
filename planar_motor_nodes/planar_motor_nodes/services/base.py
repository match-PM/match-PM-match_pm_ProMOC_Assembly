"""Compatibility wrapper for legacy service base module path."""

from .handlers.base import (
    InvalidParameterError,
    ParameterValidationError,
    PositionOutOfBoundsError,
    ServiceCallbacksBase,
    ServiceRegistration,
)


__all__ = [
    "InvalidParameterError",
    "ParameterValidationError",
    "PositionOutOfBoundsError",
    "ServiceCallbacksBase",
    "ServiceRegistration",
]
