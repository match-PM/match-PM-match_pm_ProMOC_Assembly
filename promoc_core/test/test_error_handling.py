"""Unit tests for ROS service error response handling."""

from __future__ import annotations

import pytest

from promoc_core import error_codes
from promoc_core.error_handling import handle_service_errors
from promoc_core.promoc_exceptions import ConfigurationError


class _Response:
    def __init__(self):
        self.success = True
        self.error_code = error_codes.SUCCESS
        self.status_message = ""


class _Logger:
    def __init__(self):
        self.messages: list[str] = []

    def error(self, message: str) -> None:
        self.messages.append(message)


class _Callbacks:
    def __init__(self):
        self.logger = _Logger()

    @handle_service_errors()
    def raises_promoc_error(self, request, response):
        raise ConfigurationError(
            "bad parameter",
            error_code=error_codes.INVALID_COMMAND,
        )

    @handle_service_errors()
    def raises_unexpected_error(self, request, response):
        raise RuntimeError("boom")


def test_handle_service_errors_maps_promoc_error_to_response() -> None:
    callbacks = _Callbacks()
    response = callbacks.raises_promoc_error(object(), _Response())

    assert response.success is False
    assert response.error_code == error_codes.INVALID_COMMAND
    assert "bad parameter" in response.status_message
    assert callbacks.logger.messages


def test_handle_service_errors_maps_unexpected_error_to_unknown_error() -> None:
    response = _Callbacks().raises_unexpected_error(object(), _Response())

    assert response.success is False
    assert response.error_code == error_codes.UNKNOWN_ERROR
    assert response.status_message == "RuntimeError: boom"


def test_handle_service_errors_reraises_when_no_response_object_exists() -> None:
    @handle_service_errors()
    def broken_callback():
        raise RuntimeError("no response")

    with pytest.raises(RuntimeError, match="no response"):
        broken_callback()
