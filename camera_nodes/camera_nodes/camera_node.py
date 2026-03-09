"""Deprecated compatibility wrapper for the legacy camera node module path.

Do not extend this file.
Use ``camera_nodes.node`` as the canonical entry point.
"""

from .node import CameraNode, main


__all__ = ["CameraNode", "main"]
