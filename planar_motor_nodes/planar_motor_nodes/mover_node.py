"""Deprecated compatibility wrapper for the legacy mover node module path.

Do not extend this file.
Use ``planar_motor_nodes.node`` as the canonical entry point.
"""

from .node import MoverServiceNode, main


__all__ = ["MoverServiceNode", "main"]
