"""Camera domain layer: models, logic, and algorithms."""

__all__ = [
    "CameraImageProcessing",
    "FlyOverDetector",
    "FlyOverResult",
    "FocusProfile",
    "FocusProfileBuilder",
]


def __getattr__(name):
    if name in {"CameraImageProcessing", "FlyOverDetector", "FlyOverResult"}:
        from .logic import CameraImageProcessing, FlyOverDetector, FlyOverResult

        mapping = {
            "CameraImageProcessing": CameraImageProcessing,
            "FlyOverDetector": FlyOverDetector,
            "FlyOverResult": FlyOverResult,
        }
        return mapping[name]
    if name in {"FocusProfile", "FocusProfileBuilder"}:
        from .models import FocusProfile, FocusProfileBuilder

        mapping = {
            "FocusProfile": FocusProfile,
            "FocusProfileBuilder": FocusProfileBuilder,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
