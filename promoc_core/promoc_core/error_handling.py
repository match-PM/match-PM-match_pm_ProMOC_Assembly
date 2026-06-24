"""Small helpers for ROS service error responses."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from . import error_codes
from .promoc_exceptions import ProMocError


def _logger_from_args(args, explicit_logger):
    if explicit_logger is not None:
        return explicit_logger
    if args and hasattr(args[0], "logger"):
        return args[0].logger
    return None


def _response_from_args(args):
    for arg in args:
        if hasattr(arg, "success"):
            return arg
    return None


def _fill_error_response(response, error: Exception):
    response.success = False
    if isinstance(error, ProMocError):
        response.error_code = int(error.error_code)
        response.status_message = str(error)
    else:
        response.error_code = int(error_codes.UNKNOWN_ERROR)
        response.status_message = f"{type(error).__name__}: {error}"
    return response


def handle_service_errors(logger=None):
    """Convert service callback exceptions into standard ROS response fields."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_logger = _logger_from_args(args, logger)

            try:
                return func(*args, **kwargs)
            except Exception as error:
                if current_logger:
                    if isinstance(error, ProMocError):
                        current_logger.error(f"Service error: {error}")
                    else:
                        current_logger.error(
                            f"Unexpected service error: {type(error).__name__}: {error}"
                        )

                response = _response_from_args(args)
                if response is None:
                    raise
                return _fill_error_response(response, error)

        return wrapper

    return decorator
