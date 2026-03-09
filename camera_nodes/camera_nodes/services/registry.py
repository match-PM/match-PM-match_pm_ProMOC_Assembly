"""Feature-oriented service handlers for camera_node."""

from __future__ import annotations

from .handlers.autofocus import AutofocusHandler
from .handlers.exposure import ExposureHandler
from .handlers.mtf import MTFHandler


class CameraServiceHandlers:
    """Flat service composition for camera features.

    This avoids a deep MRO/mixin chain and keeps responsibilities explicit.
    """

    def __init__(self, node, camera_driver):
        self.autofocus = AutofocusHandler(node, camera_driver)
        self.mtf = MTFHandler(node, camera_driver)
        self.exposure = ExposureHandler(node, camera_driver)
