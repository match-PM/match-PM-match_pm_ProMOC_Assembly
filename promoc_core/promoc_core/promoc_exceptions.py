"""Shared exception classes for ProMOC nodes."""

from typing import Optional, Dict, Any


class ProMocError(Exception):
    """Basis-Exception mit message, details (dict) und error_code.

    Ermoeglicht strukturierte Fehlerbehandlung: Jeder Fehler traegt einen
    numerischen Code aus error_codes und optionale Debug-Details.
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


# --- Exception-Hierarchie ---
# ProMocError
#   +-- ConnectionError (Verbindungsfehler)
#   |     +-- CommunicationError
#   |     +-- DeviceNotFoundError
#   |     +-- CommunicationTimeoutError
#   +-- MotionError (Bewegungsfehler)
#   |     +-- MovementTimeoutError
#   |     +-- HomingRequiredError
#   |     +-- HomingFailedError
#   +-- SafetyError (Sicherheitsverletzungen)
#   |     +-- PositionOutOfBoundsError
#   |     +-- CollisionDetectedError
#   |     +-- SoftLimitViolationError
#   +-- HardwareError (Hardware-Fehler)
#   |     +-- DriverNotAvailableError
#   +-- ConfigurationError (Konfiguration/Validierung)
#   +-- ServiceError (ROS2-Service-Fehler)
#   |     +-- ServiceCallFailedError
#   +-- ImageProcessingError (Bildverarbeitung)

class ConnectionError(ProMocError):
    """Verbindungs- und Kommunikationsfehler."""
    pass


class CommunicationError(ConnectionError):
    """Low-Level-Kommunikationsfehler."""
    pass


class DeviceNotFoundError(ConnectionError):
    """Geraet nicht gefunden."""
    pass


class CommunicationTimeoutError(ConnectionError):
    """Kommunikations-Timeout."""
    pass


class MotionError(ProMocError):
    """Fehler waehrend Bewegungsoperationen."""
    pass


class MovementTimeoutError(MotionError):
    """Bewegungs-Timeout."""
    pass


class HomingRequiredError(MotionError):
    """Homing erforderlich vor Bewegung."""
    pass


class HomingFailedError(MotionError):
    """Homing fehlgeschlagen."""
    pass


class SafetyError(ProMocError):
    """Sicherheitsverletzung."""
    pass


class PositionOutOfBoundsError(SafetyError):
    """Position ausserhalb erlaubter Grenzen."""
    pass


class CollisionDetectedError(SafetyError):
    """Kollisionsrisiko erkannt."""
    pass


class SoftLimitViolationError(SafetyError):
    """Soft-Limit erreicht."""
    pass


class HardwareError(ProMocError):
    """Hardware-bezogene Fehler."""
    pass


class DriverNotAvailableError(HardwareError):
    """Treiberbibliothek oder -schnittstelle nicht verfuegbar."""
    pass


class ConfigurationError(ProMocError):
    """Konfigurations- und Validierungsfehler."""
    pass


class ServiceError(ProMocError):
    """ROS2-Service-bezogene Fehler."""
    pass


class ServiceCallFailedError(ServiceError):
    """Service-Aufruf fehlgeschlagen."""
    pass


class ImageProcessingError(ProMocError):
    """Fehler bei der Bildverarbeitung."""
    pass
