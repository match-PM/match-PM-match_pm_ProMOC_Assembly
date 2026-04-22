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
        details: Optional[Dict[str, Any]] = None,
        error_code: int = 1,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code

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


class CommunicationError(ConnectionError):
    """Low-level communication errors.

    Use for: device not connected, transport failure, protocol errors.
    """

    pass


class DeviceNotFoundError(ConnectionError):
    """Device discovery errors.

    Use for: missing device, invalid port, device not enumerated.
    """

    pass


class CommunicationTimeoutError(ConnectionError):
    """Communication timeout errors."""

    pass


# =============================================================================
# Motion Errors
# =============================================================================


class MotionError(ProMocError):
    """Errors during motion operations.

    Use for: movement timeout, position out of bounds, collision, homing failure.
    """

    pass


class MovementTimeoutError(MotionError):
    """Movement timeout errors."""

    pass


class HomingRequiredError(MotionError):
    """Raised when homing is required before a motion."""

    pass


# =============================================================================
# Safety Errors
# =============================================================================


class SafetyError(ProMocError):
    """Safety violations.

    Use for: soft/hard limit violations, emergency stop, safety zone violations.
    """

    pass


class PositionOutOfBoundsError(SafetyError):
    """Position is outside allowed bounds."""

    pass


class CollisionDetectedError(SafetyError):
    """Collision risk detected."""

    pass


# =============================================================================
# Hardware Errors
# =============================================================================


class HardwareError(ProMocError):
    """Hardware-related errors.

    Use for: driver unavailable, initialization failure, sensor read error.
    """

    pass


class DriverNotAvailableError(HardwareError):
    """Required driver library or interface not available."""

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


class ServiceCallFailedError(ServiceError):
    """Service call failed or returned an error."""

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
PositionError = MotionError
