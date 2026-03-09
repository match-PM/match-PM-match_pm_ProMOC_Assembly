"""Deprecated compatibility wrapper for the legacy linear-axis node module path.

Do not extend this file.
Use ``linear_axis_nodes.node`` as the canonical entry point.
"""

from .node import LTS300Node, main


__all__ = ["LTS300Node", "main"]
