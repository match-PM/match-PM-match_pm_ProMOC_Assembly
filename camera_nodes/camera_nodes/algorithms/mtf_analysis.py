"""
MTF Analysis using Slanted Edge Method (ISO 12233).

This module is kept for backward compatibility. The implementation
has been moved into the `camera_nodes.algorithms.mtf` package.
"""

from .mtf import MTFAnalyzer, MTFConfig, MTFResult, compute_mtf

__all__ = [
    "MTFAnalyzer",
    "MTFConfig",
    "MTFResult",
    "compute_mtf",
]
