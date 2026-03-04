"""Service layer for planar motor node callbacks."""

from .base import ServiceCallbacksBase
from .motion import MotionCallbacks
from .control import ControlCallbacks


class ServiceCallbacks(MotionCallbacks, ControlCallbacks):
    """
    Combined service callbacks class.

    Inherits from MotionCallbacks and ControlCallbacks, which both
    inherit from ServiceCallbacksBase. This provides all callbacks
    in a single class for easy integration with the mover node.
    """

    pass


__all__ = [
    "ServiceCallbacks",
    "ServiceCallbacksBase",
    "MotionCallbacks",
    "ControlCallbacks",
]
