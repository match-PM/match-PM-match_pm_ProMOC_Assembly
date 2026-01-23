"""

Exception-Hierarchie:
    ProMocError (Basis)
    ├── ConnectionError     # Verbindung, Timeout, Device not found
    ├── MotionError         # Bewegung, Position, Kollision, Homing
    ├── SafetyError         # Soft/Hard Limits, Emergency Stop
    ├── HardwareError       # Driver, Sensor, Initialisierung
    ├── ConfigurationError  # Parameter, Validierung
    └── ServiceError        # ROS2 Service-Fehler

"""


from typing import Optional, Dict, Any


class ProMocError(Exception):
    """Basis-Exception für alle ProMOC-Fehler.
    
    Attributes:
        message: Beschreibung des Fehlers
        details: Optionale zusätzliche Informationen (dict)
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
# Verbindungsfehler
# =============================================================================

class ConnectionError(ProMocError):
    """Verbindungs- und Kommunikationsfehler.
    
    Ersetzt: DeviceNotFoundError, DeviceDisconnectedError, 
             CommunicationTimeoutError, CommunicationError
    """
    pass


# =============================================================================
# Bewegungsfehler
# =============================================================================

class MotionError(ProMocError):
    """Fehler bei Bewegungsoperationen.
    
    Ersetzt: MovementTimeoutError, PositionOutOfBoundsError,
             CollisionDetectedError, HomingFailedError
    """
    pass


# =============================================================================
# Sicherheitsfehler
# =============================================================================

class SafetyError(ProMocError):
    """Sicherheitsverletzungen.
    
    Ersetzt: SoftLimitViolationError, HardLimitViolationError,
             EmergencyStopError, SafetyZoneViolationError
    """
    pass


# =============================================================================
# Hardware-Fehler
# =============================================================================

class HardwareError(ProMocError):
    """Hardware-bezogene Fehler.
    
    Ersetzt: DriverNotAvailableError, HardwareInitializationError,
             SensorReadError, CalibrationError
    """
    pass


# =============================================================================
# Konfigurationsfehler
# =============================================================================

class ConfigurationError(ProMocError):
    """Konfigurations- und Validierungsfehler.
    
    Ersetzt: InvalidParameterError, MissingConfigurationError,
             ValidationError, ParameterValidationError
    """
    pass


# =============================================================================
# Service-Fehler
# =============================================================================

class ServiceError(ProMocError):
    """ROS2 Service-bezogene Fehler.
    
    Ersetzt: ServiceCallFailedError, InvalidServiceRequestError,
             ServiceTimeoutError
    """
    pass


# =============================================================================
# Bildverarbeitungsfehler (Kamera-spezifisch)
# =============================================================================

class ImageProcessingError(ProMocError):
    """Fehler bei der Bildverarbeitung."""
    pass

"""
# =============================================================================
# Abwärtskompatibilität - Aliase für häufig genutzte alte Namen
# =============================================================================

# Connection
DeviceNotFoundError = ConnectionError
DeviceDisconnectedError = ConnectionError
CommunicationTimeoutError = ConnectionError
CommunicationError = ConnectionError

# Motion
MovementTimeoutError = MotionError
PositionOutOfBoundsError = MotionError
CollisionDetectedError = MotionError
HomingFailedError = MotionError

# Safety
SoftLimitViolationError = SafetyError
HardLimitViolationError = SafetyError
EmergencyStopError = SafetyError
SafetyZoneViolationError = SafetyError
SafetyViolation = SafetyError  # Alter Name

# Hardware
DriverNotAvailableError = HardwareError
HardwareInitializationError = HardwareError
SensorReadError = HardwareError
CalibrationError = HardwareError
CalibrationFailedError = HardwareError
CalibrationDataInvalidError = HardwareError
HomingRequiredError = HardwareError

# Configuration
InvalidParameterError = ConfigurationError
MissingConfigurationError = ConfigurationError
ValidationError = ConfigurationError
ParameterValidationError = ConfigurationError

# Service
ServiceCallFailedError = ServiceError
InvalidServiceRequestError = ServiceError
ServiceTimeoutError = ServiceError
"""