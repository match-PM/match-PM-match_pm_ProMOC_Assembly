# ProMOC Error Handling - Quick Reference

## 🚀 Quick Start

### 1. Import Exceptions
```python
from promoc_core.promoc_exceptions import (
    ProMocError,
    MotionError,
    SafetyError,
    ConnectionError,
    HardwareError,
    ConfigurationError,
    ServiceError
)
```

### 2. Raise Specific Exceptions
```python
# ❌ DON'T
raise Exception("Position out of range")

# ✅ DO
raise SafetyError(
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

| Exception | Use When |
|-----------|----------|
| `ConnectionError` | Device not found, disconnection, timeout |
| `MotionError` | Movement timeout, position error, homing failure |
| `SafetyError` | Limit violations, emergency stop, collision |
| `HardwareError` | Driver unavailable, init failure, sensor error |
| `ConfigurationError` | Invalid parameter, missing config |
| `ServiceError` | Service call failure, invalid request |
| `ImageProcessingError` | Camera/image processing errors |

## 🔧 Common Patterns

### Pattern 1: Validate Input
```python
def move_to_position(self, position: float):
    if not self.is_homed:
        raise MotionError("Homing required before movement")
    
    if position < MIN or position > MAX:
        raise SafetyError(
            f"Position {position} outside range [{MIN}, {MAX}]",
            details={'requested': position, 'min': MIN, 'max': MAX}
        )
```

### Pattern 2: Catch Specific Exceptions
```python
try:
    self.driver.move(position)
except MotionError:
    self.driver.home()
    self.driver.move(position)  # Retry
except SafetyError as e:
    self.logger.error(f"Safety violation: {e}")
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

### ❌ DON'T:
- Use bare `except:` or `except Exception:` without re-raising
- Raise generic `Exception` 
- Ignore exceptions silently
- Use print() instead of logger
- Forget to add context in `details`

## 📚 Full Documentation

See `ERROR_HANDLING.md` for complete documentation and examples.

---
**Version:** 0.2.0  
**Updated:** January 2026
