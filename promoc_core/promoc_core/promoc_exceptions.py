"""Shared exception classes for ProMOC nodes."""

from typing import Optional, Dict, Any


class ProMocError(Exception):
    """Base exception carrying a message, details, and error code."""

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


class ConnectionError(ProMocError):
    """Connection and communication errors."""

    pass


class CommunicationError(ConnectionError):
    """Low-level communication errors."""

    pass


class DeviceNotFoundError(ConnectionError):
    """Device discovery errors."""

    pass


class CommunicationTimeoutError(ConnectionError):
    """Communication timeout errors."""

    pass


class MotionError(ProMocError):
    """Errors during motion operations."""

    pass


class MovementTimeoutError(MotionError):
    """Movement timeout errors."""

    pass


class HomingRequiredError(MotionError):
    """Raised when homing is required before a motion."""

    pass


class HomingFailedError(MotionError):
    """Homing failed."""

    pass


class SafetyError(ProMocError):
    """Safety violations."""

    pass


class PositionOutOfBoundsError(SafetyError):
    """Position is outside allowed bounds."""

    pass


class CollisionDetectedError(SafetyError):
    """Collision risk detected."""

    pass


class SoftLimitViolationError(SafetyError):
    """Soft limit was reached."""

    pass


class HardwareError(ProMocError):
    """Hardware-related errors."""

    pass


class DriverNotAvailableError(HardwareError):
    """Required driver library or interface not available."""

    pass


class ConfigurationError(ProMocError):
    """Configuration and validation errors."""

    pass


class ServiceError(ProMocError):
    """ROS2 service-related errors."""

    pass


class ServiceCallFailedError(ServiceError):
    """Service call failed or returned an error."""

    pass


class ImageProcessingError(ProMocError):
    """Errors during image processing."""

    pass
