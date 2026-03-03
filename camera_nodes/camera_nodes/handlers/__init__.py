"""Feature handlers for camera services."""

__all__ = [
    "AutofocusHandler",
    "MTFHandler",
    "ExposureHandler",
]


def __getattr__(name):
    """Lazy-import handlers to keep module import side effects minimal."""
    if name == "AutofocusHandler":
        from .autofocus_handler import AutofocusHandler

        return AutofocusHandler
    if name == "MTFHandler":
        from .mtf_handler import MTFHandler

        return MTFHandler
    if name == "ExposureHandler":
        from .exposure_handler import ExposureHandler

        return ExposureHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
