"""
Custom Exception Hierarchy for ProMOC Assembly System

This module defines a comprehensive exception hierarchy for the ProMOC Assembly
system, enabling more precise error handling and better debugging capabilities.

Exception Hierarchy:
--------------------
ProMocError (base)
├── ConnectionError
│   ├── DeviceNotFoundError
│   ├── DeviceDisconnectedError
│   └── CommunicationTimeoutError
├── MotionError
│   ├── MovementTimeoutError
│   ├── PositionOutOfBoundsError
│   ├── CollisionDetectedError
│   └── HomingFailedError
├── SafetyViolation
│   ├── SoftLimitViolationError
│   ├── HardLimitViolationError
│   ├── EmergencyStopError
│   └── SafetyZoneViolationError
├── CalibrationError
│   ├── HomingRequiredError
│   ├── CalibrationFailedError
│   └── CalibrationDataInvalidError
├── HardwareError
│   ├── DriverNotAvailableError
│   ├── HardwareInitializationError
│   └── SensorReadError
├── ConfigurationError
│   ├── InvalidParameterError
│   ├── MissingConfigurationError
│   └── ValidationError
└── ServiceError
    ├── ServiceCallFailedError
    ├── InvalidServiceRequestError
    ├── ServiceTimeoutError

Usage Example:
--------------
    from promoc_core.promoc_exceptions import PositionOutOfBoundsError, HomingRequiredError
    
    def move_to_position(position):
        if not self.is_homed:
            raise HomingRequiredError("Device must be homed before movement")
        if position > self.max_position:
            raise PositionOutOfBoundsError(
                f"Position {position} exceeds maximum {self.max_position}"
            )
        # ... perform movement

"""

from typing import Optional, Dict, Any


class ProMocError(Exception):
    """
    Base exception class for all ProMOC Assembly errors.

    All custom exceptions in the ProMOC system inherit from this class,
    allowing for easy catch-all error handling when needed.

    Attributes:
        message: Human-readable error description
        error_code: Numerical error code for programmatic handling
        details: Additional context information (dict)
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._default_error_code()
        self.details = details or {}

    def _default_error_code(self) -> int:
        """Return default error code for this exception type."""
        return 1000  # Generic error

    def __str__(self) -> str:
        base = f"[{self.__class__.__name__}:{self.error_code}] {self.message}"
        if self.details:
            details_str = ", ".join(
                f"{k}={v}" for k, v in self.details.items())
            return f"{base} | Details: {details_str}"
        return base


# ============================================================================
# Connection Errors (1100-1199)
# ============================================================================

class ConnectionError(ProMocError):
    """Base class for all connection-related errors."""

    def _default_error_code(self) -> int:
        return 1100


class DeviceNotFoundError(ConnectionError):
    """Raised when a device cannot be found or discovered."""

    def _default_error_code(self) -> int:
        return 1101


class DeviceDisconnectedError(ConnectionError):
    """Raised when a device unexpectedly disconnects."""

    def _default_error_code(self) -> int:
        return 1102


class CommunicationTimeoutError(ConnectionError):
    """Raised when communication with a device times out."""

    def _default_error_code(self) -> int:
        return 1103


class CommunicationError(ConnectionError):
    """Raised when communication with a device fails (e.g., device not connected)."""

    def _default_error_code(self) -> int:
        return 1104


# ============================================================================
# Motion Errors (1200-1299)
# ============================================================================

class MotionError(ProMocError):
    """Base class for all motion-related errors."""

    def _default_error_code(self) -> int:
        return 1200


class MovementTimeoutError(MotionError):
    """Raised when a movement operation times out."""

    def _default_error_code(self) -> int:
        return 1201


class PositionOutOfBoundsError(MotionError):
    """Raised when a requested position is outside valid range."""

    def _default_error_code(self) -> int:
        return 1202


class CollisionDetectedError(MotionError):
    """Raised when a collision is detected or predicted."""

    def _default_error_code(self) -> int:
        return 1203


class HomingFailedError(MotionError):
    """Raised when homing operation fails."""

    def _default_error_code(self) -> int:
        return 1204


# ============================================================================
# Safety Errors (1300-1399)
# ============================================================================

class SafetyViolation(ProMocError):
    """Base class for all safety-related errors."""

    def _default_error_code(self) -> int:
        return 1300


class SoftLimitViolationError(SafetyViolation):
    """Raised when a software limit is violated."""

    def _default_error_code(self) -> int:
        return 1301


class HardLimitViolationError(SafetyViolation):
    """Raised when a hardware limit is violated."""

    def _default_error_code(self) -> int:
        return 1302


class EmergencyStopError(SafetyViolation):
    """Raised when emergency stop is triggered."""

    def _default_error_code(self) -> int:
        return 1303


class SafetyZoneViolationError(SafetyViolation):
    """Raised when a safety zone is violated."""

    def _default_error_code(self) -> int:
        return 1304


# ============================================================================
# Calibration Errors (1400-1499)
# ============================================================================

class CalibrationError(ProMocError):
    """Base class for all calibration-related errors."""

    def _default_error_code(self) -> int:
        return 1400


class HomingRequiredError(CalibrationError):
    """Raised when an operation requires homing first."""

    def _default_error_code(self) -> int:
        return 1401


class CalibrationFailedError(CalibrationError):
    """Raised when calibration process fails."""

    def _default_error_code(self) -> int:
        return 1402


class CalibrationDataInvalidError(CalibrationError):
    """Raised when calibration data is invalid or corrupted."""

    def _default_error_code(self) -> int:
        return 1403


# ============================================================================
# Hardware Errors (1500-1599)
# ============================================================================

class HardwareError(ProMocError):
    """Base class for all hardware-related errors."""

    def _default_error_code(self) -> int:
        return 1500


class DriverNotAvailableError(HardwareError):
    """Raised when required hardware driver is not available."""

    def _default_error_code(self) -> int:
        return 1501


class HardwareInitializationError(HardwareError):
    """Raised when hardware initialization fails."""

    def _default_error_code(self) -> int:
        return 1502


class SensorReadError(HardwareError):
    """Raised when reading sensor data fails."""

    def _default_error_code(self) -> int:
        return 1503


# ============================================================================
# Configuration Errors (1600-1699)
# ============================================================================

class ConfigurationError(ProMocError):
    """Base class for all configuration-related errors."""

    def _default_error_code(self) -> int:
        return 1600


class InvalidParameterError(ConfigurationError):
    """Raised when a parameter has an invalid value."""

    def _default_error_code(self) -> int:
        return 1601


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    def _default_error_code(self) -> int:
        return 1602


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def _default_error_code(self) -> int:
        return 1603


# Alias for backwards compatibility - ParameterValidationError is used in some modules
ParameterValidationError = InvalidParameterError


# ============================================================================
# Service Errors (1700-1799)
# ============================================================================

class ServiceError(ProMocError):
    """Base class for all service-related errors."""

    def _default_error_code(self) -> int:
        return 1700


class ServiceCallFailedError(ServiceError):
    """Raised when a service call fails."""

    def _default_error_code(self) -> int:
        return 1701


class InvalidServiceRequestError(ServiceError):
    """Raised when a service request contains invalid data."""

    def _default_error_code(self) -> int:
        return 1702


class ServiceTimeoutError(ServiceError):
    """Raised when a service call times out."""

    def _default_error_code(self) -> int:
        return 1703


# ============================================================================
# Error Code Registry
# ============================================================================

ERROR_CODE_REGISTRY = {
    1000: "Generic ProMOC Error",
    # Connection Errors
    1100: "Connection Error",
    1101: "Device Not Found",
    1102: "Device Disconnected",
    1103: "Communication Timeout",
    1104: "Communication Error",
    # Motion Errors
    1200: "Motion Error",
    1201: "Movement Timeout",
    1202: "Position Out Of Bounds",
    1203: "Collision Detected",
    1204: "Homing Failed",
    # Safety Errors
    1300: "Safety Violation",
    1301: "Soft Limit Violation",
    1302: "Hard Limit Violation",
    1303: "Emergency Stop",
    1304: "Safety Zone Violation",
    # Calibration Errors
    1400: "Calibration Error",
    1401: "Homing Required",
    1402: "Calibration Failed",
    1403: "Calibration Data Invalid",
    # Hardware Errors
    1500: "Hardware Error",
    1501: "Driver Not Available",
    1502: "Hardware Initialization Error",
    1503: "Sensor Read Error",
    # Configuration Errors
    1600: "Configuration Error",
    1601: "Invalid Parameter",
    1602: "Missing Configuration",
    1603: "Validation Error",
    # Service Errors
    1700: "Service Error",
    1701: "Service Call Failed",
    1702: "Invalid Service Request",
    1703: "Service Timeout",
    # Vision Errors
    1800: "Image Processing Error",
}


class ImageProcessingError(ProMocError):
    """Raised when image processing fails."""

    def _default_error_code(self) -> int:
        return 1800


def get_error_description(error_code: int) -> str:
    """
    Get human-readable description for an error code.

    Args:
        error_code: The numerical error code

    Returns:
        Error description string, or "Unknown Error" if code not found
    """
    return ERROR_CODE_REGISTRY.get(error_code, "Unknown Error")
