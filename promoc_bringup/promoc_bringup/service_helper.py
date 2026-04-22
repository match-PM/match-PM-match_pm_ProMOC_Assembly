#!/usr/bin/env python3
"""Service helper utilities for ProMOC bringup."""

from __future__ import annotations

import time
from typing import Any, Optional

import rclpy
from rclpy.node import Node

from promoc_core.logging import LogTags, TaggedLogger


class ServiceHelper:
    """Helper for consistent ROS2 service-call handling."""

    def __init__(self, node: Node):
        self.node = node
        self.logger = TaggedLogger(node.get_logger(), LogTags.SYS)

    def call_service(
        self,
        client,
        request,
        success_msg: str,
        error_msg: str,
        timeout_sec: float = 10.0,
        wait_for_service_sec: float = 2.0,
    ) -> Optional[Any]:
        """Call a service with unified waiting, timeout and logging."""
        if not client.wait_for_service(timeout_sec=wait_for_service_sec):
            self.logger.error(
                f'Service "{client.srv_name}" not available. Skipping call.'
            )
            return None

        try:
            future = client.call_async(request)
            rclpy.spin_until_future_complete(
                self.node,
                future,
                timeout_sec=timeout_sec,
            )

            result = future.result()
            if result is None:
                self.logger.error(f"{error_msg}: No response received")
                return None

            if self.was_successful(result):
                self.logger.info(success_msg)
            else:
                status_msg = getattr(result, "status_message", "Unknown error")
                self.logger.error(f"{error_msg}: {status_msg}")

            return result

        except Exception as exc:
            self.logger.error(f'Exception calling "{client.srv_name}": {exc}')
            return None

    def was_successful(self, result: Any) -> bool:
        """Return whether a response object indicates success."""
        if result is None:
            return False
        if hasattr(result, "success"):
            return bool(result.success)
        return True

    def wait_for_services(
        self,
        clients_with_names: list,
        timeout_per_service: float = 10.0,
    ) -> bool:
        """Wait for all services to become available.

        Args:
            clients_with_names: Sequence of ``(client, readable_name)`` tuples.
            timeout_per_service: Seconds to wait per service. ``<= 0`` means wait forever.
        """
        for client, name in clients_with_names:
            self.logger.info(f"Waiting for {name} service...")

            deadline = None
            if timeout_per_service > 0:
                deadline = time.monotonic() + timeout_per_service

            while not client.wait_for_service(timeout_sec=1.0):
                if not rclpy.ok():
                    return False

                if deadline is not None and time.monotonic() >= deadline:
                    self.logger.error(
                        f"Timeout waiting for service {name} "
                        f"after {timeout_per_service:.1f}s."
                    )
                    return False

                self.logger.info(f"Service {name} not available yet, waiting...")

            self.logger.info(f"Service {name} is ready.")

        return True
