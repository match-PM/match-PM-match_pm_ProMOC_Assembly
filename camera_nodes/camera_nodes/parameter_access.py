"""Shared typed access helpers for ROS parameters."""

from __future__ import annotations


class ParameterAccessor:
    """Small adapter to centralize typed ROS parameter reads."""

    def __init__(self, node):
        self._node = node

    def raw(self, name: str, default=None):
        if not self._node.has_parameter(name):
            return default
        value = self._node.get_parameter(name).value
        if value is None:
            return default
        return value

    def as_float(self, name: str, default: float) -> float:
        value = self.raw(name, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def as_int(self, name: str, default: int) -> int:
        value = self.raw(name, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def as_str(self, name: str, default: str = "") -> str:
        value = self.raw(name, default)
        try:
            return str(value)
        except Exception:
            return str(default)

    def as_bool(self, name: str, default: bool = False) -> bool:
        value = self.raw(name, default)
        try:
            return bool(value)
        except Exception:
            return bool(default)
