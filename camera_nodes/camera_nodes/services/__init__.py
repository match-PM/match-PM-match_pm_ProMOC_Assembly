"""Service layer for camera node callbacks."""

__all__ = [
    "CameraServiceHandlers",
    "AutofocusHandler",
    "MTFHandler",
    "ExposureHandler",
]


def __getattr__(name):
    """Lazy-import service handlers to keep import side effects minimal."""
    if name == "CameraServiceHandlers":
        from .registry import CameraServiceHandlers

        return CameraServiceHandlers
    if name == "AutofocusHandler":
        from .handlers.autofocus import AutofocusHandler

        return AutofocusHandler
    if name == "MTFHandler":
        from .handlers.mtf import MTFHandler

        return MTFHandler
    if name == "ExposureHandler":
        from .handlers.exposure import ExposureHandler

        return ExposureHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
