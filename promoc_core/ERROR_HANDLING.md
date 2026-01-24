# Error Handling System - ProMOC Assembly

## Overview

The ProMOC Assembly System uses a simplified, hierarchical exception system for consistent error handling. This document describes usage and best practices.

## Exception Hierarchy

```
ProMocError (Base)
├── ConnectionError      # Connection, Timeout, Device not found
├── MotionError          # Movement, Position, Collision, Homing
├── SafetyError          # Soft/Hard Limits, Emergency Stop
├── HardwareError        # Driver, Sensor, Initialization
├── ConfigurationError   # Parameters, Validation
├── ServiceError         # ROS2 Service errors
└── ImageProcessingError # Camera-specific processing errors
```

## Usage

### 1. Raising Exceptions

```python
from promoc_core.promoc_exceptions import (
    MotionError,
    SafetyError,
    ConnectionError
)

class MyDriver:
    def move_to_position(self, position: float):
        # Check if homed
        if not self.is_homed:
            raise MotionError(
                "Device must be homed before movement",
                details={'current_state': 'unhomed', 'requested_position': position}
            )
        
        # Validate position
        if position < self.min_position or position > self.max_position:
            raise SafetyError(
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

### 2. Service Error Handling with Decorator

```python
from promoc_core.error_handling import handle_service_errors

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        self.srv = self.create_service(
            MoveAbsolute,
            'move_absolute',
            self.move_absolute_callback
        )
    
    @handle_service_errors(logger=None)  # Logger auto-detected
    def move_absolute_callback(self, request, response):
        """Service callback with automatic error handling."""
        # Business logic - exceptions handled automatically
        self.driver.move_to_position(request.position)
        
        response.success = True
        response.status_message = "Movement completed successfully"
        return response
```

### 3. Retry Mechanism

```python
from promoc_core.error_handling import retry_on_error, RetryConfig

class MyDriver:
    @retry_on_error(RetryConfig(
        max_attempts=5,
        delay=1.0,
        backoff_factor=2.0
    ))
    def connect(self, port: str) -> bool:
        """Automatic retry on connection errors."""
        return self._establish_connection(port)
```

### 4. Error Recovery Strategies

```python
from promoc_core.error_handling import (
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
            # Attempt recovery
            context = {'driver': self.driver, 'port': self.port}
            if self.recovery_manager.attempt_recovery(e, context):
                # Recovery successful, retry operation
                self.driver.move_to_position(100.0)
            else:
                # Recovery failed
                self.get_logger().error(f"Could not recover from error: {e}")
                raise
```

### 5. Standardized Service Responses

```python
from promoc_core.error_handling import ServiceResponse

def my_service_callback(self, request, response):
    start_time = time.time()
    
    try:
        result = self.driver.do_something()
        
        service_response = ServiceResponse.success_response(
            message="Operation completed successfully",
            execution_time=time.time() - start_time,
            result_value=result
        )
        
    except ProMocError as e:
        service_response = ServiceResponse.error_response(
            error=e,
            execution_time=time.time() - start_time
        )
    
    return service_response.to_ros_response(response)
```

## Best Practices

### 1. Use Specific Exceptions

❌ **Bad:**
```python
except Exception as e:
    print(f"Error: {e}")
```

✅ **Good:**
```python
except MotionError as e:
    self.logger.error(f"Motion failed: {e}")
    # Specific handling
except SafetyError as e:
    self.logger.warning(f"Safety violation: {e}")
    self.emergency_stop()
```

### 2. Add Details

❌ **Bad:**
```python
raise MotionError("Invalid position")
```

✅ **Good:**
```python
raise MotionError(
    f"Position {pos}mm exceeds limit {max_pos}mm",
    details={
        'requested_position': pos,
        'max_position': max_pos,
        'current_position': self.get_position(),
        'axis': self.axis_name
    }
)
```

### 3. Logging with Error Context

```python
try:
    operation()
except ProMocError as e:
    self.logger.error(
        f"Operation failed: {e}",
        exc_info=True  # Adds stack trace
    )
    # Details available in e.details
    self.logger.debug(f"Error details: {e.details}")
```

## Exception Categories

| Category | Use For |
|----------|---------|
| `ConnectionError` | Device not found, disconnection, timeout |
| `MotionError` | Movement timeout, position error, homing failure |
| `SafetyError` | Limit violations, emergency stop, collision |
| `HardwareError` | Driver unavailable, init failure, sensor error |
| `ConfigurationError` | Invalid parameter, missing config, validation |
| `ServiceError` | Service call failure, invalid request |
| `ImageProcessingError` | Camera/image processing errors |

## Testing

```python
import pytest
from promoc_core.promoc_exceptions import MotionError

def test_position_validation():
    driver = MyDriver()
    
    with pytest.raises(MotionError) as exc_info:
        driver.move_to_position(1000.0)  # Outside bounds
    
    # Check error details
    assert 'requested' in exc_info.value.details
```

## Further Resources

- `promoc_exceptions.py`: Exception definitions
- `error_handling.py`: Error handling utilities
- Service interface definitions in `srv/`

---

**Created:** October 29, 2025  
**Author:** ProMOC Assembly Team
