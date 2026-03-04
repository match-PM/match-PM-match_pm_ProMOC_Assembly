"""Composed entrypoint for planar motor service handlers."""

from __future__ import annotations

from .base import ServiceRegistration
from .control import ControlCallbacks
from .motion import MotionCallbacks


SERVICE_REGISTRY: tuple[ServiceRegistration, ...] = (
    ServiceRegistration("linear_motion_si", "callback_linear_motion_si"),
    ServiceRegistration("six_dof_motion", "callback_six_d_motion"),
    ServiceRegistration("activate_xbots", "callback_activate_xbot"),
    ServiceRegistration("levitation_xbots", "callback_levitation_xbot"),
    ServiceRegistration("arc_motion_si", "callback_arc_motion_si"),
    ServiceRegistration("stop_motion", "callback_stop_motion"),
    ServiceRegistration("rotary_motion", "callback_rotary_motion"),
    ServiceRegistration(
        "set_velocity_acceleration", "callback_set_velocity_acceleration"
    ),
)


class ServiceHandlers:
    """Composed mover service handlers with explicit registry wiring."""

    def __init__(self, logger, pmc_interface, mover_utils, config):
        self._motion = MotionCallbacks(
            logger,
            pmc_interface,
            mover_utils,
            config,
        )
        self._control = ControlCallbacks(
            logger,
            pmc_interface,
            mover_utils,
            config,
        )
        self._callback_map = {
            registration.service_name: self._resolve_callback(
                registration.callback_name
            )
            for registration in SERVICE_REGISTRY
        }

    def _resolve_callback(self, callback_name: str):
        if hasattr(self._motion, callback_name):
            return getattr(self._motion, callback_name)
        if hasattr(self._control, callback_name):
            return getattr(self._control, callback_name)
        raise AttributeError(f"Unknown callback '{callback_name}' in SERVICE_REGISTRY")

    def get_callback(self, service_name: str):
        """Return callback function for a canonical mover service name."""
        return self._callback_map[service_name]

    def iter_service_registry(self):
        """Iterate `(service_name, callback)` in canonical registration order."""
        for registration in SERVICE_REGISTRY:
            yield (
                registration.service_name,
                self._callback_map[registration.service_name],
            )

    def __getattr__(self, name: str):
        """Compatibility access for existing `callback_*` attribute lookups."""
        for registration in SERVICE_REGISTRY:
            if registration.callback_name == name:
                return self._callback_map[registration.service_name]
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Backward compatibility for imports still using ServiceCallbacks.
ServiceCallbacks = ServiceHandlers
