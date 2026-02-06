"""Camera Service Callbacks - Modular Structure.

Modules:
    - autofocus: Autofocus with 5 algorithms (GoldenSection, HillClimbing, Parabolic, Fibonacci, Exhaustive)
    - mtf: MTF measurements and ROI selection
    - exposure: Exposure control
    - exposure: Exposure control
"""

from .autofocus import AutofocusCallbacks
from .mtf import MTFCallbacks
from .exposure import ExposureCallbacks
from .base import CallbackBase


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
        """Initializes all callback modules.
        
        Args:
            node: Parent ROS2 node
            camera_driver: Camera driver instance
        """
        # CallbackBase.__init__ wird durch MRO aufgerufen
        super().__init__(node, camera_driver)
        
        # MTF analyzer lazy init
        self._mtf_analyzer = None


__all__ = [
    'CameraServiceCallbacks',
    'AutofocusCallbacks',
    'MTFCallbacks', 
    'ExposureCallbacks',
    'CallbackBase',
]
