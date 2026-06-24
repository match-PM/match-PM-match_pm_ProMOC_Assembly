# Error Handling

The runtime uses one simple rule:

- raise a specific `promoc_core.promoc_exceptions` error in business logic
- let the service callback decorator convert that error into ROS response fields

## Exception Hierarchy

```text
ProMocError
├── ConnectionError
├── MotionError
├── SafetyError
├── HardwareError
├── ConfigurationError
├── ServiceError
└── ImageProcessingError
```

## Service Callback Pattern

```python
from promoc_core import error_codes
from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import ConfigurationError


class MyCallbacks:
    @handle_service_errors()
    def callback_set_value(self, request, response):
        if request.value <= 0:
            raise ConfigurationError(
                "value must be positive",
                error_code=error_codes.INVALID_COMMAND,
                details={"value": request.value},
            )

        response.success = True
        response.error_code = error_codes.SUCCESS
        response.status_message = "value accepted"
        return response
```

`handle_service_errors()` catches `ProMocError` and fills:

- `success = False`
- `error_code`
- `status_message`

Unexpected exceptions are mapped to `error_codes.UNKNOWN_ERROR`.

## Best Practices

- Use specific exceptions instead of generic `Exception`.
- Put useful context in the exception `details` dictionary.
- Keep recovery logic explicit in the node or driver that owns the hardware.
- Do not hide hardware reconnect, homing, or retry behavior in shared core
  helpers.
