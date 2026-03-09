"""ROS client adapters used by camera service handlers."""

__all__ = [
    "AxisClientManager",
    "CameraFormatController",
    "ParameterAccessor",
    "temporary_velocity",
]


def __getattr__(name):
    if name == "AxisClientManager":
        from .autofocus_axis import AxisClientManager

        return AxisClientManager
    if name == "CameraFormatController":
        from .camera_format import CameraFormatController

        return CameraFormatController
    if name == "ParameterAccessor":
        from .parameter_access import ParameterAccessor

        return ParameterAccessor
    if name == "temporary_velocity":
        from .axis_velocity import temporary_velocity

        return temporary_velocity
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
