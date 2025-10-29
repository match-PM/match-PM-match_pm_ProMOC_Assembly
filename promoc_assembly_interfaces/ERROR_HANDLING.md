# Error Handling System - ProMOC Assembly

## Übersicht

Das ProMOC Assembly System verwendet ein hierarchisches Custom Exception System für präzises und konsistentes Error Handling. Dieses Dokument beschreibt die Verwendung und Best Practices.

## Exception Hierarchie

```
ProMocError (Basis)
├── ConnectionError (1100-1199)
│   ├── DeviceNotFoundError (1101)
│   ├── DeviceDisconnectedError (1102)
│   └── CommunicationTimeoutError (1103)
├── MotionError (1200-1299)
│   ├── MovementTimeoutError (1201)
│   ├── PositionOutOfBoundsError (1202)
│   ├── CollisionDetectedError (1203)
│   └── HomingFailedError (1204)
├── SafetyViolation (1300-1399)
│   ├── SoftLimitViolationError (1301)
│   ├── HardLimitViolationError (1302)
│   ├── EmergencyStopError (1303)
│   └── SafetyZoneViolationError (1304)
├── CalibrationError (1400-1499)
│   ├── HomingRequiredError (1401)
│   ├── CalibrationFailedError (1402)
│   └── CalibrationDataInvalidError (1403)
├── HardwareError (1500-1599)
│   ├── DriverNotAvailableError (1501)
│   ├── HardwareInitializationError (1502)
│   └── SensorReadError (1503)
├── ConfigurationError (1600-1699)
│   ├── InvalidParameterError (1601)
│   ├── MissingConfigurationError (1602)
│   └── ValidationError (1603)
└── ServiceError (1700-1799)
    ├── ServiceCallFailedError (1701)
    ├── InvalidServiceRequestError (1702)
    └── ServiceTimeoutError (1703)
```

## Verwendung

### 1. Exceptions Werfen

```python
from promoc_assembly_interfaces.promoc_exceptions import (
    PositionOutOfBoundsError,
    HomingRequiredError,
    DeviceNotFoundError
)

class MyDriver:
    def move_to_position(self, position: float):
        # Check if homed
        if not self.is_homed:
            raise HomingRequiredError(
                "Device must be homed before movement",
                details={'current_state': 'unhomed', 'requested_position': position}
            )
        
        # Validate position
        if position < self.min_position or position > self.max_position:
            raise PositionOutOfBoundsError(
                f"Position {position}mm is outside valid range "
                f"[{self.min_position}, {self.max_position}]",
                details={
                    'requested': position,
                    'min': self.min_position,
                    'max': self.max_position
                }
            )
        
        # Perform movement
        self._move(position)
```

### 2. Service Error Handling mit Decorator

```python
from promoc_assembly_interfaces.error_handling import handle_service_errors
from promoc_assembly_interfaces.promoc_exceptions import MotionError

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        self.srv = self.create_service(
            MoveAbsolute,
            'move_absolute',
            self.move_absolute_callback
        )
    
    @handle_service_errors(logger=None)  # Logger wird automatisch erkannt
    def move_absolute_callback(self, request, response):
        """Service callback mit automatischem Error Handling."""
        # Business logic - Exceptions werden automatisch behandelt
        self.driver.move_to_position(request.position)
        
        response.success = True
        response.status_message = "Movement completed successfully"
        return response
```

### 3. Retry Mechanismus

```python
from promoc_assembly_interfaces.error_handling import retry_on_error, RetryConfig

class MyDriver:
    @retry_on_error(RetryConfig(
        max_attempts=5,
        delay=1.0,
        backoff_factor=2.0,
        retriable_exceptions=(DeviceDisconnectedError, CommunicationTimeoutError)
    ))
    def connect(self, port: str) -> bool:
        """Automatische Wiederholung bei Verbindungsfehlern."""
        # Connection logic - wird automatisch wiederholt bei Fehler
        return self._establish_connection(port)
```

### 4. Error Recovery Strategien

```python
from promoc_assembly_interfaces.error_handling import (
    ErrorRecoveryManager,
    HomingRecoveryStrategy,
    ReconnectionRecoveryStrategy
)

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        
        # Setup Recovery Manager
        self.recovery_manager = ErrorRecoveryManager(self.get_logger())
        self.recovery_manager.add_strategy(HomingRecoveryStrategy(self.get_logger()))
        self.recovery_manager.add_strategy(ReconnectionRecoveryStrategy(self.get_logger()))
    
    def perform_operation(self):
        try:
            self.driver.move_to_position(100.0)
        except ProMocError as e:
            # Versuche Recovery
            context = {
                'driver': self.driver,
                'port': self.port
            }
            if self.recovery_manager.attempt_recovery(e, context):
                # Recovery erfolgreich, Operation wiederholen
                self.driver.move_to_position(100.0)
            else:
                # Recovery fehlgeschlagen
                self.get_logger().error(f"Could not recover from error: {e}")
                raise
```

### 5. Standardisierte Service Responses

```python
from promoc_assembly_interfaces.error_handling import ServiceResponse

def my_service_callback(self, request, response):
    start_time = time.time()
    
    try:
        # Perform operation
        result = self.driver.do_something()
        
        # Create success response
        service_response = ServiceResponse.success_response(
            message="Operation completed successfully",
            execution_time=time.time() - start_time,
            result_value=result,
            additional_info="Some extra data"
        )
        
    except ProMocError as e:
        # Create error response
        service_response = ServiceResponse.error_response(
            error=e,
            execution_time=time.time() - start_time
        )
    
    # Populate ROS response
    return service_response.to_ros_response(response)
```

## Best Practices

### 1. Spezifische Exceptions verwenden

❌ **Schlecht:**
```python
except Exception as e:
    print(f"Error: {e}")
```

✅ **Gut:**
```python
except PositionOutOfBoundsError as e:
    self.logger.error(f"Position validation failed: {e}")
    # Spezifische Behandlung
except HomingRequiredError as e:
    self.logger.warning(f"Homing required: {e}")
    self.perform_homing()
```

### 2. Details hinzufügen

❌ **Schlecht:**
```python
raise PositionOutOfBoundsError("Invalid position")
```

✅ **Gut:**
```python
raise PositionOutOfBoundsError(
    f"Position {pos}mm exceeds limit {max_pos}mm",
    details={
        'requested_position': pos,
        'max_position': max_pos,
        'current_position': self.get_position(),
        'axis': self.axis_name
    }
)
```

### 3. Error Codes nutzen

```python
try:
    self.driver.move(100)
except ProMocError as e:
    # Error Code für programmatische Behandlung
    if e.error_code == 1202:  # PositionOutOfBoundsError
        # Spezielle Behandlung
        pass
    
    # Oder verwende ERROR_CODE_REGISTRY
    from promoc_assembly_interfaces.promoc_exceptions import get_error_description
    description = get_error_description(e.error_code)
```

### 4. Logging mit Error Context

```python
try:
    operation()
except ProMocError as e:
    self.logger.error(
        f"Operation failed: {e}",
        exc_info=True  # Fügt Stack Trace hinzu
    )
    # Details sind in e.details verfügbar
    self.logger.debug(f"Error details: {e.details}")
```

## Migration von bestehendem Code

### Schritt 1: Import hinzufügen

```python
from promoc_assembly_interfaces.promoc_exceptions import (
    DeviceNotFoundError,
    MovementTimeoutError,
    HomingRequiredError,
    # ... weitere nach Bedarf
)
```

### Schritt 2: Generic Exceptions ersetzen

**Vorher:**
```python
def connect(self):
    if not self._find_device():
        raise Exception("Device not found")
```

**Nachher:**
```python
def connect(self):
    if not self._find_device():
        raise DeviceNotFoundError(
            f"Could not find device on port {self.port}",
            details={'port': self.port, 'available_devices': self._list_devices()}
        )
```

### Schritt 3: Error Handling aktualisieren

**Vorher:**
```python
try:
    self.move(position)
except Exception as e:
    self.logger.error(f"Error: {e}")
    response.success = False
    response.status_message = str(e)
```

**Nachher:**
```python
from promoc_assembly_interfaces.error_handling import handle_service_errors

@handle_service_errors(logger=self.get_logger())
def callback(self, request, response):
    self.move(request.position)
    response.success = True
    response.status_message = "Movement completed"
    return response
```

## Error Code Referenz

| Code Range | Kategorie | Beschreibung |
|------------|-----------|--------------|
| 1000 | Generic | Allgemeiner ProMOC Fehler |
| 1100-1199 | Connection | Verbindungsfehler |
| 1200-1299 | Motion | Bewegungsfehler |
| 1300-1399 | Safety | Sicherheitsverstöße |
| 1400-1499 | Calibration | Kalibrierungsfehler |
| 1500-1599 | Hardware | Hardware-Fehler |
| 1600-1699 | Configuration | Konfigurationsfehler |
| 1700-1799 | Service | Service-Fehler |

## Testing

```python
import pytest
from promoc_assembly_interfaces.promoc_exceptions import PositionOutOfBoundsError

def test_position_validation():
    driver = MyDriver()
    
    with pytest.raises(PositionOutOfBoundsError) as exc_info:
        driver.move_to_position(1000.0)  # Outside bounds
    
    # Check error details
    assert exc_info.value.error_code == 1202
    assert 'requested' in exc_info.value.details
```

## Weitere Ressourcen

- `promoc_exceptions.py`: Exception Definitionen
- `error_handling.py`: Utilities für Error Handling
- Service Interface Definitionen in `srv/`

---

**Erstellt:** 29. Oktober 2025  
**Autor:** ProMOC Assembly Team
