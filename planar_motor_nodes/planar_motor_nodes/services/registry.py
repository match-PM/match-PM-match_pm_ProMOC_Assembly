"""Service registry for planar motor callbacks."""

from __future__ import annotations

from .base import ServiceRegistration
from .control import ControlCallbacks
from .motion import MotionCallbacks


SERVICE_REGISTRY: tuple[ServiceRegistration, ...] = (
    ServiceRegistration("linear_motion_si", "callback_linear_motion_si", "motion"),
    ServiceRegistration("six_dof_motion", "callback_six_d_motion", "motion"),
    ServiceRegistration("activate_xbots", "callback_activate_xbot", "control"),
    ServiceRegistration("levitation_xbots", "callback_levitation_xbot", "control"),
    ServiceRegistration("arc_motion_si", "callback_arc_motion_si", "motion"),
    ServiceRegistration("stop_motion", "callback_stop_motion", "control"),
    ServiceRegistration("rotary_motion", "callback_rotary_motion", "motion"),
    ServiceRegistration(
        "set_velocity_acceleration",
        "callback_set_velocity_acceleration",
        "control",
    ),
)


class ServiceHandlers:
    """Compose planar motor services behind one small registry."""

    def __init__(self, logger, driver, mover_utils, config):
        self._motion = MotionCallbacks(logger, driver, mover_utils, config)
        self._control = ControlCallbacks(logger, driver, mover_utils, config)
        self._callback_map = {
            registration.service_name: (
                self._resolve_callback(registration.callback_name),
                registration.group,
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
        return self._callback_map[service_name][0]

    def get_group(self, service_name: str) -> str:
        return self._callback_map[service_name][1]

    def iter_service_registry(self):
        for registration in SERVICE_REGISTRY:
            yield registration


ServiceCallbacks = ServiceHandlers
