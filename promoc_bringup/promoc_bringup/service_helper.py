#!/usr/bin/env python3
"""
Service Helper for ProMOC Bringup
=================================

This module provides reusable helper functions for calling ROS2 services.
Used by demo controllers and other automation scripts.

The main benefit is consolidating service-call boilerplate code in one place,
making demo controllers cleaner and more readable.

Usage:
    from promoc_bringup.service_helper import ServiceHelper
    
    helper = ServiceHelper(node)
    helper.call_service(client, request, "Motion started", "Motion failed")
"""

import rclpy
from rclpy.node import Node
from typing import Optional, Any, Callable


class ServiceHelper:
    """
    Helper class for calling ROS2 services with consistent error handling.

    This class wraps common patterns like:
    - Waiting for service availability
    - Calling service with timeout
    - Logging success/failure
    - Handling exceptions

    Example:
        >>> helper = ServiceHelper(self)  # 'self' is a ROS2 Node
        >>> 
        >>> # Simple call
        >>> result = helper.call_service(
        ...     client=self.move_client,
        ...     request=MoveRequest(position=10.0),
        ...     success_msg="Move completed",
        ...     error_msg="Move failed"
        ... )
        >>> 
        >>> # Check result
        >>> if helper.was_successful(result):
        ...     print("Motion done!")
    """

    def __init__(self, node: Node):
        """
        Initialize the helper with a ROS2 node.

        Args:
            node: The ROS2 node that owns the service clients.
                  Used for logging and spinning.
        """
        self.node = node
        self.logger = node.get_logger()

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
        Call a ROS2 service with proper error handling.

        How it works:
            1. Wait for service to be available
            2. Call service asynchronously
            3. Spin until response or timeout
            4. Log result and return

        Args:
            client: The ROS2 service client
            request: The service request message
            success_msg: Message to log on success
            error_msg: Message to log on failure
            timeout_sec: Timeout for the service call (default: 10s)
            wait_for_service_sec: Timeout waiting for service (default: 2s)

        Returns:
            The service response, or None if failed

        Example:
            >>> request = MoveAbsolute.Request()
            >>> request.position = 50.0
            >>> result = helper.call_service(
            ...     self.move_client, request,
            ...     "Moved to 50mm", "Move failed",
            ...     timeout_sec=15.0
            ... )
        """
        # Step 1: Wait for service
        if not client.wait_for_service(timeout_sec=wait_for_service_sec):
            self.logger.error(
                f'Service "{client.srv_name}" not available. Skipping call.'
            )
            return None

        # Step 2: Call service
        try:
            future = client.call_async(request)
            rclpy.spin_until_future_complete(
                self.node, future, timeout_sec=timeout_sec
            )

            # Step 3: Check result
            result = future.result()
            if result is None:
                self.logger.error(f'{error_msg}: No response received')
                return None

            # Step 4: Check for success field (if exists)
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
        Check if a service result indicates success.

        Handles different service response formats:
        - Has 'success' field → check its value
        - No 'success' field → assume success if result exists

        Args:
            result: The service response

        Returns:
            True if the call was successful
        """
        if result is None:
            return False
        if hasattr(result, 'success'):
            return result.success
        return True  # No success field, assume success

    def wait_for_services(
        self,
        clients_with_names: list,
        timeout_per_service: float = 10.0
    ) -> bool:
        """
        Wait for multiple services to become available.

        Args:
            clients_with_names: List of (client, name) tuples
            timeout_per_service: Timeout for each service

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
