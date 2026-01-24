#!/usr/bin/env python3
"""
Service Helper for ProMOC Bringup

Provides reusable helper functions for consistent ROS2 service calls.
Centralizes boilerplate code: waiting, timeouts, error handling, logging.

Usage:
    from promoc_bringup.service_helper import ServiceHelper
    helper = ServiceHelper(node)
    helper.call_service(client, request, "Success", "Failed")
"""

import rclpy
from rclpy.node import Node
from typing import Optional, Any, Callable

from promoc_core.logging import TaggedLogger, LogTags


class ServiceHelper:
    """
    Helper class for calling ROS2 services with consistent error handling.

    Encapsulates common patterns:
    - Wait for service availability
    - Service call with timeout
    - Unified logging for success/failure
    - Exception handling
    """

    def __init__(self, node: Node):
        """
        Initialize with a ROS2 node.

        Args:
            node: ROS2 Node instance for logging and spinning.
        """
        self.node = node
        self.logger = TaggedLogger(node.get_logger(), LogTags.SYS)

    def call_service(
        self,
        client,
        request,
        success_msg: str,
        error_msg: str,
        timeout_sec: float = 10.0,
        wait_for_service_sec: float = 2.0
    ) -> Optional[Any]:
        """
        Call a ROS2 service with clean error handling.

        Process:
            1. Wait for service availability
            2. Call service asynchronously
            3. Spin until response or timeout
            4. Log and return result

        Args:
            client: ROS2 service client
            request: Request message
            success_msg: Log message on success
            error_msg: Log message on failure
            timeout_sec: Call timeout in seconds (default: 10s)
            wait_for_service_sec: Service availability timeout (default: 2s)

        Returns:
            Service response or None on failure
        """
        if not client.wait_for_service(timeout_sec=wait_for_service_sec):
            self.logger.error(
                f'Service "{client.srv_name}" not available. Skipping call.'
            )
            return None

        try:
            future = client.call_async(request)
            rclpy.spin_until_future_complete(
                self.node, future, timeout_sec=timeout_sec
            )

            result = future.result()
            if result is None:
                self.logger.error(f'{error_msg}: No response received')
                return None

            if self.was_successful(result):
                self.logger.info(success_msg)
            else:
                status_msg = getattr(result, 'status_message', 'Unknown error')
                self.logger.error(f'{error_msg}: {status_msg}')

            return result

        except Exception as e:
            self.logger.error(
                f'Exception calling "{client.srv_name}": {e}'
            )
            return None

    def was_successful(self, result: Any) -> bool:
        """
        Check if a service response indicates success.

        Supports different response formats:
        - Has 'success' field: return its value
        - No 'success' field: assume success if result exists

        Args:
            result: Service response

        Returns:
            True if call was successful
        """
        if result is None:
            return False
        if hasattr(result, 'success'):
            return result.success
        return True

    def wait_for_services(
        self,
        clients_with_names: list,
        timeout_per_service: float = 10.0
    ) -> bool:
        """
        Wait for multiple services to become available.

        Args:
            clients_with_names: List of (client, name) tuples
            timeout_per_service: Timeout per service

        Returns:
            True if all services are available, False otherwise

        Example:
            >>> success = helper.wait_for_services([
            ...     (self.move_client, "move"),
            ...     (self.home_client, "home"),
            ... ])
        """
        for client, name in clients_with_names:
            self.logger.info(f'⏳ Waiting for {name} service...')

            while not client.wait_for_service(timeout_sec=1.0):
                if not rclpy.ok():
                    return False
                self.logger.info(f'⏳ Service {name} not available, waiting...')

            self.logger.info(f'✅ Service {name} is ready!')

        return True
