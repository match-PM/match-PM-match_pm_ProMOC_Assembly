"""Concrete camera service handlers."""

__all__ = ["AutofocusHandler", "ExposureHandler", "MTFHandler"]


def __getattr__(name):
    if name == "AutofocusHandler":
        from .autofocus import AutofocusHandler

        return AutofocusHandler
    if name == "ExposureHandler":
        from .exposure import ExposureHandler

        return ExposureHandler
    if name == "MTFHandler":
        from .mtf import MTFHandler

        return MTFHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
