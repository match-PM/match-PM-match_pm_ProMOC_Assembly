"""Concrete camera service handlers."""

<<<<<<< HEAD
__all__ = ["AutofocusHandler", "ExposureHandler"]
=======
__all__ = ["AutofocusHandler", "ExposureHandler", "MTFHandler"]
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0


def __getattr__(name):
    if name == "AutofocusHandler":
        from .autofocus import AutofocusHandler

        return AutofocusHandler
    if name == "ExposureHandler":
        from .exposure import ExposureHandler

        return ExposureHandler
<<<<<<< HEAD
=======
    if name == "MTFHandler":
        from .mtf import MTFHandler

        return MTFHandler
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
