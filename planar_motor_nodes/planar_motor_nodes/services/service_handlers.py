"""Compatibility wrapper for legacy service registry module path."""

from .registry import SERVICE_REGISTRY, ServiceCallbacks, ServiceHandlers


__all__ = [
    "SERVICE_REGISTRY",
    "ServiceCallbacks",
    "ServiceHandlers",
]
