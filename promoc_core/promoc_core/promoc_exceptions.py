"""
ProMOC Exception Hierarchy
==========================

Exception Hierarchy:
    ProMocError (Base)
    ├── ConnectionError     # Connection, Timeout, Device not found
    ├── MotionError         # Movement, Position, Collision, Homing
    ├── SafetyError         # Soft/Hard Limits, Emergency Stop
    ├── HardwareError       # Driver, Sensor, Initialization
    ├── ConfigurationError  # Parameters, Validation
    └── ServiceError        # ROS2 Service errors

"""

from typing import Optional, Dict, Any


class ProMocError(Exception):
    """Base exception for all ProMOC errors.
    
    Attributes:
        message: Description of the error
        details: Optional additional information (dict)
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"[{self.__class__.__name__}] {self.message} | {details_str}"
        return f"[{self.__class__.__name__}] {self.message}"


# =============================================================================
# Connection Errors
# =============================================================================

class ConnectionError(ProMocError):
    """Connection and communication errors.
    
    Use for: device not found, disconnection, communication timeout.
    """
    pass


# =============================================================================
# Motion Errors
# =============================================================================

class MotionError(ProMocError):
    """Errors during motion operations.
    
    Use for: movement timeout, position out of bounds, collision, homing failure.
    """
    pass


# =============================================================================
# Safety Errors
# =============================================================================

class SafetyError(ProMocError):
    """Safety violations.
    
    Use for: soft/hard limit violations, emergency stop, safety zone violations.
    """
    pass


# =============================================================================
# Hardware Errors
# =============================================================================

class HardwareError(ProMocError):
    """Hardware-related errors.
    
    Use for: driver unavailable, initialization failure, sensor read error.
    """
    pass


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(ProMocError):
    """Configuration and validation errors.
    
    Use for: invalid parameters, missing configuration, validation failure.
    """
    pass


# =============================================================================
# Service Errors
# =============================================================================

class ServiceError(ProMocError):
    """ROS2 service-related errors.
    
    Use for: service call failure, invalid request, service timeout.
    """
    pass


# =============================================================================
# Image Processing Errors (Camera-specific)
# =============================================================================

class ImageProcessingError(ProMocError):
    """Errors during image processing."""
    pass


# Convenience aliases for common specific errors
HomingFailedError = MotionError
SoftLimitViolationError = SafetyError