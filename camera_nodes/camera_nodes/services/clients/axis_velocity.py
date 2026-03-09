"""Helpers for linear-axis callback operations."""

from __future__ import annotations

from contextlib import contextmanager

from promoc_assembly_interfaces.srv import GetVelocityParameters, SetVelocityParameters
from promoc_core.promoc_exceptions import ServiceError


@contextmanager
def temporary_velocity(clients, max_velocity: float, backup=None):
    """Temporarily set max velocity and restore original values afterwards."""
    vel_backup = backup
    if vel_backup is None:
        vel_backup = clients["get_vel"].call(GetVelocityParameters.Request())
    if not vel_backup or not vel_backup.success:
        raise ServiceError("Failed to read velocity parameters")

    req = SetVelocityParameters.Request()
    req.min_velocity = vel_backup.min_velocity
    req.acceleration = vel_backup.acceleration
    req.max_velocity = float(max_velocity)
    clients["set_vel"].call(req)
    try:
        yield vel_backup
    finally:
        restore = SetVelocityParameters.Request()
        restore.min_velocity = vel_backup.min_velocity
        restore.acceleration = vel_backup.acceleration
        restore.max_velocity = vel_backup.max_velocity
        clients["set_vel"].call(restore)
