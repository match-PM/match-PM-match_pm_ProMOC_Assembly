"""
Callbacks Package for Planar Motor Node.

This package contains the service callbacks split into logical modules:

- base: Base class with shared utilities and input processing
- motion: Motion callbacks (linear, 6dof, rotary, arc)
- control: Control callbacks (activate, levitate, stop, velocity)
"""

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
