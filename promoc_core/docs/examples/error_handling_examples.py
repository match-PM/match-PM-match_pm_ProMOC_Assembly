"""Small examples for the current ProMOC error-handling style."""

from __future__ import annotations

from promoc_core import error_codes
from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import ConfigurationError, MotionError


class ExampleResponse:
    """Tiny stand-in for generated ROS service response objects."""

    def __init__(self):
        self.success = True
        self.error_code = error_codes.SUCCESS
        self.status_message = ""


class ExampleLinearAxisCallbacks:
    """Example service callbacks with explicit business logic."""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger

    @handle_service_errors()
    def callback_move_absolute(self, request, response):
        if request.position_mm < 0.0:
            raise ConfigurationError(
                "position_mm must be non-negative",
                error_code=error_codes.INVALID_COMMAND,
                details={"position_mm": request.position_mm},
            )

        if not self.driver.is_homed:
            raise MotionError(
                "axis must be homed before movement",
                error_code=error_codes.DEVICE_UNHOMED,
            )

        self.driver.move_absolute(request.position_mm)
        response.success = True
        response.error_code = error_codes.SUCCESS
        response.status_message = "move complete"
        return response


def manual_error_handling_example(driver, request, response):
    """Use this style when a callback needs custom recovery or retry logic."""
    try:
        driver.move_absolute(request.position_mm)
    except MotionError as error:
        response.success = False
        response.error_code = error.error_code
        response.status_message = str(error)
        return response

    response.success = True
    response.error_code = error_codes.SUCCESS
    response.status_message = "move complete"
    return response
