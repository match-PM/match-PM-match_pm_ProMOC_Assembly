# ProMOC Core Quick Reference

## Raise Specific Exceptions

```python
from promoc_core.promoc_exceptions import SafetyError

raise SafetyError(
    "position outside configured limits",
    details={"requested": position},
)
```

## Handle Service Errors

```python
from promoc_core import error_codes
from promoc_core.error_handling import handle_service_errors


@handle_service_errors()
def my_service_callback(self, request, response):
    self.driver.do_work()
    response.success = True
    response.error_code = error_codes.SUCCESS
    response.status_message = "done"
    return response
```

The decorator is intentionally small. It only maps exceptions into the common
ROS response fields. Retry, reconnect, and homing behavior should stay explicit
in the owning node or driver.

## Common Exception Types

| Exception | Use When |
| --- | --- |
| `ConnectionError` | Device not found, disconnection, timeout |
| `MotionError` | Movement timeout, position error, homing failure |
| `SafetyError` | Limit violations, emergency stop, collision |
| `HardwareError` | Driver unavailable, init failure, sensor error |
| `ConfigurationError` | Invalid parameter, missing config |
| `ServiceError` | Service call failure, invalid request |
| `ImageProcessingError` | Camera/image processing errors |
