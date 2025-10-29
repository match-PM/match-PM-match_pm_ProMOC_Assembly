"""
Error Handling Utilities for ProMOC Assembly System

This module provides utilities for consistent error handling across the
ProMOC Assembly system, including standardized service responses, retry
mechanisms, and error recovery strategies.

Author: ProMOC Assembly Team
Date: 29. Oktober 2025
"""

import time
import functools
from typing import Callable, Any, Optional, TypeVar, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from promoc_exceptions import (
        ProMocError, 
        CommunicationTimeoutError,
        DeviceDisconnectedError,
        ConnectionError as ProMocConnectionError
    )
except ImportError:
    # Fallback if module is in same directory
    from .promoc_exceptions import (
        ProMocError,
        CommunicationTimeoutError,
        DeviceDisconnectedError,
        ConnectionError as ProMocConnectionError
    )


# Type variable for generic functions
T = TypeVar('T')


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ServiceResponse:
    """
    Standardized service response structure.
    
    This class provides a consistent format for all service responses,
    including success status, error codes, messages, and additional metadata.
    
    Attributes:
        success: Whether the operation succeeded
        error_code: Numerical error code (0 = success)
        status_message: Human-readable status message
        warnings: List of warning messages
        execution_time: Time taken to execute the operation (seconds)
        details: Additional response-specific information
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
        **details
    ) -> 'ServiceResponse':
        """Create a successful response."""
        return cls(
            success=True,
            error_code=0,
            status_message=message,
            warnings=warnings or [],
            execution_time=execution_time,
            details=details
        )
    
    @classmethod
    def error_response(
        cls,
        error: Exception,
        execution_time: float = 0.0,
        **details
    ) -> 'ServiceResponse':
        """
        Create an error response from an exception.
        
        Args:
            error: The exception that occurred
            execution_time: Time taken before error occurred
            **details: Additional context information
            
        Returns:
            ServiceResponse with error information
        """
        if isinstance(error, ProMocError):
            return cls(
                success=False,
                error_code=error.error_code,
                status_message=str(error),
                execution_time=execution_time,
                details={**error.details, **details}
            )
        else:
            return cls(
                success=False,
                error_code=9999,  # Unknown error
                status_message=f"{type(error).__name__}: {str(error)}",
                execution_time=execution_time,
                details=details
            )
    
    def to_ros_response(self, response_obj: Any) -> Any:
        """
        Populate a ROS service response object.
        
        Args:
            response_obj: ROS service response object to populate
            
        Returns:
            The populated response object
        """
        response_obj.success = self.success
        if hasattr(response_obj, 'error_code'):
            response_obj.error_code = self.error_code
        if hasattr(response_obj, 'status_message'):
            response_obj.status_message = self.status_message
        if hasattr(response_obj, 'execution_time'):
            response_obj.execution_time = self.execution_time
        if hasattr(response_obj, 'warnings'):
            response_obj.warnings = self.warnings
        
        # Populate additional fields from details
        for key, value in self.details.items():
            if hasattr(response_obj, key):
                setattr(response_obj, key, value)
        
        return response_obj


@dataclass
class RetryConfig:
    """
    Configuration for retry mechanism.
    
    Attributes:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay after each attempt
        max_delay: Maximum delay between retries (seconds)
        retriable_exceptions: Tuple of exception types to retry on
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
    Decorator for automatic retry on specific exceptions.
    
    Usage:
        @retry_on_error(RetryConfig(max_attempts=5))
        def connect_to_device():
            # ... connection code
            pass
    
    Args:
        config: Retry configuration (uses defaults if None)
        
    Returns:
        Decorated function with retry capability
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = config.delay
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retriable_exceptions as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        # Log retry attempt if logger is available
                        if args and hasattr(args[0], 'logger'):
                            args[0].logger.warning(
                                f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                                f"Retrying in {delay:.1f}s..."
                            )
                        
                        time.sleep(delay)
                        delay = min(delay * config.backoff_factor, config.max_delay)
                    else:
                        # Last attempt failed
                        if args and hasattr(args[0], 'logger'):
                            args[0].logger.error(
                                f"All {config.max_attempts} attempts failed. "
                                f"Last error: {e}"
                            )
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


class ErrorRecoveryStrategy:
    """
    Base class for error recovery strategies.
    
    Subclass this to implement specific recovery behaviors for different
    types of errors.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def can_recover(self, error: Exception) -> bool:
        """
        Check if this strategy can recover from the given error.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if recovery is possible, False otherwise
        """
        return False
    
    def recover(self, error: Exception, context: dict) -> bool:
        """
        Attempt to recover from the error.
        
        Args:
            error: The exception that occurred
            context: Context information (device state, etc.)
            
        Returns:
            True if recovery succeeded, False otherwise
        """
        return False


class HomingRecoveryStrategy(ErrorRecoveryStrategy):
    """
    Recovery strategy that performs homing after certain errors.
    """
    
    def can_recover(self, error: Exception) -> bool:
        from promoc_exceptions import (
            PositionOutOfBoundsError,
            HomingRequiredError,
            SoftLimitViolationError
        )
        return isinstance(error, (
            PositionOutOfBoundsError,
            HomingRequiredError,
            SoftLimitViolationError
        ))
    
    def recover(self, error: Exception, context: dict) -> bool:
        """
        Recover by performing homing operation.
        
        Args:
            error: The exception that occurred
            context: Must contain 'driver' with home() method
            
        Returns:
            True if homing succeeded
        """
        try:
            driver = context.get('driver')
            if driver and hasattr(driver, 'home'):
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
    Recovery strategy that attempts to reconnect after connection errors.
    """
    
    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, (
            DeviceDisconnectedError,
            ProMocConnectionError,
        ))
    
    def recover(self, error: Exception, context: dict) -> bool:
        """
        Recover by attempting to reconnect.
        
        Args:
            error: The exception that occurred
            context: Must contain 'driver' with connect() method and connection parameters
            
        Returns:
            True if reconnection succeeded
        """
        try:
            driver = context.get('driver')
            if driver and hasattr(driver, 'connect'):
                if self.logger:
                    self.logger.info(f"Attempting reconnection after: {error}")
                
                # Get connection parameters from context
                port = context.get('port')
                
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
    Manages multiple error recovery strategies.
    
    This class coordinates different recovery strategies and attempts them
    in order until one succeeds or all fail.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        self.strategies: List[ErrorRecoveryStrategy] = []
    
    def add_strategy(self, strategy: ErrorRecoveryStrategy):
        """Add a recovery strategy to the manager."""
        self.strategies.append(strategy)
    
    def attempt_recovery(self, error: Exception, context: dict) -> bool:
        """
        Attempt recovery using available strategies.
        
        Args:
            error: The exception that occurred
            context: Context information for recovery
            
        Returns:
            True if any strategy succeeded, False otherwise
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
            self.logger.warning(
                f"No recovery strategy succeeded for error: {error}"
            )
        
        return False


def handle_service_errors(logger=None, recovery_manager: Optional[ErrorRecoveryManager] = None):
    """
    Decorator for service callbacks with automatic error handling.
    
    Usage:
        @handle_service_errors(logger=self.get_logger())
        def move_absolute_callback(self, request, response):
            # ... service implementation
            return response
    
    Args:
        logger: Logger instance for error logging
        recovery_manager: Optional recovery manager for error recovery
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Add execution time if response has the field
                if hasattr(result, 'execution_time'):
                    result.execution_time = execution_time
                
                return result
                
            except ProMocError as e:
                execution_time = time.time() - start_time
                
                if logger:
                    logger.error(f"Service error: {e}", exc_info=True)
                
                # Attempt recovery if manager is available
                if recovery_manager:
                    context = {'args': args, 'kwargs': kwargs}
                    if recovery_manager.attempt_recovery(e, context):
                        if logger:
                            logger.info("Recovery succeeded, retrying operation")
                        # Retry the operation after successful recovery
                        try:
                            return func(*args, **kwargs)
                        except Exception as retry_error:
                            if logger:
                                logger.error(f"Retry after recovery failed: {retry_error}")
                
                # Create error response
                response = ServiceResponse.error_response(e, execution_time)
                
                # If we have a ROS response object in args, populate it
                for arg in args:
                    if hasattr(arg, 'success'):
                        return response.to_ros_response(arg)
                
                # Otherwise return the ServiceResponse
                return response
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                if logger:
                    logger.error(
                        f"Unexpected error in service: {type(e).__name__}: {e}",
                        exc_info=True
                    )
                
                response = ServiceResponse.error_response(e, execution_time)
                
                for arg in args:
                    if hasattr(arg, 'success'):
                        return response.to_ros_response(arg)
                
                return response
        
        return wrapper
    return decorator
