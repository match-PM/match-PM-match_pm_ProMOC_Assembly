"""Camera Service Callbacks - Modular Structure.

Modules:
    - autofocus: Autofocus with 5 algorithms (GoldenSection, HillClimbing, Parabolic, Fibonacci, Exhaustive)
    - mtf: MTF measurements and ROI selection
    - exposure: Exposure control
"""

from .base import CallbackBase

# Keep base/helper imports available even in minimal test environments where
# generated ROS service modules are not present.
from .focus_profile import FocusProfile, FocusProfileBuilder

AutofocusCallbacks = None
MTFCallbacks = None
ExposureCallbacks = None
FlyOverDetector = None
FlyOverResult = None

try:  # pragma: no cover - exercised in ROS runtime
    from .fly_over import FlyOverDetector, FlyOverResult
    from .autofocus import AutofocusCallbacks
    from .mtf import MTFCallbacks
    from .exposure import ExposureCallbacks
except ImportError:
    pass


if AutofocusCallbacks is not None and MTFCallbacks is not None and ExposureCallbacks is not None:

    class CameraServiceCallbacks(AutofocusCallbacks, MTFCallbacks, ExposureCallbacks):
        """Combined service callbacks for the camera node.

        Inherits from all specialized callback classes:
        - AutofocusCallbacks: autofocus_callback (modes 0-4), autofocus_comparison_callback
        - MTFCallbacks: select_roi_callback, measure_mtf_callback, detect_rois_callback
        - ExposureCallbacks: manual_set_exposure_callback

        Usage:
            callbacks = CameraServiceCallbacks(node, camera_driver)
        """

        def __init__(self, node, camera_driver):
            """Initializes all callback modules."""
            # CallbackBase.__init__ is invoked via MRO.
            super().__init__(node, camera_driver)


__all__ = [
    'CallbackBase',
    'FocusProfile',
    'FocusProfileBuilder',
]

if FlyOverDetector is not None and FlyOverResult is not None:
    __all__.extend(
        [
            'FlyOverDetector',
            'FlyOverResult',
        ]
    )

if AutofocusCallbacks is not None and MTFCallbacks is not None and ExposureCallbacks is not None:
    __all__.extend(
        [
            'CameraServiceCallbacks',
            'AutofocusCallbacks',
            'MTFCallbacks',
            'ExposureCallbacks',
        ]
    )
