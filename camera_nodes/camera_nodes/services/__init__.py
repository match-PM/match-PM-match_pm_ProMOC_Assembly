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
        from .autofocus_handler import AutofocusHandler

        return AutofocusHandler
    if name == "MTFHandler":
        from .mtf_handler import MTFHandler

        return MTFHandler
    if name == "ExposureHandler":
        from .exposure_handler import ExposureHandler

        return ExposureHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
