"""Service-first exports for the camera package."""

__all__ = [
    "CameraServiceHandlers",
    "AutofocusHandler",
    "MTFHandler",
    "ExposureHandler",
]


def __getattr__(name):
    if name == "CameraServiceHandlers":
        from .registry import CameraServiceHandlers

        return CameraServiceHandlers
    if name == "AutofocusHandler":
        from .autofocus import AutofocusHandler

        return AutofocusHandler
    if name == "MTFHandler":
        from .mtf import MTFHandler

        return MTFHandler
    if name == "ExposureHandler":
        from .exposure import ExposureHandler

        return ExposureHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
