"""Camera Service Callbacks - Modular Structure.

Modules:
    - autofocus: Autofocus with 3 modes (Standard, HillClimbing, Parabolic) + Comparison service
    - mtf: MTF measurements and ROI selection
    - exposure: Exposure control
"""

from .autofocus import AutofocusCallbacks
from .mtf import MTFCallbacks
from .exposure import ExposureCallbacks
from .base import CallbackBase


class CameraServiceCallbacks(AutofocusCallbacks, MTFCallbacks, ExposureCallbacks):
    """Combined service callbacks for the camera node.
    
    Inherits from all specialized callback classes:
    - AutofocusCallbacks: autofocus_callback (with refinement_mode 0-2), autofocus_comparison_callback
    - MTFCallbacks: select_roi_callback, measure_mtf_callback
    - ExposureCallbacks: manual_set_exposure_callback
    
    Usage:
        callbacks = CameraServiceCallbacks(node, camera_driver)
        # ... register services with callbacks
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
