"""Small helpers for ROS service error responses."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from . import error_codes
from .promoc_exceptions import ProMocError


def _logger_from_args(args, explicit_logger):
    # Sucht den Logger: explizit uebergeben -> self.logger vom ersten Argument -> None
    if explicit_logger is not None:
        return explicit_logger
    if args and hasattr(args[0], "logger"):
        return args[0].logger
    return None


def _response_from_args(args):
    # Findet das Response-Objekt in den Funktionsargumenten (Attribut 'success')
    for arg in args:
        if hasattr(arg, "success"):
            return arg
    return None


def _fill_error_response(response, error: Exception):
    # Befuellt die Service-Response mit Fehlerdaten.
    # Bei ProMocError: spezifischer error_code und message.
    # Bei anderen Exceptions: UNKNOWN_ERROR und Typ+Message.
    response.success = False
    if isinstance(error, ProMocError):
        response.error_code = int(error.error_code)
        response.status_message = str(error)
    else:
        response.error_code = int(error_codes.UNKNOWN_ERROR)
        response.status_message = f"{type(error).__name__}: {error}"
    return response


def handle_service_errors(logger=None):
    """Dekorator: Wandelt Exceptions in Service-Callbacks in ROS-Response-Felder um.

    Funktionsweise:
    1. Fangt jede Exception im dekorierten Callback ab
    2. Loggt den Fehler (mit ProMocError-Erkennung)
    3. Sucht das Response-Objekt (anhand des 'success'-Attributs)
    4. Befuellt success=False, error_code und status_message
    5. Wirft die Exception weiter, wenn kein Response gefunden wurde
    """

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
