"""
Algorithms Package for ProMOC Core.

This package contains reusable algorithms for image processing,
focus analysis, and optical measurements.

Modules:
    - focus_metrics: Focus quality metrics (variance, tenengrad, brenner)
    - autofocus: Hybrid autofocus algorithm (coarse + golden section)
    - mtf_analysis: MTF computation using slanted edge method
"""

from .focus_metrics import (
    laplacian_variance,
    tenengrad,
    brenner_gradient,
    normalized_variance,
    sml
)

from .autofocus import HybridAutofocus, AutofocusResult, AutofocusConfig, FocusPhase

from .mtf_analysis import MTFAnalyzer, MTFResult, MTFConfig, compute_mtf

__all__ = [
    # Focus metrics
    'laplacian_variance',
    'tenengrad',
    'brenner_gradient',
    'normalized_variance',
    'sml',
    # Autofocus
    'HybridAutofocus',
    'AutofocusResult',
    'AutofocusConfig',
    'FocusPhase',
    # MTF
    'MTFAnalyzer',
    'MTFResult',
    'MTFConfig',
    'compute_mtf',
]
