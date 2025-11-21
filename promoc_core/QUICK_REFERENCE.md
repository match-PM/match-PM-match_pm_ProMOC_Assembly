# ProMOC Error Handling - Quick Reference

## 🚀 Quick Start

### 1. Import Exceptions
```python
from promoc_core.promoc_exceptions import (
    PositionOutOfBoundsError,
    HomingRequiredError,
    DeviceNotFoundError,
    MovementTimeoutError
)
```

### 2. Raise Specific Exceptions
```python
# ❌ DON'T
raise Exception("Position out of range")

# ✅ DO
raise PositionOutOfBoundsError(
    f"Position {pos}mm exceeds max {max_pos}mm",
    details={'requested': pos, 'max': max_pos}
)
```

### 3. Service Callback with Auto-Error-Handling
```python
from promoc_core.error_handling import handle_service_errors

@handle_service_errors(logger=self.get_logger())
def my_service_callback(self, request, response):
    # Just write the happy path!
    self.driver.move(request.position)
    response.success = True
    return response
```

### 4. Add Retry to Functions
```python
from promoc_core.error_handling import retry_on_error, RetryConfig

@retry_on_error(RetryConfig(max_attempts=5, delay=1.0))
def connect(self, port: str):
    # Will retry automatically on connection errors
    return self._establish_connection(port)
```

## 📋 Exception Types Cheat Sheet

| Category | Exception | Error Code | Use When |
|----------|-----------|------------|----------|
| **Connection** | `DeviceNotFoundError` | 1101 | Device can't be found |
| | `DeviceDisconnectedError` | 1102 | Device unexpectedly disconnects |
| | `CommunicationTimeoutError` | 1103 | Communication times out |
| **Motion** | `MovementTimeoutError` | 1201 | Movement takes too long |
| | `PositionOutOfBoundsError` | 1202 | Position outside valid range |
| | `CollisionDetectedError` | 1203 | Collision detected/predicted |
| | `HomingFailedError` | 1204 | Homing operation fails |
| **Safety** | `SoftLimitViolationError` | 1301 | Software limit violated |
| | `HardLimitViolationError` | 1302 | Hardware limit violated |
| | `EmergencyStopError` | 1303 | Emergency stop triggered |
| | `SafetyZoneViolationError` | 1304 | Safety zone violated |
| **Calibration** | `HomingRequiredError` | 1401 | Operation needs homing first |
| | `CalibrationFailedError` | 1402 | Calibration fails |
| | `CalibrationDataInvalidError` | 1403 | Calibration data corrupted |
| **Hardware** | `DriverNotAvailableError` | 1501 | Driver library not available |
| | `HardwareInitializationError` | 1502 | Hardware init fails |
| | `SensorReadError` | 1503 | Sensor reading fails |
| **Configuration** | `InvalidParameterError` | 1601 | Parameter has invalid value |
| | `MissingConfigurationError` | 1602 | Required config missing |
| | `ValidationError` | 1603 | Config validation fails |
| **Service** | `ServiceCallFailedError` | 1701 | Service call fails |
| | `InvalidServiceRequestError` | 1702 | Request contains invalid data |
| | `ServiceTimeoutError` | 1703 | Service call times out |

## 🔧 Common Patterns

### Pattern 1: Validate Input
```python
def move_to_position(self, position: float):
    if not self.is_homed:
        raise HomingRequiredError("Homing required before movement")
    
    if position < MIN or position > MAX:
        raise PositionOutOfBoundsError(
            f"Position {position} outside range [{MIN}, {MAX}]",
            details={'requested': position, 'min': MIN, 'max': MAX}
        )
```

### Pattern 2: Catch Specific Exceptions
```python
try:
    self.driver.move(position)
except HomingRequiredError:
    self.driver.home()
    self.driver.move(position)  # Retry
except PositionOutOfBoundsError as e:
    self.logger.error(f"Invalid position: {e}")
    # Use safe position
    safe_pos = clamp(position, MIN, MAX)
    self.driver.move(safe_pos)
```

### Pattern 3: Error Recovery
```python
from promoc_core.error_handling import (
    ErrorRecoveryManager,
    HomingRecoveryStrategy
)

recovery_manager = ErrorRecoveryManager(logger)
recovery_manager.add_strategy(HomingRecoveryStrategy(logger))

try:
    self.driver.move(position)
except ProMocError as e:
    if recovery_manager.attempt_recovery(e, {'driver': self.driver}):
        self.driver.move(position)  # Retry after recovery
```

### Pattern 4: Service Response
```python
from promoc_core.error_handling import ServiceResponse

def callback(self, request, response):
    start = time.time()
    try:
        result = self.do_operation()
        sr = ServiceResponse.success_response(
            "Operation successful",
            execution_time=time.time() - start,
            result=result
        )
    except ProMocError as e:
        sr = ServiceResponse.error_response(e, time.time() - start)
    
    return sr.to_ros_response(response)
```

## 🎯 Best Practices

### ✅ DO:
- Use specific exception types
- Add `details` dictionary with context
- Use `@handle_service_errors` decorator for services
- Log with appropriate level (error, warning, info, debug)
- Catch specific exceptions before generic ones
- Include error_code in responses

### ❌ DON'T:
- Use bare `except:` or `except Exception:` without re-raising
- Raise generic `Exception` 
- Ignore exceptions silently
- Use print() instead of logger
- Forget to add context in `details`

## 📞 Error Codes

| Range | Category |
|-------|----------|
| 1000 | Generic Error |
| 1100-1199 | Connection Errors |
| 1200-1299 | Motion Errors |
| 1300-1399 | Safety Violations |
| 1400-1499 | Calibration Errors |
| 1500-1599 | Hardware Errors |
| 1600-1699 | Configuration Errors |
| 1700-1799 | Service Errors |

## 📚 Full Documentation

See `ERROR_HANDLING.md` for complete documentation and examples.

---
**Version:** 0.1.0  
**Updated:** 29. Oktober 2025
