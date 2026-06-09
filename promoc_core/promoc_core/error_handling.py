"""Utilities for error handling in the ProMOC assembly system.

This module bundles helper functions and classes for consistent error handling
throughout the ProMOC assembly system, including:

- Standardized service responses (success/error_code/status_message/etc.).
- Retry mechanisms for transient connection drops or timeouts.
- Recovery strategies (e.g., homing, reconnect) that can be optionally
  applied automatically.

Note:
    This module does not modify ROS2 interfaces directly but helps to
    implement service callbacks *uniformly* and to communicate error cases
    cleanly to the outside world.

Author: ProMOC Assembly Team
Date: October 29, 2025
"""

import time
import functools
from typing import Callable, Any, Optional, TypeVar, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from . import error_codes
    from .promoc_exceptions import (
        ProMocError,
        ConnectionError as ProMocConnectionError,
        MotionError,
        SafetyError,
    )
except ImportError:
    # Fallback if module is in the same directory
    import error_codes
    from promoc_exceptions import (
        ProMocError,
        ConnectionError as ProMocConnectionError,
        MotionError,
        SafetyError,
    )

# Aliases for backward compatibility with retry config
CommunicationTimeoutError = ProMocConnectionError
DeviceDisconnectedError = ProMocConnectionError


# Type variable for generic functions
T = TypeVar("T")


class ErrorSeverity(Enum):
    """Severity levels for errors/warnings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ServiceResponse:
    """
    Standardized response structure for services.

    This class provides a uniform format for service responses, including
    a success flag, error code, status message, warnings, and optional metadata.

    Attributes:
        success: Whether the operation was successful.
        error_code: A numerical error code (0 = success).
        status_message: A human-readable status or error message.
        warnings: A list of warning messages.
        execution_time: The duration of the operation in seconds.
        details: Additional, response-specific information.
    """

    success: bool
    error_code: int = 0
    status_message: str = ""
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    details: dict = field(default_factory=dict)

    @classmethod
    def success_response(
        cls,
        message: str = "Operation completed successfully",
        execution_time: float = 0.0,
        warnings: Optional[List[str]] = None,
        **details,
    ) -> "ServiceResponse":
        """Creates a successful response."""
        return cls(
            success=True,
            error_code=0,
            status_message=message,
            warnings=warnings or [],
            execution_time=execution_time,
            details=details,
        )

    @classmethod
    def error_response(
        cls, error: Exception, execution_time: float = 0.0, **details
    ) -> "ServiceResponse":
        """Creates an error response from an exception.

        Args:
            error: The exception that occurred.
            execution_time: The runtime until the error occurred (in seconds).
            **details: Additional context.

        Returns:
            A ServiceResponse containing error information.
        """
        if isinstance(error, ProMocError):
            return cls(
                success=False,
                error_code=error.error_code,
                status_message=str(error),
                execution_time=execution_time,
                details={**error.details, **details},
            )
        else:
            return cls(
                success=False,
                error_code=error_codes.UNKNOWN_ERROR,
                status_message=f"{type(error).__name__}: {str(error)}",
                execution_time=execution_time,
                details=details,
            )

    def to_ros_response(self, response_obj: Any) -> Any:
        """
        Populates a ROS service response object.

        Args:
            response_obj: The ROS response object to be populated.

        Returns:
            The populated response object.
        """
        response_obj.success = self.success
        if hasattr(response_obj, "error_code"):
            response_obj.error_code = self.error_code
        if hasattr(response_obj, "message"):
            response_obj.message = self.status_message
        if hasattr(response_obj, "status_message"):
            response_obj.status_message = self.status_message
        if hasattr(response_obj, "execution_time"):
            response_obj.execution_time = self.execution_time
        if hasattr(response_obj, "warnings"):
            response_obj.warnings = self.warnings

        # Populate additional fields from details
        for key, value in self.details.items():
            if hasattr(response_obj, key):
                setattr(response_obj, key, value)

        return response_obj


@dataclass
class RetryConfig:
    """
    Configuration for the retry mechanism.

    Attributes:
        max_attempts: The maximum number of attempts.
        delay: The initial wait time between attempts (in seconds).
        backoff_factor: The multiplier for the wait time after each attempt.
        max_delay: The maximum wait time (in seconds).
        retriable_exceptions: A tuple of exception types for which a retry
            is sensible.
    """

    max_attempts: int = 3
    delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 30.0
    retriable_exceptions: Tuple[type, ...] = (
        CommunicationTimeoutError,
        DeviceDisconnectedError,
    )


def retry_on_error(config: Optional[RetryConfig] = None):
    """
    A decorator for automatic retries on specific exceptions.

    Example:
        @retry_on_error(RetryConfig(max_attempts=5))
        def connect_to_device():
            # ... connection code
            pass

    Args:
        config: Retry configuration (uses default if None).

    Returns:
        A decorated function with retry capabilities.
    """
    if config is None:
        config = RetryConfig()
    if config.max_attempts < 1:
        raise ValueError("RetryConfig.max_attempts must be >= 1")
    if config.delay < 0:
        raise ValueError("RetryConfig.delay must be >= 0")
    if config.backoff_factor <= 0:
        raise ValueError("RetryConfig.backoff_factor must be > 0")
    if config.max_delay < 0:
        raise ValueError("RetryConfig.max_delay must be >= 0")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            delay = config.delay

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retriable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_attempts - 1:
                        # Log retry attempt if a logger is available
                        if args and hasattr(args[0], "logger"):
                            args[0].logger.warning(
                                f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                                f"Retrying in {delay:.1f}s..."
                            )

                        time.sleep(delay)
                        delay = min(delay * config.backoff_factor, config.max_delay)
                    else:
                        # Last attempt failed
                        if args and hasattr(args[0], "logger"):
                            args[0].logger.error(
                                f"All {config.max_attempts} attempts failed. "
                                f"Last error: {e}"
                            )

            # All retries exhausted
            if last_exception is None:
                raise RuntimeError(
                    "retry_on_error exhausted without captured exception"
                )
            raise last_exception

        return wrapper

    return decorator


class ErrorRecoveryStrategy:
    """
    Base class for recovery strategies.

    Inherit from this to implement specific recovery mechanisms (e.g., homing,
    reconnect). The manager can then select appropriate strategies based on the
    exception type.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def can_recover(self, error: Exception) -> bool:
        """
        Checks if this strategy can handle the given error.

        Args:
            error: The exception that occurred.

        Returns:
            True if recovery is possible, otherwise False.
        """
        return False

    def recover(self, error: Exception, context: dict) -> bool:
        """
        Attempts to resolve the error.

        Args:
            error: The exception that occurred.
            context: Contextual information (device state, handles, parameters, etc.).

        Returns:
            True if recovery was successful, otherwise False.
        """
        return False


class HomingRecoveryStrategy(ErrorRecoveryStrategy):
    """
    A recovery strategy that performs homing after specific errors.
    """

    def can_recover(self, error: Exception) -> bool:
        # Recoverable for motion errors related to position/homing
        # and safety errors related to soft limits
        return isinstance(error, (MotionError, SafetyError))

    def recover(self, error: Exception, context: dict) -> bool:
        """
        Recovers by executing a homing operation.

        Args:
            error: The exception that occurred.
            context: Must contain at least a 'driver' with a home() method.

        Returns:
            True if homing was successful.
        """
        try:
            driver = context.get("driver")
            if driver and hasattr(driver, "home"):
                if self.logger:
                    self.logger.info(f"Attempting recovery via homing after: {error}")

                success = driver.home()

                if self.logger:
                    if success:
                        self.logger.info("Homing recovery successful")
                    else:
                        self.logger.error("Homing recovery failed")

                return success
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during homing recovery: {e}")

        return False


class ReconnectionRecoveryStrategy(ErrorRecoveryStrategy):
    """
    A recovery strategy that attempts to reconnect after connection errors.
    """

    def can_recover(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                DeviceDisconnectedError,
                ProMocConnectionError,
            ),
        )

    def recover(self, error: Exception, context: dict) -> bool:
        """
        Recovers by reconnecting.

        Args:
            error: The exception that occurred.
            context: Must contain at least a 'driver' with a connect() method,
                     and optionally connection parameters (e.g., port).

        Returns:
            True if reconnection was successful.
        """
        try:
            driver = context.get("driver")
            if driver and hasattr(driver, "connect"):
                if self.logger:
                    self.logger.info(f"Attempting reconnection after: {error}")

                # Get connection parameters from context
                port = context.get("port")

                success = driver.connect(port=port)

                if self.logger:
                    if success:
                        self.logger.info("Reconnection successful")
                    else:
                        self.logger.error("Reconnection failed")

                return success
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during reconnection recovery: {e}")

        return False


class ErrorRecoveryManager:
    """
    A manager for multiple recovery strategies.

    This manager coordinates different strategies and tries them in order
    until one succeeds or all fail.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.strategies: List[ErrorRecoveryStrategy] = []

    def add_strategy(self, strategy: ErrorRecoveryStrategy):
        """Adds a recovery strategy to the manager."""
        self.strategies.append(strategy)

    def attempt_recovery(self, error: Exception, context: dict) -> bool:
        """
        Attempts recovery using the available strategies.

        Args:
            error: The exception that occurred.
            context: Context for the recovery.

        Returns:
            True if any strategy was successful, otherwise False.
        """
        for strategy in self.strategies:
            if strategy.can_recover(error):
                if self.logger:
                    self.logger.info(
                        f"Attempting recovery with {strategy.__class__.__name__}"
                    )

                if strategy.recover(error, context):
                    return True

        if self.logger:
            self.logger.warning(f"No recovery strategy succeeded for error: {error}")

        return False


def handle_service_errors(
    logger=None, recovery_manager: Optional[ErrorRecoveryManager] = None
):
    """
    A decorator for service callbacks with automatic error handling.

    Example:
        @handle_service_errors(logger=self.get_logger())
        def move_absolute_callback(self, request, response):
            # ... service implementation
            return response

    Args:
        logger: A logger instance for logging.
        recovery_manager: An optional ErrorRecoveryManager for automatic recovery.

    Returns:
        A decorated function with error handling.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Auto-detect logger from self (args[0]) if not provided
            nonlocal logger
            current_logger = logger
            if current_logger is None and args and hasattr(args[0], "logger"):
                current_logger = args[0].logger

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Add execution time if the response has the field
                if hasattr(result, "execution_time"):
                    result.execution_time = execution_time

                return result

            except ProMocError as e:
                execution_time = time.time() - start_time

                if current_logger:
                    current_logger.error(f"Service error: {e}")

                # Attempt recovery if a manager is available
                if recovery_manager:
                    context = {"args": args, "kwargs": kwargs}
                    if recovery_manager.attempt_recovery(e, context):
                        if current_logger:
                            current_logger.info(
                                "Recovery succeeded, retrying operation"
                            )
                        # Retry the operation after successful recovery
                        try:
                            return func(*args, **kwargs)
                        except Exception as retry_error:
                            if current_logger:
                                current_logger.error(
                                    f"Retry after recovery failed: {retry_error}"
                                )

                # Create an error response
                response = ServiceResponse.error_response(e, execution_time)

                # If we have a ROS response object in args, populate it
                for arg in args:
                    if hasattr(arg, "success"):
                        return response.to_ros_response(arg)

                # Otherwise, return the ServiceResponse
                return response

            except Exception as e:
                execution_time = time.time() - start_time

                if current_logger:
                    current_logger.error(
                        f"Unexpected error in service: {type(e).__name__}: {e}"
                    )

                response = ServiceResponse.error_response(e, execution_time)

                for arg in args:
                    if hasattr(arg, "success"):
                        return response.to_ros_response(arg)

                return response

        return wrapper

    return decorator
