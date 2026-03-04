"""Axis service client management for autofocus handlers."""

from __future__ import annotations

import time

from promoc_assembly_interfaces.srv import (
    GetOperationStatus,
    GetPosition,
    GetVelocityParameters,
    SetVelocityParameters,
    JogAxis,
    MoveAbsolute,
    Stop,
)
from promoc_core.promoc_exceptions import ServiceError


class AxisClientManager:
    """Build and cache linear-axis service clients for autofocus workflows."""

    def __init__(self, callback_handler):
        self._handler = callback_handler
        self._cached_axis_clients: dict[str, object] = {}

    def get_all_axis_clients(self) -> dict[str, object]:
        """Create or return cached service clients for the configured linear axis."""
        if self._cached_axis_clients:
            return self._cached_axis_clients

        axis_name = self._handler._param_str("x_axis_node_name", "lts300_x_axis")
        axis_prefix = f"/promoc/linear_axis/{axis_name}"
        node = self._handler._node

        clients = {
            "move": node.create_client(MoveAbsolute, f"{axis_prefix}/move_absolute"),
            "jog": node.create_client(JogAxis, f"{axis_prefix}/jog_axis"),
            "status": node.create_client(
                GetOperationStatus, f"{axis_prefix}/get_operation_status"
            ),
            "position": node.create_client(GetPosition, f"{axis_prefix}/get_position"),
            "stop": node.create_client(Stop, f"{axis_prefix}/stop"),
            "get_vel": node.create_client(
                GetVelocityParameters, f"{axis_prefix}/get_velocity_parameters"
            ),
            "set_vel": node.create_client(
                SetVelocityParameters, f"{axis_prefix}/set_velocity_parameters"
            ),
        }

        for name, client in clients.items():
            if not client.wait_for_service(timeout_sec=2.0):
                raise ServiceError(f"Linear axis {name} service not available")

        self._cached_axis_clients = clients
        return clients

    def wait_for_axis_idle(self, clients: dict[str, object]) -> None:
        """Block until axis reports idle or raise on error states."""
        while True:
            response = clients["status"].call(GetOperationStatus.Request())
            if response and response.operation_status == "idle":
                return
            if response and response.operation_status in ["error", "emergency_stop"]:
                raise ServiceError(f"Axis error: {response.status_message}")
            time.sleep(0.05)

    def get_position(self, clients: dict[str, object]) -> float:
        """Read axis position from topic cache first, service as fallback."""
        node = self._handler._node
        if hasattr(node, "current_axis_position") and node.current_axis_position >= 0:
            return float(node.current_axis_position)

        response = clients["position"].call(GetPosition.Request())
        if response and response.success:
            return float(response.axis_position)
        return -1.0
