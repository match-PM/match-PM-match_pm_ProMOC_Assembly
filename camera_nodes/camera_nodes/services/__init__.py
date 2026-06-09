"""Concrete camera service handlers."""

__all__ = ["AutofocusHandler", "ExposureHandler"]


def __getattr__(name):
    if name == "AutofocusHandler":
        from .autofocus import AutofocusHandler

        return AutofocusHandler
    if name == "ExposureHandler":
        from .exposure import ExposureHandler

        return ExposureHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
